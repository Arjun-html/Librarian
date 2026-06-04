#!/usr/bin/env python3
"""
librarian.py — CLI for Arjun's reading library.

Commands:
  migrate          Populate library.db from built-in data (run once)
  add              Interactively add a new book
  list             List books  [--section <s>] [--status <s>]
  update <id>      Edit a book's fields
  remove <id>      Delete a book
  hero <id>        Set newspaper hero fields for a Reading book
  generate         Regenerate index.html, library.html, books/*.html and library.md
"""

import re
import sqlite3
import sys
import html as html_lib
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT          = Path(__file__).parent
DB            = ROOT / 'library.db'
TEMPLATE      = ROOT / 'templates' / 'index_base.html'
LIB_TEMPLATE  = ROOT / 'templates' / 'library_base.html'
BOOK_TEMPLATE = ROOT / 'templates' / 'book_base.html'
INDEX         = ROOT / 'index.html'
LIBRARY       = ROOT / 'library.html'
BOOKS_DIR     = ROOT / 'books'
MD_FILE       = ROOT / 'library.md'

SECTIONS = ['software', 'engineering', 'finance', 'philosophy']
SECTION_NAMES = {
    'software':    'Software Related Books',
    'engineering': 'Engineering & Mathematics',
    'finance':     'Finance',
    'philosophy':  'Greater Awareness & Philosophy',
}
STATUS_LABEL = {'read': 'Read', 'reading': 'Reading', 'list': 'Reading List'}
STATUS_CLASS  = {'read': 'status-read', 'reading': 'status-reading', 'list': 'status-list'}

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


def render_book_card(book):
    cover        = _cover_div(book)
    status_label = STATUS_LABEL[book['status']]
    status_class = STATUS_CLASS[book['status']]

    notes_block = ''
    if book['my_notes'] and book['my_notes'] != '—':
        notes_block = (
            '\n                                <div class="my-notes">'
            f'\n                                    <span class="my-notes-label">My Notes</span>'
            f'\n                                    <div class="my-notes-text">{e(book["my_notes"])}</div>'
            '\n                                </div>'
        )

    ai_block = ''
    if book['ai_notes']:
        ai_block = (
            '\n                                <div class="summary">'
            f'\n                                    <span class="summary-label">About</span>'
            f'\n                                    <div class="summary-text">{e(book["ai_notes"])}</div>'
            '\n                                </div>'
        )

    return (
        f'                <div class="book-card">\n'
        f'                    <div class="book-header">\n'
        f'                        <div class="book-title-group">\n'
        f'                            <div class="book-title">{e(book["title"])}</div>\n'
        f'                            <div class="book-author">{e(book["author"])}</div>\n'
        f'                        </div>\n'
        f'                        <div class="book-status {status_class}">{status_label}</div>\n'
        f'                        <div class="expand-icon">▼</div>\n'
        f'                    </div>\n'
        f'                    <div class="book-details">\n'
        f'                        <div class="book-content">\n'
        f'                            {cover}\n'
        f'                            <div class="book-text">{notes_block}{ai_block}\n'
        f'                            </div>\n'
        f'                        </div>\n'
        f'                    </div>\n'
        f'                </div>'
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
        f'            <a class="book-tile" href="books/{slug}.html">\n'
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
            f'                    <div class="detail-notes-text">{e(book["my_notes"])}</div>\n'
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


def _hero_cover_src(book):
    if book['local_cover_path']:
        return book['local_cover_path']
    if book['isbn']:
        return f"https://covers.openlibrary.org/b/isbn/{book['isbn']}-M.jpg"
    return None


def render_hero(conn):
    """Build section-banner + newspaper-content HTML from books with hero_slot set."""
    books = conn.execute(
        "SELECT * FROM books WHERE status='reading' AND hero_slot IS NOT NULL "
        "ORDER BY CASE hero_slot WHEN 'lead' THEN 0 WHEN 'side' THEN 1 ELSE 2 END, hero_sort"
    ).fetchall()

    n = conn.execute("SELECT COUNT(*) FROM books WHERE status='reading'").fetchone()[0]
    volume_word = f"{n} Volume{'s' if n != 1 else ''}"
    banner = f'        <div class="section-banner">{volume_word} Under Active Review</div>'

    lead    = [b for b in books if b['hero_slot'] == 'lead']
    sides   = [b for b in books if b['hero_slot'] == 'side']
    bottoms = [b for b in books if b['hero_slot'] == 'bottom']

    top_parts = []
    for b in lead:
        src = _hero_cover_src(b)
        img = f'<img src="{e(src)}" alt="{e(b["title"])}" onerror="this.style.display=\'none\'">' if src else ''
        body = f'\n                    <p class="story-body">{e(b["hero_body"])}</p>' if b['hero_body'] else ''
        top_parts.append(
            f'                <!-- LEAD STORY: {e(b["title"])} -->\n'
            f'                <div class="story-lead">\n'
            f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
            f'                    <div class="story-img-lead">\n'
            f'                        {img}\n'
            f'                    </div>\n'
            f'                    <h2 class="story-headline-lead">{e(b["hero_headline"] or b["title"])}</h2>\n'
            f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
            f'                    <div class="story-byline">By {e(b["author"])} &bull; {e(b["hero_byline_extra"] or "")}</div>{body}\n'
            f'                    <span class="story-progress">&#9998;&nbsp; {e(b["hero_progress"] or "")}</span>\n'
            f'                </div>'
        )

    for b in sides:
        src = _hero_cover_src(b)
        img = f'<img src="{e(src)}" alt="{e(b["title"])}" onerror="this.style.display=\'none\'">' if src else ''
        top_parts.append(
            f'                <div class="story-side">\n'
            f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
            f'                    <div class="story-img-sm">\n'
            f'                        {img}\n'
            f'                    </div>\n'
            f'                    <h3 class="story-headline">{e(b["hero_headline"] or b["title"])}</h3>\n'
            f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
            f'                    <div class="story-byline">By {e(b["author"])} &bull; {e(b["hero_byline_extra"] or "")}</div>\n'
            f'                    <span class="story-progress">&#9998;&nbsp; {e(b["hero_progress"] or "")}</span>\n'
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
            bottom_parts.append(
                f'                <div class="story-bottom">\n'
                f'                    <div class="story-kicker">{e(b["hero_kicker"] or "")}</div>\n'
                f'                    <div class="story-img-sm">\n'
                f'                        {img}\n'
                f'                    </div>\n'
                f'                    <h3 class="story-headline-sm">{e(b["hero_headline"] or b["title"])}</h3>\n'
                f'                    <div class="story-deck">{e(b["hero_deck"] or "")}</div>\n'
                f'                    <div class="story-byline">By {e(b["author"])} &bull; {e(b["hero_byline_extra"] or "")}</div>\n'
                f'                    <span class="story-progress">&#9998;&nbsp; {e(b["hero_progress"] or "")}</span>\n'
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

def cmd_generate():
    ensure_schema()
    if not TEMPLATE.exists():
        sys.exit(f'Error: template not found at {TEMPLATE}')

    conn = get_db()
    template = TEMPLATE.read_text(encoding='utf-8')

    template = template.replace('%%NEWSPAPER_DYNAMIC%%', render_hero(conn))

    # Masthead date: current date in Hong Kong (UTC+8), e.g. "Sunday, 26 June 2026, <i>Hong Kong</i>"
    hk_now = datetime.now(timezone(timedelta(hours=8)))
    masthead_date = f"{hk_now.strftime('%A')}, {hk_now.day} {hk_now.strftime('%B')} {hk_now.year}, <i>Hong Kong</i>"
    template = template.replace('%%MASTHEAD_DATE%%', masthead_date)

    for sec in SECTIONS:
        books = conn.execute(
            'SELECT * FROM books WHERE section=? ORDER BY sort_order, id', (sec,)
        ).fetchall()
        cards = '\n'.join(render_book_card(b) for b in books)
        template = template.replace(f'%%BOOKS_{sec}%%', cards)

    today = date.today()
    template = template.replace('%%FOOTER_DATE%%', f"{today.strftime('%B')} {today.day}, {today.year}")

    INDEX.write_text(template, encoding='utf-8')
    print(f'Generated {INDEX.name}')

    _generate_library(conn)
    _generate_books(conn)
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


def cmd_migrate(force=False):
    ensure_schema()
    conn = get_db()
    existing = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    if existing > 0 and not force:
        sys.exit(f'Database already has {existing} books. Use --force to overwrite.')
    if force:
        conn.execute('DELETE FROM books')
        conn.commit()

    for b in BOOKS_DATA:
        conn.execute(
            '''INSERT INTO books
               (title, author, isbn, section, status, my_notes, ai_notes, sort_order,
                hero_slot, hero_sort, hero_kicker, hero_headline, hero_deck,
                hero_byline_extra, hero_body, hero_progress, local_cover_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                b['title'], b['author'], b.get('isbn'), b['section'], b['status'],
                b.get('my_notes'), b.get('ai_notes'), b.get('sort_order', 0),
                b.get('hero_slot'), b.get('hero_sort', 0), b.get('hero_kicker'),
                b.get('hero_headline'), b.get('hero_deck'), b.get('hero_byline_extra'),
                b.get('hero_body'), b.get('hero_progress'), b.get('local_cover_path'),
            )
        )

    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
    conn.close()
    print(f'Migrated {count} books into {DB.name}')


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

# ── Book data for migrate ─────────────────────────────────────────────────────

BOOKS_DATA = [
    # ── Software Related Books ────────────────────────────────────────────────
    {
        'title': 'Python for Finance', 'author': 'Yves Hilpisch',
        'isbn': '9781492024330', 'section': 'software', 'status': 'reading', 'sort_order': 1,
        'my_notes': 'I am halfway through, good book that clearly shows what resources do and need in python',
        'ai_notes': 'A comprehensive guide to financial analysis using Python. Covers data analysis, visualization, and algorithmic trading. Practical approach to implementing financial concepts in Python, making it accessible for practitioners.',
        'hero_slot': 'side', 'hero_sort': 1,
        'hero_kicker': 'Quantitative Finance',
        'hero_headline': 'Halfway Through Hilpisch: Python Meets the Trading Desk',
        'hero_deck': 'A practical synthesis of financial theory and computation for the modern practitioner',
        'hero_byline_extra': 'Progress: Halfway through',
        'hero_progress': 'Mid-way',
    },
    {
        'title': 'Java Software Solutions', 'author': 'Lewis J. Loftus',
        'isbn': '9780134462011', 'section': 'software', 'status': 'reading', 'sort_order': 2,
        'my_notes': 'Almost finished the book, was doing it for my java course this semester, even a middle schooler can read and work through this book',
        'ai_notes': 'An introductory Java programming textbook that emphasizes problem-solving and object-oriented programming concepts. Known for its clear explanations, detailed examples, and approachable style that makes it accessible even to beginners.',
        'hero_slot': 'bottom', 'hero_sort': 1,
        'hero_kicker': 'Software Engineering',
        'hero_headline': 'Java Solutions Nearing Completion: Object Orientation at Last Conquered',
        'hero_deck': 'Semester coursework companion nears its final pages',
        'hero_byline_extra': 'Progress: Almost finished',
        'hero_progress': 'Almost done',
    },
    {
        'title': 'Designing Data-Intensive Applications', 'author': 'Martin Kleppmann',
        'isbn': '9781449373320', 'section': 'software', 'status': 'list', 'sort_order': 3,
        'ai_notes': 'A deep dive into the principles and architecture of modern distributed systems. Covers databases, data processing, messaging systems, and distributed architectures. Essential reading for understanding how to build scalable systems that handle massive amounts of data.',
    },
    {
        'title': 'Computer Architecture', 'author': 'John L. Hennessy & David A. Patterson',
        'isbn': '9780128119051', 'section': 'software', 'status': 'list', 'sort_order': 4,
        'ai_notes': 'The definitive text on computer architecture covering processor design, memory hierarchies, parallelism, and system organization. Known for its rigorous approach and comprehensive treatment of both classical and modern architectural concepts.',
    },
    {
        'title': 'Python for Data Analysis', 'author': 'Wes McKinney',
        'isbn': '9781491957660', 'section': 'software', 'status': 'list', 'sort_order': 5,
        'ai_notes': 'Practical guide to data manipulation, cleaning, and analysis using Python with pandas library. Covers data structures, handling missing data, time series, and statistical analysis. Essential for anyone working with data in Python.',
    },

    # ── Engineering & Mathematics ─────────────────────────────────────────────
    {
        'title': 'Fundamentals of Electric Circuits',
        'author': 'Charles K. Alexander & Matthew N.O. Sadiku',
        'isbn': '9780078028229', 'section': 'engineering', 'status': 'read', 'sort_order': 1,
        'my_notes': 'Worked through a lot of this book for a university course',
        'ai_notes': "A comprehensive textbook covering circuit analysis fundamentals including Ohm's law, Kirchhoff's laws, nodal analysis, mesh analysis, and AC circuit analysis. Uses systematic problem-solving approaches with practical applications.",
    },
    {
        'title': 'Reducing Traffic Injury', 'author': 'G.W. Trinica',
        'section': 'engineering', 'status': 'read', 'sort_order': 2,
        'my_notes': 'Had to read this one for my internship at a traffic analysis research firm',
        'ai_notes': 'Focuses on methods and strategies for reducing traffic injuries and fatalities. Covers traffic safety engineering, human factors, and data analysis for identifying risk factors and implementing interventions.',
    },
    {
        'title': 'Signals and Linear Systems',
        'author': 'Alan V. Oppenheim & Alan S. Willsky',
        'local_cover_path': 'book_covers_additional/signals_and_systems.jpg',
        'section': 'engineering', 'status': 'read', 'sort_order': 3,
        'my_notes': 'Amazing book I worked through for my course in university with the same name. Really interested in building something that involves these topics',
        'ai_notes': 'A comprehensive treatment of continuous-time and discrete-time signals and linear systems. Covers Fourier analysis, Laplace transforms, Z-transforms, and their applications. Fundamental for signal processing and communications.',
    },
    {
        'title': 'Digital Design', 'author': 'Morris Mano',
        'isbn': '9780131989245', 'section': 'engineering', 'status': 'list', 'sort_order': 4,
        'ai_notes': 'Classic introductory textbook on digital logic design and computer organization. Covers Boolean algebra, combinational circuits, sequential circuits, and the design of digital systems from logic gates to complete processors.',
    },
    {
        'title': 'Microelectronic Circuits',
        'author': 'Adel S. Sedra & Kenneth C. Smith',
        'local_cover_path': 'book_covers_additional/Microelectronics__82622.jpg',
        'section': 'engineering', 'status': 'list', 'sort_order': 5,
        'ai_notes': 'Comprehensive treatment of analog and digital integrated circuits. Covers transistor operation, amplifier design, frequency response, and feedback systems. Essential for understanding electronic design at the component level.',
    },
    {
        'title': 'Bayesian Statistics the Fun Way', 'author': 'Will Kurt',
        'isbn': '9781593279288', 'section': 'engineering', 'status': 'list', 'sort_order': 6,
        'ai_notes': "An accessible introduction to Bayesian statistics using intuitive examples and visualizations. Covers probability, Bayes' theorem, and practical applications without heavy mathematical notation. Great for building intuition.",
    },
    {
        'title': 'The Elements of Statistical Learning',
        'author': 'Trevor Hastie, Robert Tibshirani & Jerome Friedman',
        'isbn': '9780387848587', 'section': 'engineering', 'status': 'list', 'sort_order': 7,
        'ai_notes': 'A comprehensive reference on supervised and unsupervised learning methods. Covers regression, classification, tree-based methods, boosting, neural networks, and high-dimensional problems. Rigorous mathematical treatment with practical examples.',
    },
    {
        'title': 'Finite Markov Chains',
        'author': 'John G. Kemeny & J. Laurie Snell',
        'section': 'engineering', 'status': 'list', 'sort_order': 8,
        'ai_notes': 'Mathematical treatment of finite-state Markov chains covering transition probabilities, steady-state distributions, and applications. Fundamental for understanding stochastic processes and their applications in various fields.',
    },
    {
        'title': 'Pleasures of Probability', 'author': 'Richard Isaac',
        'isbn': '9780387978840', 'section': 'engineering', 'status': 'reading', 'sort_order': 9,
        'my_notes': 'Covered the first few chapters',
        'ai_notes': 'An intuitive introduction to probability theory emphasizing conceptual understanding. Uses games, puzzles, and real-world examples to build probability intuition. Accessible yet mathematically sound.',
        'hero_slot': 'bottom', 'hero_sort': 2,
        'hero_kicker': 'Mathematics',
        'hero_headline': 'Isaac Illuminates Probability: A Gentle Walk Through the Landscape of Chance',
        'hero_deck': 'First chapters reveal an author who prizes wonder over rigor',
        'hero_byline_extra': 'Progress: First chapters covered',
        'hero_progress': 'Just begun',
    },
    {
        'title': 'Mathematical Introduction to Linear Programming and Game Theory',
        'author': 'Louis J. Billera & Susan Ott',
        'section': 'engineering', 'status': 'list', 'sort_order': 10,
        'ai_notes': 'Introduction to optimization theory and game theory with emphasis on mathematical rigor. Covers linear programming, simplex method, duality, and applications in game-theoretic settings.',
    },
    {
        'title': 'Why Math?', 'author': 'R.D. Driver',
        'section': 'engineering', 'status': 'list', 'sort_order': 11,
        'ai_notes': 'Explores the fundamental reasons why mathematics works and its applications across science and engineering. Discusses mathematical modeling and the philosophy behind mathematical thinking.',
    },
    {
        'title': 'Linear Algebra Done Right', 'author': 'Sheldon Axler',
        'isbn': '9783319110790', 'section': 'engineering', 'status': 'list', 'sort_order': 12,
        'ai_notes': 'A modern approach to linear algebra emphasizing understanding over computation. Covers vector spaces, linear transformations, eigenvalues, and inner product spaces. Known for its clear exposition and novel insights.',
    },

    # ── Finance ───────────────────────────────────────────────────────────────
    {
        'title': 'A Practical Guide to Quantitative Finance Interviews',
        'author': 'Xinfeng Zhou',
        'local_cover_path': 'book_covers_additional/A Practical Guide to Quantitative Finance Interviews.jpg',
        'section': 'finance', 'status': 'reading', 'sort_order': 1,
        'my_notes': 'Almost done with the brainteaser sections',
        'ai_notes': 'A practical resource for preparing for quantitative finance job interviews. Covers probability, statistics, derivatives pricing, and brainteasers commonly asked in interviews at hedge funds and trading firms.',
        'hero_slot': 'bottom', 'hero_sort': 3,
        'hero_kicker': 'Interview Preparation',
        'hero_headline': "Zhou's Brainteaser Section: The Quant Interview Gauntlet, Underway",
        'hero_deck': 'Mental arithmetic and probability puzzles designed to separate the prepared from the hopeful',
        'hero_byline_extra': 'Progress: Brainteaser sections',
        'hero_progress': 'Brainteasers',
    },
    {
        'title': 'A Random Walk Down Wall Street', 'author': 'Burton G. Malkiel',
        'isbn': '9780393330335', 'section': 'finance', 'status': 'read', 'sort_order': 2,
        'my_notes': 'Finished the book, found it nice that he gave due respect to every method before absolutely blasting their returns compared to the buy and hold',
        'ai_notes': 'A classic critique of active vs. passive investing. Covers market efficiency, stock valuation methods, and technical analysis, ultimately advocating for index investing. Balanced in acknowledging various approaches before discussing their relative performance.',
    },
    {
        'title': 'The Black Swan', 'author': 'Nassim Nicholas Taleb',
        'isbn': '9780679604181', 'section': 'finance', 'status': 'read', 'sort_order': 3,
        'my_notes': 'Read it in year 1, gave my first introduction into how do people think about risk',
        'ai_notes': 'Explores the impact of rare, unpredictable events (black swans) on society and markets. Challenges conventional thinking about probability and risk, emphasizing the importance of thinking about tail events and their extreme impact.',
    },
    {
        'title': 'Options, Volatility and Pricing', 'author': 'Sheldon Natenberg',
        'isbn': '9780071818773', 'section': 'finance', 'status': 'reading', 'sort_order': 4,
        'my_notes': "Only the last two chapters left. Found the book really interesting and loved the concepts of how volatility, the greeks affect an option's price, but couldn't really find a way how I can use these techniques of options trading without working at one of the prop firms or financial institutions",
        'ai_notes': "Comprehensive guide to options trading and pricing. Covers option mechanics, the greeks (delta, gamma, vega, theta), volatility concepts, and practical trading strategies. Written from a trader's perspective.",
        'hero_slot': 'side', 'hero_sort': 2,
        'hero_kicker': 'Derivatives',
        'hero_headline': "Natenberg Nears Conclusion: Volatility's Final Secrets Await",
        'hero_deck': 'Advanced options theory approaching its denouement — the last two chapters hold the payoff',
        'hero_byline_extra': 'Progress: Last two chapters',
        'hero_progress': 'Final stretch',
    },
    {
        'title': 'Flash Boys', 'author': 'Michael Lewis',
        'isbn': '9780393351590', 'section': 'finance', 'status': 'read', 'sort_order': 5,
        'my_notes': 'Amazing book, showed a lot of insight into how high frequency thinking works and how picks and shovels work',
        'ai_notes': 'Investigative narrative about high-frequency trading and its impact on markets. Exposes the arms race for speed advantage and discusses the hidden realities of modern electronic markets, with focus on the infrastructure and competitive dynamics.',
    },
    {
        'title': 'The Man Who Solved the Markets', 'author': 'Gregory Zuckerman',
        'isbn': '9780735217980', 'section': 'finance', 'status': 'read', 'sort_order': 6,
        'my_notes': 'Gave a lot of motivation in the first half when learning about Jim Simons journey and a lot of horror in the second half when I saw what his underlings did with all the money - get their politicians in. Showed that you need to be an active thinker',
        'ai_notes': 'Biography of Jim Simons and the Renaissance Technologies hedge fund. Chronicles his journey from pure mathematician to creating one of the most successful quant funds. Also covers the ethical complexities and personal consequences of extreme wealth and power.',
    },
    {
        'title': 'The Little Book of Common Sense Investing', 'author': 'John C. Bogle',
        'isbn': '9781119404507', 'section': 'finance', 'status': 'list', 'sort_order': 7,
        'ai_notes': 'Investment philosophy focused on low-cost index investing for long-term wealth building. Emphasizes the power of compound returns and the importance of minimizing fees. Written by the founder of Vanguard.',
    },
    {
        'title': 'The General Theory of Employment, Interest and Money',
        'author': 'John Maynard Keynes',
        'isbn': '9780230007468', 'section': 'finance', 'status': 'list', 'sort_order': 8,
        'ai_notes': 'Foundational work in macroeconomics that challenged classical economics. Introduces concepts of aggregate demand, multiplier effects, and the role of government spending in economic cycles. Dense but essential for understanding modern economics.',
    },
    {
        'title': 'Options, Futures and Other Derivatives', 'author': 'John C. Hull',
        'isbn': '9780133456318', 'section': 'finance', 'status': 'list', 'sort_order': 9,
        'ai_notes': 'Standard reference for derivatives pricing and risk management. Covers binomial models, Black-Scholes formula, exotic options, interest rate derivatives, and credit derivatives. Mathematical rigor with practical applications.',
    },
    {
        'title': 'Inside the Black Box: A Simple Guide to Systematic Trading',
        'author': 'Rishi Narang',
        'local_cover_path': 'book_covers_additional/inside_the_black_box.jpg',
        'section': 'finance', 'status': 'list', 'sort_order': 10,
        'ai_notes': 'Practical guide to quantitative and algorithmic trading. Covers systematic approach to developing trading strategies, backtesting, risk management, and implementation challenges. Balances theory with real-world considerations.',
    },

    # ── Greater Awareness & Philosophy ────────────────────────────────────────
    {
        'title': 'The Coddling of the American Mind',
        'author': 'Greg Lukianoff & Jonathan Haidt',
        'isbn': '9780735224919', 'section': 'philosophy', 'status': 'read', 'sort_order': 1,
        'my_notes': "Read it in year 1, recommended to me by Ariel, can't say it opened my eyes on what was happening in colleges around the world because I kind of knew but helped me understand it better",
        'ai_notes': 'Examines the decline of mental resilience in American youth and its relationship to educational and parenting practices. Argues that overprotection and cognitive distortions limit the development of coping skills and emotional maturity.',
    },
    {
        'title': 'The Prize: The Epic Quest for Oil, Money & Power',
        'author': 'Daniel Yergin',
        'local_cover_path': 'book_covers_additional/The_Prize_-_The_Epic_Quest_for_Oil,_Money,_and_Power.jpg',
        'section': 'philosophy', 'status': 'reading', 'sort_order': 2,
        'my_notes': "700 pages in, reading in year 2, such an interesting history of oil, and how countries on both sides weren't really saints or devils",
        'ai_notes': 'Comprehensive history of the oil industry from its origins to the late 1980s. Covers geopolitics, economic interests, and the complex relationships between nations, corporations, and individuals in the struggle for control of petroleum resources.',
        'hero_slot': 'lead', 'hero_sort': 1,
        'hero_kicker': 'History & Economics',
        'hero_headline': "Seven Hundred Pages Into Yergin's Epic: Oil, Power, and the Making of the Modern World",
        'hero_deck': "A sweeping chronicle of petroleum's grip on civilisation, read alongside markets coursework — where history and financial theory converge",
        'hero_byline_extra': 'Progress: 700 pages in',
        'hero_body': "At seven hundred pages, Daniel Yergin’s Pulitzer Prize-winning account of the global oil industry remains the definitive text on how petroleum shaped geopolitics, warfare, and the modern economy. The reader encounters empires built and toppled on the price of crude, deals struck in smoky boardrooms from Texas to Tehran, and a world perpetually remade by whoever controls the spigot. Indispensable for anyone who wishes to understand where financial markets truly come from.",
        'hero_progress': '700 pages in of 912',
    },
    {
        'title': 'How to Become a Straight-A Student', 'author': 'Cal Newport',
        'isbn': '9780767922715', 'section': 'philosophy', 'status': 'read', 'sort_order': 3,
        'my_notes': 'Read it second semester, year 1, I keep going back to refresh the tips',
        'ai_notes': 'Practical study techniques based on interviews with high-achieving students. Covers note-taking strategies, test preparation, time management, and academic planning. Focused on working smarter rather than harder.',
    },
    {
        'title': 'Sun and Steel', 'author': 'Yukio Mishima',
        'local_cover_path': 'book_covers_additional/sun_and_steel.jpg',
        'section': 'philosophy', 'status': 'read', 'sort_order': 4,
        'my_notes': 'Very invigorating book, but almost made me laugh at times with how contrived Mishima makes his own self out to be',
        'ai_notes': "Autobiographical essay exploring Mishima's philosophy of the body, aesthetics, and martial spirit. Reflects on his transformation from intellectual to bodybuilder and his search for meaning through physical discipline and beauty.",
    },
    {
        'title': 'Cows, Pigs, Wars, and Witches', 'author': 'Marvin Harris',
        'isbn': '9780679724681', 'section': 'philosophy', 'status': 'read', 'sort_order': 5,
        'my_notes': 'Really interesting book I read in my year 1, still remember the stark feelings created by the cargo cults and how we are often blind to what reality is',
        'ai_notes': 'Anthropological exploration of cultural practices and beliefs from a materialist perspective. Explains seemingly irrational behaviors (like Hindu taboos on cattle) through practical and economic reasoning, challenging assumptions about human irrationality.',
    },
    {
        'title': 'Sapiens: A Brief History of Humankind', 'author': 'Yuval Noah Harari',
        'isbn': '9780062316097', 'section': 'philosophy', 'status': 'read', 'sort_order': 6,
        'my_notes': 'Interesting book, I knew a lot of it even before reading',
        'ai_notes': "Big-picture narrative of human history covering cognitive revolution, agricultural revolution, and scientific revolution. Traces how humans went from unimportant animals to dominant species, and explores the myths and structures that hold civilization together.",
    },
    {
        'title': "Maus: A Survivor's Tale", 'author': 'Art Spiegelman',
        'isbn': '9780394747231', 'section': 'philosophy', 'status': 'read', 'sort_order': 7,
        'my_notes': 'Nice story with cool visuals',
        'ai_notes': "Groundbreaking graphic novel depicting the author's father's experiences as a Holocaust survivor. Told through comics with Jews portrayed as mice and Nazis as cats, blending personal narrative with historical testimony in an innovative visual medium.",
    },
    {
        'title': 'The Molecule of More',
        'author': 'Daniel Z. Lieberman & Michael E. Long',
        'isbn': '9781948836586', 'section': 'philosophy', 'status': 'read', 'sort_order': 8,
        'my_notes': 'Really good book, I loved the sections where they talk about the various hormones and how the different hormones give us different sort of pleasures. Additionally, the two different types of dopamines gave me a lot of clarity',
        'ai_notes': 'Neuroscience-based exploration of human behavior through the lens of dopamine and other neurochemicals. Explains how different neurochemical systems drive desire, addiction, social bonding, and satisfaction, providing insight into human motivation.',
    },
    {
        'title': 'The Stranger', 'author': 'Albert Camus',
        'isbn': '9780679720201', 'section': 'philosophy', 'status': 'read', 'sort_order': 9,
        'my_notes': "Very somber book, I appreciate the quality of writing and the way Camus describes the town and the scenes, painting a very vivid picture, but don't particularly agree with, or feel enthralled by the ending",
        'ai_notes': "Existential novel about an emotionally detached man's indifferent response to his mother's death and his subsequent trial. Explores themes of absurdism, alienation, and society's demand for conventional emotional expression and meaning.",
    },
    {
        'title': 'The Alchemist', 'author': 'Paulo Coelho',
        'isbn': '9780062315007', 'section': 'philosophy', 'status': 'read', 'sort_order': 10,
        'my_notes': 'Amazing book, warms my heart whenever I read through it, gave me goosebumps the first time I read it',
        'ai_notes': "Philosophical parable following a shepherd boy's journey in search of treasure. Emphasizes following personal legends, listening to the heart, and trusting in destiny. A meditation on purpose, meaning, and spiritual fulfillment.",
    },
    {
        'title': 'Competitive Strategy', 'author': 'Michael E. Porter',
        'isbn': '9780684841489', 'section': 'philosophy', 'status': 'list', 'sort_order': 11,
        'ai_notes': "Seminal work on business strategy examining how companies compete and maintain advantage. Introduces frameworks like Porter's Five Forces and generic strategies. Essential for understanding strategic positioning in industries.",
    },
    {
        'title': 'I, Robot', 'author': 'Isaac Asimov',
        'isbn': '9780553382563', 'section': 'philosophy', 'status': 'list', 'sort_order': 12,
        'ai_notes': 'Influential science fiction short story collection exploring artificial intelligence and ethics. Presents Asimov\'s "Three Laws of Robotics" and examines their implications through various scenarios, raising questions about machine consciousness and morality.',
    },
    {
        'title': 'Amusing Ourselves to Death', 'author': 'Neil Postman',
        'isbn': '9780143036531', 'section': 'philosophy', 'status': 'list', 'sort_order': 13,
        'ai_notes': 'Media criticism examining how television transformed American culture and discourse. Argues that entertainment-based media undermines rational thought and serious engagement with important issues, creating a culture prioritizing amusement over depth.',
    },
]

# ── Entry point ───────────────────────────────────────────────────────────────

USAGE = """\
Usage: python librarian.py <command> [args]

Commands:
  migrate          Populate library.db from built-in data (run once; --force to reset)
  add              Interactively add a new book
  list             List books  [--section software|engineering|finance|philosophy]
                               [--status read|reading|list]
  update <id>      Edit a book's fields
  remove <id>      Delete a book
  hero <id>        Set newspaper hero fields for a Reading book
  generate         Regenerate index.html, library.html, books/*.html and library.md
"""

def main():
    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(0)

    cmd  = sys.argv[1].lower()
    args = sys.argv[2:]

    if cmd == 'migrate':
        cmd_migrate(force='--force' in args)
    elif cmd == 'add':
        cmd_add()
    elif cmd == 'list':
        cmd_list(args)
    elif cmd == 'update':
        cmd_update(args)
    elif cmd == 'remove':
        cmd_remove(args)
    elif cmd == 'hero':
        cmd_hero(args)
    elif cmd == 'generate':
        cmd_generate()
    else:
        print(f'Unknown command: {cmd}\n')
        print(USAGE)
        sys.exit(1)


if __name__ == '__main__':
    main()
