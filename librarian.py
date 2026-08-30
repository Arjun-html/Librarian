#!/usr/bin/env python3
"""
librarian.py — CLI for Arjun's reading library.

Commands:
  add              Interactively add a new book
  list             List books  [--section <s>] [--status <s>]
  update <id>      Edit a book's fields
  remove <id>      Delete a book
  hero <id>        Set newspaper hero fields for a Reading book
  cache-covers     Download Open Library covers locally (--force re-downloads all)
  generate         Regenerate index.html, library.html, books/*.html and library.md
                   (auto-caches new covers first; --no-cache to skip)
"""

import re
import sqlite3
import sys
import html as html_lib
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    import markdown as _markdown
except ImportError:
    _markdown = None

try:
    import yaml as _yaml
except ImportError:
    _yaml = None

ROOT          = Path(__file__).parent
DB            = ROOT / 'library.db'
TEMPLATE      = ROOT / 'templates' / 'index_base.html'
LIB_TEMPLATE  = ROOT / 'templates' / 'library_base.html'
BOOK_TEMPLATE = ROOT / 'templates' / 'book_base.html'
INDEX         = ROOT / 'index.html'
LIBRARY       = ROOT / 'library.html'
BOOKS_DIR     = ROOT / 'books'
MD_FILE       = ROOT / 'library.md'

COVERS_DIR            = ROOT / 'book_covers_additional'
ESSAYS_DIR            = ROOT / 'essays'
ESSAYS_SRC            = ESSAYS_DIR / 'src'
ESSAYS_IMG            = ESSAYS_DIR / 'images'
ESSAYS_INDEX          = ESSAYS_DIR / 'index.html'
ESSAYS_INDEX_TEMPLATE = ROOT / 'templates' / 'essays_index_base.html'
ESSAY_TEMPLATE        = ROOT / 'templates' / 'essay_base.html'

GALLERIES_DIR             = ROOT / 'galleries'
GALLERY_IMAGES_DIR        = ROOT / 'gallery_images'
GALLERIES_INDEX           = GALLERIES_DIR / 'index.html'
GALLERIES_INDEX_TEMPLATE  = ROOT / 'templates' / 'galleries_index_base.html'
GALLERY_VISIT_TEMPLATE    = ROOT / 'templates' / 'gallery_visit_base.html'

SECTIONS = ['software', 'engineering', 'finance', 'philosophy']
SECTION_NAMES = {
    'software':    'Software Related Books',
    'engineering': 'Engineering & Mathematics',
    'finance':     'Finance',
    'philosophy':  'Greater Awareness & Philosophy',
}
STATUS_LABEL = {'read': 'Read', 'reading': 'Reading', 'list': 'Reading List'}
STATUS_CLASS  = {'read': 'status-read', 'reading': 'status-reading', 'list': 'status-list'}

# Essay categories share the book section keys, but use short display names.
ESSAY_CATEGORIES = {
    'software':    'Software',
    'engineering': 'Engineering',
    'finance':     'Finance',
    'philosophy':  'Philosophy',
}

# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS books (
        id                INTEGER PRIMARY KEY AUTOINCREMENT,
        title             TEXT    NOT NULL,
        author            TEXT    NOT NULL,
        isbn              TEXT,
        section           TEXT    NOT NULL CHECK(section IN ('software','engineering','finance','philosophy')),
        status            TEXT    NOT NULL CHECK(status IN ('read','reading','list')),
        my_notes          TEXT,
        ai_notes          TEXT,
        sort_order        INTEGER NOT NULL DEFAULT 0,
        hero_slot         TEXT    CHECK(hero_slot IN ('lead','side','bottom')),
        hero_sort         INTEGER NOT NULL DEFAULT 0,
        hero_kicker       TEXT,
        hero_headline     TEXT,
        hero_deck         TEXT,
        hero_byline_extra TEXT,
        hero_body         TEXT,
        hero_progress     TEXT,
        local_cover_path  TEXT,
        date_added        DATE    DEFAULT CURRENT_DATE
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS gallery_visits (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT NOT NULL,
        venue       TEXT,
        visit_date  DATE NOT NULL,
        notes       TEXT,
        sort_order  INTEGER NOT NULL DEFAULT 0
    )''')
    conn.execute('''CREATE TABLE IF NOT EXISTS gallery_artworks (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        visit_id       INTEGER NOT NULL REFERENCES gallery_visits(id) ON DELETE CASCADE,
        name           TEXT NOT NULL,
        artist         TEXT,
        period         TEXT,
        reference_img  TEXT,
        own_photo_img  TEXT,
        my_notes       TEXT,
        sort_order     INTEGER NOT NULL DEFAULT 0
    )''')
    conn.commit()
    conn.close()

# ── HTML rendering ────────────────────────────────────────────────────────────

def e(s):
    return html_lib.escape(str(s), quote=False)


def _cover_div(book):
    alt = e(book['title'])
    if book['local_cover_path']:
        src = e(book['local_cover_path'])
    elif book['isbn']:
        src = f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-M.jpg"
    else:
        return '<div class="book-cover no-image"><span>No cover available</span></div>'
    return (
        f'<div class="book-cover">'
        f'<img src="{src}" alt="{alt}" onerror="this.parentElement.classList.add(\'no-image\'); this.style.display=\'none\';">'
        f'<div class="no-image" style="display:none;">No cover available</div>'
        f'</div>'
    )


def slugify(title):
    """Turn a book title into a URL-safe slug. e.g. 'The Prize' -> 'the-prize'."""
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode()
    title = title.lower().strip()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[\s_]+', '-', title)
    title = re.sub(r'-+', '-', title).strip('-')
    return title


def assign_slugs(books):
    """Map each book id to a unique slug, resolving collisions with --2, --3, …

    `books` is processed in the given order, so the first occurrence of a slug
    keeps the bare form and later duplicates get the numeric suffix.
    """
    seen, slugs = {}, {}
    for b in books:
        base = slugify(b['title']) or f"book-{b['id']}"
        n = seen.get(base, 0) + 1
        seen[base] = n
        slugs[b['id']] = base if n == 1 else f"{base}--{n}"
    return slugs


def _tile_cover(book):
    """Cover block for a library tile (sepia, falls back to 'No cover available')."""
    if book['local_cover_path']:
        src = e(book['local_cover_path'])
    elif book['isbn']:
        src = f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-M.jpg"
    else:
        return '<div class="tile-cover no-image"><span>No cover available</span></div>'
    return (
        f'<div class="tile-cover">'
        f'<img src="{src}" alt="{e(book["title"])}" '
        f'onerror="this.parentElement.classList.add(\'no-image\'); this.style.display=\'none\';">'
        f'<div class="no-image" style="display:none;">No cover available</div>'
        f'</div>'
    )


def render_book_tile(book, slug):
    """Emit a .book-tile linking to the book's per-book page (books/<slug>.html)."""
    status_label = STATUS_LABEL[book['status']]
    status_class = STATUS_CLASS[book['status']]
    cover = _tile_cover(book)
    return (
        f'            <a class="book-tile" href="books/{slug}.html" data-section="{book["section"]}" data-status="{book["status"]}">\n'
        f'                {cover}\n'
        f'                <div class="tile-meta">\n'
        f'                    <div class="tile-title">{e(book["title"])}</div>\n'
        f'                    <div class="tile-author">{e(book["author"])}</div>\n'
        f'                    <span class="book-status {status_class}">{status_label}</span>\n'
        f'                </div>\n'
        f'            </a>'
    )


def _detail_cover(book):
    """Large cover block for a per-book page. Paths are relative to books/ (../)."""
    if book['local_cover_path']:
        src = '../' + e(book['local_cover_path'])
    elif book['isbn']:
        src = f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-L.jpg"
    else:
        return '<div class="detail-cover no-image"><span>No cover available</span></div>'
    return (
        f'<div class="detail-cover">'
        f'<img src="{src}" alt="{e(book["title"])}" '
        f'onerror="this.parentElement.classList.add(\'no-image\'); this.style.display=\'none\';">'
        f'<div class="no-image" style="display:none;">No cover available</div>'
        f'</div>'
    )


def _notes_to_html(text):
    """Render my_notes (Markdown) to HTML for a per-book page.

    Uses the `markdown` package with the `extra` extension when available;
    otherwise falls back to splitting on blank lines and wrapping each chunk
    in an (HTML-escaped) <p> tag.
    """
    text = text.strip()
    if _markdown is not None:
        return _markdown.markdown(text, extensions=['extra'])
    chunks = re.split(r'\n\s*\n', text)
    return '\n'.join(f'<p>{e(chunk.strip())}</p>' for chunk in chunks if chunk.strip())


def render_book_page(book, slug):
    """Emit the <article> body for books/<slug>.html (filled into %%BOOK_CONTENT%%).

    Shows cover + title + author + section/status + full my_notes. No ai_notes.
    """
    status_label = STATUS_LABEL[book['status']]
    status_class = STATUS_CLASS[book['status']]
    section_name = SECTION_NAMES[book['section']]
    cover        = _detail_cover(book)

    if book['my_notes'] and book['my_notes'] != '—':
        notes_html = (
            '<div class="detail-notes">\n'
            '                    <span class="detail-notes-label">My Notes</span>\n'
            f'                    <div class="detail-notes-text">{_notes_to_html(book["my_notes"])}</div>\n'
            '                </div>'
        )
    else:
        notes_html = '<div class="detail-notes"><p class="detail-notes-empty">No notes recorded yet.</p></div>'

    return (
        f'        <article class="book-detail">\n'
        f'            <div class="detail-labels">\n'
        f'                <span class="detail-section">{e(section_name)}</span>\n'
        f'                <span class="book-status {status_class}">{status_label}</span>\n'
        f'            </div>\n'
        f'            <h1 class="detail-title">{e(book["title"])}</h1>\n'
        f'            <div class="detail-author">By {e(book["author"])}</div>\n'
        f'            <div class="detail-body">\n'
        f'                {cover}\n'
        f'                {notes_html}\n'
        f'            </div>\n'
        f'        </article>'
    )


# ── Essays ────────────────────────────────────────────────────────────────────

def _parse_yaml(raw):
    """Parse a YAML frontmatter block to a dict. Falls back to a minimal
    key: value line parser if PyYAML is unavailable."""
    if _yaml is not None:
        data = _yaml.safe_load(raw)
        return data if isinstance(data, dict) else {}
    meta = {}
    for line in raw.splitlines():
        if ':' in line and not line.strip().startswith('#'):
            k, v = line.split(':', 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def _split_frontmatter(text):
    """Return (meta_dict, body_str) from a Markdown file that starts with a
    YAML `--- ... ---` frontmatter block. No frontmatter → ({}, whole text)."""
    text = text.lstrip('﻿')  # strip a leading BOM if present
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n?(.*)$', text, re.DOTALL)
    if m:
        return _parse_yaml(m.group(1)), m.group(2).strip()
    return {}, text.strip()


def _coerce_date(value, path):
    """Normalise a frontmatter date to a datetime.date; warn + use today on miss."""
    if value is None:
        print(f'  Warning: {path.name} has no date; using today')
        return date.today()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip(), '%Y-%m-%d').date()
    except ValueError:
        print(f'  Warning: {path.name} has invalid date "{value}"; using today')
        return date.today()


def parse_essay(path):
    """Read an essays/src/*.md file, returning a dict with title, date,
    date_display, category, category_name, deck, slug, body_html."""
    meta, body = _split_frontmatter(path.read_text(encoding='utf-8'))

    title = str(meta.get('title') or path.stem).strip()

    cat = str(meta.get('category') or '').strip().lower()
    if cat in ESSAY_CATEGORIES:
        category, category_name = cat, ESSAY_CATEGORIES[cat]
    else:
        if cat:
            print(f'  Warning: unknown essay category "{cat}" in {path.name}; using Uncategorised')
        category, category_name = 'uncategorised', 'Uncategorised'

    d = _coerce_date(meta.get('date'), path)

    return {
        'source':        path.name,
        'title':         title,
        'date':          d,
        'date_display':  f'{d.day} {d.strftime("%B")} {d.year}',
        'category':      category,
        'category_name': category_name,
        'deck':          str(meta.get('deck') or '').strip(),
        'slug':          slugify(title),
        'body_html':     _notes_to_html(body),
    }


def render_essay_featured(essay):
    """Emit the .essay-featured hero block for essays/index.html (whole block links
    to the essay; links are same-directory since index.html lives in essays/)."""
    deck = f'\n            <p class="essay-featured-deck">{e(essay["deck"])}</p>' if essay['deck'] else ''
    return (
        f'        <a class="essay-featured" href="{essay["slug"]}.html">\n'
        f'            <div class="essay-kicker">{e(essay["category_name"])}</div>\n'
        f'            <h2 class="essay-featured-headline">{e(essay["title"])}</h2>{deck}\n'
        f'            <div class="essay-date">{e(essay["date_display"])}</div>\n'
        f'        </a>'
    )


def render_essay_tile(essay):
    """Emit a .essay-tile card (title, category chip, date) for the grid."""
    return (
        f'            <a class="essay-tile" href="{essay["slug"]}.html">\n'
        f'                <span class="essay-category essay-category-{essay["category"]}">{e(essay["category_name"])}</span>\n'
        f'                <h3 class="essay-tile-title">{e(essay["title"])}</h3>\n'
        f'                <div class="essay-date">{e(essay["date_display"])}</div>\n'
        f'            </a>'
    )


def render_essay_page(essay):
    """Emit the <article class="essay-detail"> body for an individual essay page."""
    deck = f'\n            <p class="essay-detail-deck">{e(essay["deck"])}</p>' if essay['deck'] else ''
    return (
        f'        <article class="essay-detail">\n'
        f'            <div class="essay-detail-labels">\n'
        f'                <span class="essay-category essay-category-{essay["category"]}">{e(essay["category_name"])}</span>\n'
        f'                <span class="essay-date">{e(essay["date_display"])}</span>\n'
        f'            </div>\n'
        f'            <h1 class="essay-detail-title">{e(essay["title"])}</h1>{deck}\n'
        f'            <div class="essay-detail-body">\n'
        f'                {essay["body_html"]}\n'
        f'            </div>\n'
        f'        </article>'
    )


def _hero_cover_src(book):
    if book['local_cover_path']:
        return book['local_cover_path']
    if book['isbn']:
        return f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-M.jpg"
    return None


def _byline(book):
    """`By Author` plus the optional extra, without a dangling bullet."""
    parts = [f'By {e(book["author"])}']
    if book['hero_byline_extra']:
        parts.append(e(book['hero_byline_extra']))
    return ' &bull; '.join(parts)


def _book_excerpt(book, length=460):
    """First `length` characters (plus an ellipsis) of the book's per-book-page
    text — i.e. its rendered my_notes with markup stripped and whitespace
    collapsed. Used as the lead story's blurb on the front page. Returns '' when
    the book has no notes."""
    notes = book['my_notes']
    if not notes or notes.strip() == '—':
        return ''
    text = re.sub(r'<[^>]+>', ' ', _notes_to_html(notes))   # drop HTML tags
    text = html_lib.unescape(text)                           # decode entities
    text = re.sub(r'\s+', ' ', text).strip()                 # collapse whitespace
    if not text:
        return ''
    if len(text) <= length:
        return text
    cut = text[:length]
    return cut[:cut.rfind(' ')].rstrip(' ,;:') + '…'


EXHIBIT_TITLE = 'The Shelf, by Division'


def render_shelf_exhibit(conn):
    """A report exhibit: one stacked column per section, split by status.

    Deliberately *not* a timeline — `date_added` is dominated by the one-off
    migration date, so a per-month chart would be fiction. Division and status
    are real, so that is what gets plotted.
    """
    rows = conn.execute(
        'SELECT section, status, COUNT(*) FROM books GROUP BY section, status'
    ).fetchall()
    # ESSAY_CATEGORIES holds the short display names for these same keys —
    # the full SECTION_NAMES are far too long for an axis label.
    counts = {s: {'read': 0, 'reading': 0, 'list': 0} for s in SECTIONS}
    for section, status, n in rows:
        counts[section][status] = n

    totals = {s: sum(v.values()) for s, v in counts.items()}
    tallest = max(totals.values()) or 1
    PLOT = 168   # px

    cols = []
    for key in SECTIONS:
        c, total = counts[key], totals[key]
        segs = ''.join(
            f'<div class="seg seg-{st}" style="height:{n / tallest * PLOT:.1f}px" '
            f'title="{n} {STATUS_LABEL[st]}">'
            f'{f"<span>{n}</span>" if n / tallest * PLOT >= 22 else ""}</div>'
            for st in ('list', 'reading', 'read') if (n := c[st])
        )
        cols.append(
            f'            <div class="exhibit-col">\n'
            f'                <div class="exhibit-total">{total}</div>\n'
            f'                <div class="exhibit-stack">{segs}</div>\n'
            f'                <div class="exhibit-name">{e(ESSAY_CATEGORIES[key])}</div>\n'
            f'            </div>'
        )

    key_html = ''.join(
        f'<span class="exhibit-key-item"><i class="seg-{st}"></i>{STATUS_LABEL[st]}</span>'
        for st in ('read', 'reading', 'list')
    )
    shelved = sum(totals.values()) - sum(c['list'] for c in counts.values())

    return (
        '    <section class="exhibit">\n'
        f'        <div class="exhibit-head">{EXHIBIT_TITLE}'
        f'<span class="exhibit-rule"></span>'
        f'<span class="exhibit-count">{sum(totals.values())} volumes</span></div>\n'
        '        <div class="exhibit-body">\n'
        '        <div class="exhibit-plot">\n'
        + '\n'.join(cols) + '\n'
        '        </div>\n'
        '        <div class="exhibit-side">\n'
        f'            <div class="exhibit-key">{key_html}</div>\n'
        f'            <p class="exhibit-note">Counted at press time. {shelved} volumes are '
        f'published to the Library; Reading List titles are held in the ledger only.</p>\n'
        '        </div>\n'
        '        </div>\n'
        '    </section>'
    )


def render_hero(conn):
    """Build section-banner + newspaper-content HTML from books with hero_slot set."""
    books = conn.execute(
        "SELECT * FROM books WHERE status='reading' AND hero_slot IS NOT NULL "
        "ORDER BY CASE hero_slot WHEN 'lead' THEN 0 WHEN 'side' THEN 1 ELSE 2 END, hero_sort"
    ).fetchall()

    n = conn.execute("SELECT COUNT(*) FROM books WHERE status='reading'").fetchone()[0]
    volume_word = f"{n} Volume{'s' if n != 1 else ''}"
    banner = f'        <div class="section-banner">{volume_word} Under Active Review</div>'

    # Slugs must match the per-book page filenames: _generate_books / _generate_library
    # build them with assign_slugs over the same read/reading query, in the same order.
    pageable = conn.execute(
        "SELECT * FROM books WHERE status IN ('read','reading') ORDER BY title COLLATE NOCASE"
    ).fetchall()
    slugs = assign_slugs(pageable)

    def _link(book, inner):
        return f'<a href="books/{slugs[book["id"]]}.html">{inner}</a>'

    lead    = [b for b in books if b['hero_slot'] == 'lead']
    sides   = [b for b in books if b['hero_slot'] == 'side']
    bottoms = [b for b in books if b['hero_slot'] == 'bottom']

    top_parts = []
    for b in lead:
        src = _hero_cover_src(b)
        img = f'<img src="{e(src)}" alt="{e(b["title"])}" onerror="this.style.display=\'none\'">' if src else ''
        cover = _link(b, img) if img else ''
        excerpt = _book_excerpt(b)
        body = f'\n                    <p class="story-body">{e(excerpt)}</p>' if excerpt else ''
        top_parts.append(
            f'                <!-- LEAD STORY: {e(b["title"])} -->\n'
            f'                <div class="story-lead">\n'
            f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
            f'                    <div class="story-img-lead">\n'
            f'                        {cover}\n'
            f'                    </div>\n'
            f'                    <h2 class="story-headline-lead">{_link(b, e(b["hero_headline"] or b["title"]))}</h2>\n'
            f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
            f'                    <div class="story-byline">{_byline(b)}</div>{body}\n'
            f'                    <span class="story-progress">{e(b["hero_progress"] or "")}</span>\n'
            f'                </div>'
        )

    for b in sides:
        src = _hero_cover_src(b)
        img = f'<img src="{e(src)}" alt="{e(b["title"])}" onerror="this.style.display=\'none\'">' if src else ''
        cover = _link(b, img) if img else ''
        top_parts.append(
            f'                <div class="story-side">\n'
            f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
            f'                    <div class="story-img-sm">\n'
            f'                        {cover}\n'
            f'                    </div>\n'
            f'                    <h3 class="story-headline">{_link(b, e(b["hero_headline"] or b["title"]))}</h3>\n'
            f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
            f'                    <div class="story-byline">{_byline(b)}</div>\n'
            f'                    <span class="story-progress">{e(b["hero_progress"] or "")}</span>\n'
            f'                </div>'
        )

    newspaper_top = (
        '            <!-- Top section -->\n'
        '            <div class="newspaper-top">\n\n'
        + '\n\n'.join(top_parts) +
        '\n\n            </div><!-- /newspaper-top -->'
    )

    bottom_html = ''
    if bottoms:
        bottom_parts = []
        for b in bottoms:
            src = _hero_cover_src(b)
            img = f'<img src="{e(src)}" alt="{e(b["title"])}" onerror="this.style.display=\'none\'">' if src else ''
            cover = _link(b, img) if img else ''
            bottom_parts.append(
                f'                <div class="story-bottom">\n'
                f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
                f'                    <div class="story-img-sm">\n'
                f'                        {cover}\n'
                f'                    </div>\n'
                f'                    <h3 class="story-headline-sm">{_link(b, e(b["hero_headline"] or b["title"]))}</h3>\n'
                f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
                f'                    <div class="story-byline">{_byline(b)}</div>\n'
                f'                    <span class="story-progress">{e(b["hero_progress"] or "")}</span>\n'
                f'                </div>'
            )
        bottom_html = (
            '\n\n            <!-- Bottom row: ' + str(len(bottoms)) + ' stories -->\n'
            '            <div class="newspaper-bottom-row">\n\n'
            + '\n\n'.join(bottom_parts) +
            '\n\n            </div><!-- /newspaper-bottom-row -->'
        )

    return (
        banner + '\n\n'
        '        <div class="newspaper-content">\n\n'
        '            ' + newspaper_top + '\n'
        + bottom_html + '\n\n'
        '        </div><!-- /newspaper-content -->\n'
    )

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_generate(args=None):
    args = args or []
    ensure_schema()
    if not TEMPLATE.exists():
        sys.exit(f'Error: template not found at {TEMPLATE}')

    conn = get_db()

    # Best-effort: cache any not-yet-cached Open Library covers locally first, so
    # the pages link to local files and survive the cover host's periodic outages.
    # Does nothing once every cover is cached (all books skipped → no network);
    # bails out fast if the host is unreachable so generate never hangs. Opt out
    # with `generate --no-cache`.
    if '--no-cache' not in args:
        c = _cache_covers(conn, fail_fast=True, quiet=True, timeout=12)
        if c['cached']:
            print(f'Cached {c["cached"]} new cover(s) locally.')
        elif c['unreachable']:
            print('Note: covers.openlibrary.org unreachable - skipped cover caching.')

    template = TEMPLATE.read_text(encoding='utf-8')

    template = template.replace('%%NEWSPAPER_DYNAMIC%%', render_hero(conn))
    template = template.replace('%%SHELF_EXHIBIT%%', render_shelf_exhibit(conn))

    # Masthead date: current date in Hong Kong (UTC+8), e.g. "Sunday, 26 June 2026, <i>Hong Kong</i>"
    hk_now = datetime.now(timezone(timedelta(hours=8)))
    masthead_date = f"{hk_now.strftime('%A')}, {hk_now.day} {hk_now.strftime('%B')} {hk_now.year}, <i>Hong Kong</i>"
    template = template.replace('%%MASTHEAD_DATE%%', masthead_date)

    today = date.today()
    template = template.replace('%%FOOTER_DATE%%', f"{today.strftime('%B')} {today.day}, {today.year}")

    INDEX.write_text(template, encoding='utf-8')
    print(f'Generated {INDEX.name}')

    _generate_library(conn)
    _generate_books(conn)
    _generate_essays(conn)
    _generate_galleries(conn)
    _generate_md(conn)
    conn.close()


def _generate_library(conn):
    """Build library.html: every read/reading book as an alphabetical grid of tiles."""
    if not LIB_TEMPLATE.exists():
        sys.exit(f'Error: library template not found at {LIB_TEMPLATE}')

    books = conn.execute(
        "SELECT * FROM books WHERE status IN ('read','reading') "
        "ORDER BY title COLLATE NOCASE"
    ).fetchall()
    slugs = assign_slugs(books)
    tiles = '\n'.join(render_book_tile(b, slugs[b['id']]) for b in books)

    template = LIB_TEMPLATE.read_text(encoding='utf-8')
    template = template.replace('%%BOOK_TILES%%', tiles)

    hk_now = datetime.now(timezone(timedelta(hours=8)))
    masthead_date = f"{hk_now.strftime('%A')}, {hk_now.day} {hk_now.strftime('%B')} {hk_now.year}, <i>Hong Kong</i>"
    template = template.replace('%%MASTHEAD_DATE%%', masthead_date)

    n = len(books)
    template = template.replace('%%LIBRARY_COUNT%%', f"{n} Volume{'s' if n != 1 else ''}")

    LIBRARY.write_text(template, encoding='utf-8')
    print(f'Generated {LIBRARY.name}')


def _generate_books(conn):
    """Build one books/<slug>.html per read/reading book; prune stale pages.

    Uses the same query + assign_slugs as _generate_library, so slugs (and thus
    the tile links in library.html) match the generated filenames exactly.
    """
    if not BOOK_TEMPLATE.exists():
        sys.exit(f'Error: book template not found at {BOOK_TEMPLATE}')

    books = conn.execute(
        "SELECT * FROM books WHERE status IN ('read','reading') "
        "ORDER BY title COLLATE NOCASE"
    ).fetchall()
    slugs = assign_slugs(books)

    BOOKS_DIR.mkdir(exist_ok=True)
    template = BOOK_TEMPLATE.read_text(encoding='utf-8')

    wanted = set()
    for b in books:
        slug = slugs[b['id']]
        filename = f'{slug}.html'
        wanted.add(filename)
        page = template.replace('%%BOOK_TITLE%%', e(b['title']))
        page = page.replace('%%BOOK_CONTENT%%', render_book_page(b, slug))
        (BOOKS_DIR / filename).write_text(page, encoding='utf-8')

    # Prune pages for books that were removed/renamed since the last build.
    for stale in BOOKS_DIR.glob('*.html'):
        if stale.name not in wanted:
            stale.unlink()

    print(f'Generated {len(books)} pages in {BOOKS_DIR.name}/')


def _generate_essays(conn=None):
    """Build essays/index.html + one essays/<slug>.html per essays/src/*.md.

    Essays are file-driven (they never touch the DB; `conn` is accepted only for
    signature parity with the other _generate_* helpers). Layout = Option B:
    the newest-dated essay becomes the featured hero, the rest form a
    chronological grid. Stale pages (slugs with no source .md) are pruned.
    """
    if not ESSAYS_INDEX_TEMPLATE.exists() or not ESSAY_TEMPLATE.exists():
        sys.exit(f'Error: essay templates not found in {ESSAYS_INDEX_TEMPLATE.parent}')

    ESSAYS_SRC.mkdir(parents=True, exist_ok=True)
    ESSAYS_IMG.mkdir(parents=True, exist_ok=True)

    essays = []
    for path in sorted(ESSAYS_SRC.glob('*.md')):
        try:
            essays.append(parse_essay(path))
        except Exception as exc:
            print(f'  Skipping {path.name}: {exc}')

    # Newest first; the first essay is featured, the remainder fill the grid.
    essays.sort(key=lambda es: es['date'], reverse=True)

    # Unique, stable slugs (collisions -> --2, --3, …), same scheme as books.
    seen = {}
    for es in essays:
        base = slugify(es['title']) or 'essay'
        n = seen.get(base, 0) + 1
        seen[base] = n
        es['slug'] = base if n == 1 else f'{base}--{n}'

    # Individual essay pages.
    page_tpl = ESSAY_TEMPLATE.read_text(encoding='utf-8')
    wanted = set()
    for es in essays:
        filename = f'{es["slug"]}.html'
        wanted.add(filename)
        page = page_tpl.replace('%%ESSAY_TITLE%%', e(es['title']))
        page = page.replace('%%ESSAY_CONTENT%%', render_essay_page(es))
        (ESSAYS_DIR / filename).write_text(page, encoding='utf-8')

    # Listing page.
    featured = render_essay_featured(essays[0]) if essays else '<p class="essays-empty">No essays yet.</p>'
    grid = '\n'.join(render_essay_tile(es) for es in essays[1:])

    hk_now = datetime.now(timezone(timedelta(hours=8)))
    masthead_date = f"{hk_now.strftime('%A')}, {hk_now.day} {hk_now.strftime('%B')} {hk_now.year}, <i>Hong Kong</i>"
    n = len(essays)
    count = f"{n} Dispatch{'es' if n != 1 else ''}"

    index = ESSAYS_INDEX_TEMPLATE.read_text(encoding='utf-8')
    index = index.replace('%%ESSAYS_FEATURED%%', featured)
    index = index.replace('%%ESSAYS_GRID%%', grid)
    index = index.replace('%%MASTHEAD_DATE%%', masthead_date)
    index = index.replace('%%ESSAY_COUNT%%', count)
    ESSAYS_INDEX.write_text(index, encoding='utf-8')

    # Prune stale essay pages (keep index.html).
    for stale in ESSAYS_DIR.glob('*.html'):
        if stale.name != 'index.html' and stale.name not in wanted:
            stale.unlink()

    print(f'Generated essays/index.html + {n} essay page(s)')


def _format_visit_date(d):
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, '%Y-%m-%d').date()
        except ValueError:
            return d
    return f'{d.day} {d.strftime("%B")} {d.year}'


def _visit_slugs(visits):
    seen, slugs = {}, {}
    for v in visits:
        base = slugify(v['title']) or f'visit-{v["id"]}'
        n = seen.get(base, 0) + 1
        seen[base] = n
        slugs[v['id']] = base if n == 1 else f'{base}--{n}'
    return slugs


def render_gallery_visit_tile(visit, artwork_count, slug):
    date_display = _format_visit_date(visit['visit_date'])
    venue = f'<div class="visit-venue">{e(visit["venue"])}</div>' if visit['venue'] else ''
    return (
        f'            <a class="visit-tile" href="{slug}.html">\n'
        f'                <div class="visit-date">{e(date_display)}</div>\n'
        f'                <h3 class="visit-title">{e(visit["title"])}</h3>\n'
        f'                {venue}\n'
        f'                <div class="visit-count">{artwork_count} work{"s" if artwork_count != 1 else ""}</div>\n'
        f'            </a>'
    )


def render_gallery_artwork(art):
    """One artwork card: reference plate (if any) + own photo (if any) + label + notes."""
    imgs = []
    if art['reference_img']:
        imgs.append(
            f'<figure class="artwork-fig artwork-ref">'
            f'<img src="../{e(art["reference_img"])}" alt="Reference reproduction of {e(art["name"])}">'
            f'<figcaption>Reference plate</figcaption></figure>'
        )
    if art['own_photo_img']:
        imgs.append(
            f'<figure class="artwork-fig artwork-mine">'
            f'<img src="../{e(art["own_photo_img"])}" alt="{e(art["name"])}, as seen">'
            f'<figcaption>As I saw it</figcaption></figure>'
        )
    if not imgs:
        imgs.append('<div class="artwork-noimg">No image available</div>')

    name = e(art['name'])
    meta_parts = []
    if art['artist']:
        meta_parts.append(e(art['artist']))
    else:
        meta_parts.append('<em>Unidentified</em>')
    if art['period']:
        meta_parts.append(e(art['period']))
    meta = ' &middot; '.join(meta_parts)

    notes = ''
    if art['my_notes'] and art['my_notes'].strip():
        notes = f'<div class="artwork-notes">{_notes_to_html(art["my_notes"])}</div>'

    return (
        '            <article class="artwork">\n'
        f'                <div class="artwork-imgs">{"".join(imgs)}</div>\n'
        f'                <h3 class="artwork-name">{name}</h3>\n'
        f'                <div class="artwork-meta">{meta}</div>\n'
        f'                {notes}\n'
        '            </article>'
    )


def render_gallery_visit_page(visit, artworks):
    date_display = _format_visit_date(visit['visit_date'])
    venue = f'<div class="visit-detail-venue">{e(visit["venue"])}</div>' if visit['venue'] else ''
    intro = ''
    if visit['notes'] and visit['notes'].strip():
        intro = f'\n            <div class="visit-detail-intro">{_notes_to_html(visit["notes"])}</div>'
    body = '\n'.join(render_gallery_artwork(a) for a in artworks) or \
           '            <p class="visit-empty">No artworks recorded for this visit.</p>'
    return (
        '        <article class="visit-detail">\n'
        f'            <div class="visit-detail-date">{e(date_display)}</div>\n'
        f'            <h1 class="visit-detail-title">{e(visit["title"])}</h1>\n'
        f'            {venue}{intro}\n'
        '            <div class="artwork-list">\n'
        f'{body}\n'
        '            </div>\n'
        '        </article>'
    )


def _generate_galleries(conn):
    """Build galleries/index.html + one galleries/<slug>.html per visit."""
    if not GALLERIES_INDEX_TEMPLATE.exists() or not GALLERY_VISIT_TEMPLATE.exists():
        sys.exit(f'Error: gallery templates not found in {GALLERIES_INDEX_TEMPLATE.parent}')

    GALLERIES_DIR.mkdir(parents=True, exist_ok=True)

    visits = conn.execute(
        'SELECT * FROM gallery_visits ORDER BY visit_date DESC, sort_order, id'
    ).fetchall()
    slugs = _visit_slugs(visits)

    page_tpl = GALLERY_VISIT_TEMPLATE.read_text(encoding='utf-8')
    wanted = set()
    tile_parts = []
    for v in visits:
        artworks = conn.execute(
            'SELECT * FROM gallery_artworks WHERE visit_id=? ORDER BY sort_order, id',
            (v['id'],)
        ).fetchall()
        slug = slugs[v['id']]
        filename = f'{slug}.html'
        wanted.add(filename)
        page = page_tpl.replace('%%VISIT_TITLE%%', e(v['title']))
        page = page.replace('%%VISIT_CONTENT%%', render_gallery_visit_page(v, artworks))
        (GALLERIES_DIR / filename).write_text(page, encoding='utf-8')
        tile_parts.append(render_gallery_visit_tile(v, len(artworks), slug))

    hk_now = datetime.now(timezone(timedelta(hours=8)))
    masthead_date = f"{hk_now.strftime('%A')}, {hk_now.day} {hk_now.strftime('%B')} {hk_now.year}, <i>Hong Kong</i>"
    n = len(visits)
    count = f"{n} Visit{'s' if n != 1 else ''}" if n else 'No visits recorded'

    tiles_html = '\n'.join(tile_parts) or '            <p class="galleries-empty">No visits yet.</p>'

    index = GALLERIES_INDEX_TEMPLATE.read_text(encoding='utf-8')
    index = index.replace('%%VISIT_TILES%%', tiles_html)
    index = index.replace('%%MASTHEAD_DATE%%', masthead_date)
    index = index.replace('%%VISIT_COUNT%%', count)
    GALLERIES_INDEX.write_text(index, encoding='utf-8')

    for stale in GALLERIES_DIR.glob('*.html'):
        if stale.name != 'index.html' and stale.name not in wanted:
            stale.unlink()

    print(f'Generated galleries/index.html + {n} visit page(s)')


def _generate_md(conn):
    lines = [
        '# University Reading Library',
        '**Started: Year 2 of Electronics Engineering**',
        '',
        '---',
        '',
    ]
    all_books = conn.execute('SELECT * FROM books ORDER BY sort_order, id').fetchall()
    by_section = {s: [b for b in all_books if b['section'] == s] for s in SECTIONS}

    for sec in SECTIONS:
        books = by_section[sec]
        if not books:
            continue
        lines.append(f'## {SECTION_NAMES[sec]}')
        lines.append('')
        for i, b in enumerate(books, 1):
            lines.append(f'### {i}. {b["title"]}')
            lines.append(f'**Author:** {b["author"]}  ')
            lines.append(f'**Status:** {STATUS_LABEL[b["status"]]}  ')
            lines.append(f'**My Notes:** {b["my_notes"] or "—"}')
            lines.append('')
            lines.append(f'**AI Notes:** {b["ai_notes"] or "—"}')
            lines.append('')
            lines.append('---')
            lines.append('')

    lines += [
        '## Recommended Reading',
        "*Books suggested by my reading—I'll expand this as patterns emerge.*",
        '',
        '### For Software Development:',
        '- Building Microservices by Sam Newman',
        '- The Pragmatic Programmer by Andrew Hunt & David Thomas',
        '- Code Complete by Steve McConnell',
        '',
        '### For Finance:',
        '- Quantitative Finance for Dummies by Steve Greenberg',
        '- The Intelligent Investor by Benjamin Graham',
        '- A Man for All Markets by Edward O. Thorp',
        '',
        '### For Greater Awareness:',
        '- Thinking, Fast and Slow by Daniel Kahneman',
        '- The Righteous Mind by Jonathan Haidt',
        '- Antifragile by Nassim Nicholas Taleb',
        '',
        '---',
        '',
    ]

    total     = len(all_books)
    read_n    = sum(1 for b in all_books if b['status'] == 'read')
    reading_n = sum(1 for b in all_books if b['status'] == 'reading')
    list_n    = sum(1 for b in all_books if b['status'] == 'list')
    today = date.today()
    lines.append(f"**Last Updated:** {today.strftime('%B')} {today.day}, {today.year}  ")
    lines.append(f'**Total Books:** {total} ({read_n} Read, {reading_n} Reading, {list_n} Reading List)')

    MD_FILE.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Generated {MD_FILE.name}')


def cmd_list(args):
    ensure_schema()
    section_filter = None
    status_filter  = None
    i = 0
    while i < len(args):
        if args[i] == '--section' and i + 1 < len(args):
            section_filter = args[i + 1]; i += 2
        elif args[i] == '--status' and i + 1 < len(args):
            status_filter = args[i + 1]; i += 2
        else:
            i += 1

    query  = 'SELECT * FROM books WHERE 1=1'
    params = []
    if section_filter:
        query += ' AND section=?'; params.append(section_filter)
    if status_filter:
        query += ' AND status=?'; params.append(status_filter)
    query += ' ORDER BY section, sort_order, id'

    conn  = get_db()
    books = conn.execute(query, params).fetchall()
    conn.close()

    if not books:
        print('No books found.')
        return

    print(f'{"ID":<4} {"Title":<52} {"Author":<35} {"Section":<12} {"Status"}')
    print('-' * 116)
    for b in books:
        title  = (b['title'][:50]  + '..') if len(b['title'])  > 52 else b['title']
        author = (b['author'][:33] + '..') if len(b['author']) > 35 else b['author']
        print(f'{b["id"]:<4} {title:<52} {author:<35} {b["section"]:<12} {STATUS_LABEL[b["status"]]}')


def cmd_add():
    ensure_schema()
    print('Add a new book (Ctrl+C to cancel)\n')
    title    = _prompt('Title')
    author   = _prompt('Author')
    section  = _prompt_choice('Section', SECTIONS)
    status   = _prompt_choice('Status', list(STATUS_LABEL.keys()))
    isbn     = _prompt('ISBN (leave blank if none)', required=False)
    my_notes = _prompt('My Notes (leave blank if none)', required=False)
    ai_notes = _prompt('AI Notes (leave blank if none)', required=False)

    conn = get_db()
    max_sort = conn.execute(
        'SELECT MAX(sort_order) FROM books WHERE section=?', (section,)
    ).fetchone()[0] or 0
    conn.execute(
        'INSERT INTO books (title, author, isbn, section, status, my_notes, ai_notes, sort_order) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (title, author, isbn or None, section, status, my_notes or None, ai_notes or None, max_sort + 1)
    )
    conn.commit()
    book_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
    conn.close()
    print(f'\nAdded "{title}" with ID {book_id}')

    if input('Regenerate index.html now? [y/N]: ').strip().lower() == 'y':
        cmd_generate()


def cmd_update(args):
    if not args:
        sys.exit('Usage: python librarian.py update <id>')
    ensure_schema()
    book_id = int(args[0])
    conn = get_db()
    b = conn.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not b:
        sys.exit(f'No book with ID {book_id}')

    print(f'Updating: {b["title"]} (press Enter to keep current value)\n')
    fields = [
        ('title',    'Title',     b['title']),
        ('author',   'Author',    b['author']),
        ('isbn',     'ISBN',      b['isbn'] or ''),
        ('section',  'Section',   b['section']),
        ('status',   'Status',    b['status']),
        ('my_notes', 'My Notes',  b['my_notes'] or ''),
        ('ai_notes', 'AI Notes',  b['ai_notes'] or ''),
        ('local_cover_path', 'Local cover path', b['local_cover_path'] or ''),
    ]

    updates = {}
    for col, label, current in fields:
        val = input(f'{label} [{current}]: ').strip()
        if val:
            updates[col] = val if val != '-' else None

    if updates:
        set_clause = ', '.join(f'{col}=?' for col in updates)
        conn.execute(f'UPDATE books SET {set_clause} WHERE id=?', (*updates.values(), book_id))
        conn.commit()
        print(f'Updated book {book_id}')
    else:
        print('No changes made.')
    conn.close()

    if input('Regenerate index.html now? [y/N]: ').strip().lower() == 'y':
        cmd_generate()


def cmd_remove(args):
    if not args:
        sys.exit('Usage: python librarian.py remove <id>')
    ensure_schema()
    book_id = int(args[0])
    conn = get_db()
    b = conn.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not b:
        sys.exit(f'No book with ID {book_id}')

    if input(f'Remove "{b["title"]}" by {b["author"]}? [y/N]: ').strip().lower() == 'y':
        conn.execute('DELETE FROM books WHERE id=?', (book_id,))
        conn.commit()
        print(f'Removed book {book_id}')
        if input('Regenerate index.html now? [y/N]: ').strip().lower() == 'y':
            cmd_generate()
    else:
        print('Cancelled.')
    conn.close()


def cmd_hero(args):
    if not args:
        sys.exit('Usage: python librarian.py hero <id>')
    ensure_schema()
    book_id = int(args[0])
    conn = get_db()
    b = conn.execute('SELECT * FROM books WHERE id=?', (book_id,)).fetchone()
    if not b:
        sys.exit(f'No book with ID {book_id}')
    if b['status'] != 'reading':
        print(f'Warning: book status is "{b["status"]}", not "reading"')

    print(f'Setting hero fields for: {b["title"]}\n')
    slot         = _prompt_choice('Hero slot', ['lead', 'side', 'bottom'])
    kicker       = _prompt('Kicker (e.g. "Quantitative Finance")')
    headline     = _prompt('Headline')
    deck         = _prompt('Deck (subheadline)')
    byline_extra = _prompt('Byline extra (e.g. "Progress: Halfway through")')
    progress     = _prompt('Progress label (e.g. "Mid-way")')
    body         = _prompt('Story body paragraph (lead only; Enter to skip)', required=False) if slot == 'lead' else None

    max_sort = conn.execute(
        'SELECT MAX(hero_sort) FROM books WHERE hero_slot=?', (slot,)
    ).fetchone()[0] or 0

    conn.execute(
        'UPDATE books SET hero_slot=?, hero_sort=?, hero_kicker=?, hero_headline=?, '
        'hero_deck=?, hero_byline_extra=?, hero_body=?, hero_progress=? WHERE id=?',
        (slot, max_sort + 1, kicker, headline, deck, byline_extra, body or None, progress, book_id)
    )
    conn.commit()
    conn.close()
    print(f'Hero fields set for book {book_id}')

    if input('Regenerate index.html now? [y/N]: ').strip().lower() == 'y':
        cmd_generate()

# ── Helpers ───────────────────────────────────────────────────────────────────

def _prompt(label, required=True):
    while True:
        val = input(f'{label}: ').strip()
        if val or not required:
            return val
        print(f'  {label} is required.')


def _prompt_choice(label, choices):
    choices_str = '/'.join(choices)
    while True:
        val = input(f'{label} [{choices_str}]: ').strip().lower()
        if val in choices:
            return val
        print(f'  Choose one of: {choices_str}')


def _download_cover(isbn, timeout=20):
    """Fetch one Open Library cover by ISBN.

    Returns (data, None) on success, (None, 'missing') when the cover does not
    exist (HTTP 404 or a blank placeholder), or (None, 'unreachable') when the
    host can't be reached (down / timeout / DNS).
    """
    import urllib.request, urllib.error
    # ?default=false → Open Library returns 404 for a missing cover instead of a
    # blank 1×1 placeholder served with HTTP 200.
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
    req = urllib.request.Request(
        url, headers={'User-Agent': 'ArjunArchives/1.0 (cover-cache)'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        # A response (even a 404) means the host is up — just no cover for this ISBN.
        return (None, 'missing' if exc.code == 404 else f'HTTP {exc.code}')
    except Exception:
        return (None, 'unreachable')
    if len(data) < 1000:              # guard against a stray blank placeholder
        return (None, 'missing')
    return (data, None)


def _cache_covers(conn, force=False, fail_fast=False, quiet=False, timeout=20):
    """Download missing Open Library covers into book_covers_additional/ and
    repoint each book's local_cover_path at the saved file. Shared by the
    `cache-covers` command and `generate`.

    Only books with an ISBN are touched; books that already have a local cover
    are skipped unless `force`. With `fail_fast`, the first 'unreachable' result
    stops the run (the host is down — no point timing out on every remaining
    book); the returned dict then carries unreachable=True. `quiet` suppresses
    per-book output. Returns a counts dict.
    """
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    rows = conn.execute(
        "SELECT id, title, isbn, local_cover_path FROM books "
        "WHERE isbn IS NOT NULL AND TRIM(isbn) <> '' "
        "ORDER BY title COLLATE NOCASE"
    ).fetchall()

    counts = {'cached': 0, 'skipped': 0, 'missing': 0, 'failed': 0, 'unreachable': False}
    for b in rows:
        if b['local_cover_path'] and not force:
            counts['skipped'] += 1
            continue
        isbn = b['isbn'].strip()
        data, err = _download_cover(isbn, timeout)
        if err is None:
            rel = f"book_covers_additional/{isbn}.jpg"
            (COVERS_DIR / f"{isbn}.jpg").write_bytes(data)
            conn.execute('UPDATE books SET local_cover_path=? WHERE id=?', (rel, b['id']))
            conn.commit()
            counts['cached'] += 1
            if not quiet:
                print(f'  Cached "{b["title"]}" -> {rel} ({len(data):,} bytes)')
        elif err == 'missing':
            counts['missing'] += 1
            if not quiet:
                print(f'  No cover for "{b["title"]}" (ISBN {isbn})')
        else:  # 'unreachable' or 'HTTP nnn'
            counts['failed'] += 1
            if err == 'unreachable' and fail_fast:
                counts['unreachable'] = True
                break
            if not quiet:
                print(f'  Failed "{b["title"]}" (ISBN {isbn}): {err}')
    return counts


GALLERY_VAULT_DEFAULT = Path.home() / 'Documents' / 'Obsidian Vault' / 'ART'
GALLERY_ATTACH_DEFAULT = Path.home() / 'Documents' / 'Obsidian Vault' / 'Attachments'


def _obs_table(text):
    """Parse Obsidian's two-column pipe-table into {key: value}. Very small parser."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('|') or line.count('|') < 3:
            continue
        parts = [c.strip() for c in line.strip('|').split('|')]
        if len(parts) < 2 or set(parts[0]) <= set('-: '):
            continue
        key = parts[0].strip('* ').strip()
        val = parts[1].strip()
        if key and val:
            out[key.lower()] = val
    return out


def _obs_embeds(text):
    return re.findall(r'!\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]', text)


def _obs_links(text):
    return re.findall(r'(?<!!)\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]', text)


def _extract_arjuns_notes(text):
    m = re.search(r'###\s*Arjun[’\']s Notes\s*\n(.*?)(?=\n###|\n---|\n\[\[Root MOC\]\]|\Z)',
                  text, re.DOTALL)
    if not m:
        return ''
    body = m.group(1)
    body = re.sub(r'<br\s*/?>', '', body)
    body = body.strip()
    return body


def _copy_attachment(name, attach_dir, dest_dir):
    """Find `name` inside attach_dir (case-insensitive) and copy to dest_dir.
    Returns the relative site path (gallery_images/<file>) or None."""
    import shutil
    if not name:
        return None
    target = attach_dir / name
    if not target.exists():
        matches = list(attach_dir.glob(name))
        if not matches:
            lowered = name.lower()
            for p in attach_dir.iterdir():
                if p.name.lower() == lowered:
                    target = p
                    break
            else:
                return None
        else:
            target = matches[0]
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / target.name
    if not dest.exists() or dest.stat().st_size != target.stat().st_size:
        shutil.copy2(target, dest)
    return f'gallery_images/{target.name}'


def _parse_artwork_note(path, attach_dir):
    """Return a dict with name/artist/period/reference_img/own_photo_img/my_notes."""
    text = path.read_text(encoding='utf-8')
    m = re.match(r'#\s*(.+)', text)
    name = (m.group(1).strip() if m else path.stem)
    tbl = _obs_table(text)
    embeds = _obs_embeds(text)

    # Reference plate = first non-"my photo" embed; own photo = first "my photo" embed.
    ref, mine = None, None
    for emb in embeds:
        low = emb.lower()
        if 'my photo' in low or '(mine)' in low:
            mine = mine or emb
        else:
            ref = ref or emb

    artist = tbl.get('artist')
    period = tbl.get('date') or tbl.get('period')
    unidentified = 'unidentified' in name.lower() or bool(re.search(r'not identified', text, re.IGNORECASE))
    if unidentified:
        artist = None

    return {
        'name':          name,
        'artist':        artist,
        'period':        period,
        'reference_img': _copy_attachment(ref, attach_dir, GALLERY_IMAGES_DIR) if ref else None,
        'own_photo_img': _copy_attachment(mine, attach_dir, GALLERY_IMAGES_DIR) if mine else None,
        'my_notes':      _extract_arjuns_notes(text) or None,
        'source_stem':   path.stem,
    }


def _parse_visit_note(path, attach_dir):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'#\s*(.+)', text)
    title = (m.group(1).strip() if m else path.stem)
    tbl = _obs_table(text)

    venue = tbl.get('venue')
    visited = tbl.get('visited') or tbl.get('date') or ''
    d = None
    md = re.search(r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})', visited or path.stem)
    if md:
        try:
            d = datetime.strptime(f'{md.group(1)} {md.group(2)} {md.group(3)}', '%d %B %Y').date()
        except ValueError:
            pass
    if not d:
        md2 = re.search(r'(\d{4})', path.stem)
        d = date(int(md2.group(1)), 1, 1) if md2 else date.today()

    linked = _obs_links(text)
    # Filter out venue/other visit backlinks
    artwork_stems = [l for l in linked
                     if 'MOC' not in l and 'Root' not in l and l != path.stem
                     and '2026' not in l]  # crude: dated visit notes contain year

    return {
        'title':       title,
        'venue':       venue,
        'visit_date':  d,
        'notes':       _extract_arjuns_notes(text) or None,
        'artwork_stems': artwork_stems,
        'source_stem': path.stem,
    }


def cmd_galleries_migrate(args):
    """Populate gallery_visits + gallery_artworks from an Obsidian ART/ folder.

    Idempotent: existing visits/artworks are replaced by source_stem match on title.
    Images are copied into gallery_images/. Run `generate` afterwards.
    """
    vault = Path(args[0]) if args else GALLERY_VAULT_DEFAULT
    attach = Path(args[1]) if len(args) > 1 else GALLERY_ATTACH_DEFAULT
    if not vault.exists():
        sys.exit(f'ART folder not found: {vault}')
    if not attach.exists():
        sys.exit(f'Attachments folder not found: {attach}')

    ensure_schema()
    conn = get_db()

    # Every .md file — classify as visit (matches a dated pattern in filename or
    # links to multiple artworks) vs artwork.
    md_files = sorted(p for p in vault.glob('*.md') if p.name != 'Template.md')

    # First pass: parse artworks by stem.
    artworks_by_stem = {}
    visits = []
    for path in md_files:
        text = path.read_text(encoding='utf-8')
        # Heuristic: a "visit" note has no "Seen at" table row and has an
        # "Objects seen here" / "Works I photographed" / "Works seen here" header.
        if re.search(r'###\s*(Works I photographed|Objects seen here|Works seen here)',
                     text, re.IGNORECASE):
            visits.append(_parse_visit_note(path, attach))
        elif 'MOC' in path.stem or 'Applications and Jobs' in path.stem:
            continue
        else:
            aw = _parse_artwork_note(path, attach)
            artworks_by_stem[path.stem] = aw

    # Wipe and re-insert (idempotent).
    conn.execute('DELETE FROM gallery_artworks')
    conn.execute('DELETE FROM gallery_visits')
    conn.commit()

    for vi, v in enumerate(visits):
        cur = conn.execute(
            'INSERT INTO gallery_visits (title, venue, visit_date, notes, sort_order) '
            'VALUES (?, ?, ?, ?, ?)',
            (v['title'], v['venue'], v['visit_date'].isoformat(), v['notes'], vi)
        )
        visit_id = cur.lastrowid
        for ai, stem in enumerate(v['artwork_stems']):
            aw = artworks_by_stem.get(stem)
            if not aw:
                print(f'  Warning: {v["source_stem"]} references [[{stem}]] but no note found')
                continue
            conn.execute(
                'INSERT INTO gallery_artworks '
                '(visit_id, name, artist, period, reference_img, own_photo_img, my_notes, sort_order) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                (visit_id, aw['name'], aw['artist'], aw['period'],
                 aw['reference_img'], aw['own_photo_img'], aw['my_notes'], ai)
            )
        print(f'  {v["title"]}: {len(v["artwork_stems"])} artwork(s)')
    conn.commit()
    conn.close()
    print(f'\nMigrated {len(visits)} visit(s). Run: python librarian.py generate')


def cmd_cache_covers(args):
    """Download Open Library covers into book_covers_additional/ and repoint each
    book's local_cover_path, so the site no longer depends on
    covers.openlibrary.org at view time (it goes down periodically).

    Books that already have a local cover are left as-is unless --force is given.
    Re-run `generate` afterwards to bake the local paths into the pages.
    """
    ensure_schema()
    conn = get_db()
    c = _cache_covers(conn, force='--force' in args, fail_fast=False, quiet=False)
    print(f'\nCached {c["cached"]}, skipped (already local) {c["skipped"]}, '
          f'no cover {c["missing"]}, failed {c["failed"]}.')
    if c['failed']:
        print('Some downloads failed — if covers.openlibrary.org is unreachable, '
              're-run this once it is back up (cached books are skipped).')
    if c['cached']:
        print('Now run: python librarian.py generate')


# ── Entry point ───────────────────────────────────────────────────────────────

USAGE = """\
Usage: python librarian.py <command> [args]

Commands:
  add              Interactively add a new book
  list             List books  [--section software|engineering|finance|philosophy]
                               [--status read|reading|list]
  update <id>      Edit a book's fields
  remove <id>      Delete a book
  hero <id>        Set newspaper hero fields for a Reading book
  cache-covers     Download Open Library covers locally (--force re-downloads all)
  galleries-migrate  Ingest Obsidian ART/ folder into gallery_visits/artworks
                     [<ART path> [<Attachments path>]]
  generate         Regenerate index.html, library.html, books/*.html, essays/*, galleries/* and library.md
                   (auto-caches new covers first; --no-cache to skip)
"""

def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    cmd  = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == 'add':
        cmd_add()
    elif cmd == 'list':
        cmd_list(args)
    elif cmd == 'update':
        cmd_update(args)
    elif cmd == 'remove':
        cmd_remove(args)
    elif cmd == 'hero':
        cmd_hero(args)
    elif cmd in ('cache-covers', 'cache_covers'):
        cmd_cache_covers(args)
    elif cmd in ('galleries-migrate', 'galleries_migrate'):
        cmd_galleries_migrate(args)
    elif cmd == 'generate':
        cmd_generate(args)
    else:
        print(f'Unknown command: {cmd}\n')
        print(USAGE)
        sys.exit(1)


if __name__ == '__main__':
    main()
