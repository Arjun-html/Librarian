# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

**Arjun's Archives** — a personal reading-library website for a university student (Electrical/Mechanical Engineering and Computer Science). It's a static site with no build step for *viewing* — but the HTML pages are **generated**, not hand-written (see below). Open `index.html` in a browser to view it.

The authoritative design document is **`ClaudeAi_SPEC_v2.md`** (the v2 vision). `SPEC.md` is the v1 baseline, kept for history. When in doubt about intended behaviour, defer to the v2 spec.

### The v2 vision (three sections)

1. **Front page (`index.html`)** — a Financial-Times-style newspaper front page: masthead + strapline, editorial hero featuring currently-reading books, an "About this publication" column, and truncated previews of book entries that link to full per-book pages.
2. **Library (`library.html`)** — every `read`/`reading` book, alphabetical, as cover + title + author + status chip. Each tile links to its own per-book page. `list` (Reading List) books are excluded from the website but stay in the DB.
3. **Essays & Thoughts (`essays/`)** — personal essays. *Design TBD; out of scope until separately specced.*

### Build status (what exists today vs. the v2 roadmap)

- **Built:** front page (`index.html`), the generated **`library.html`** listing, the generated per-book **`books/[slug].html`** pages, `library.md` export, the SQLite source of truth, CLI + Tkinter GUI, dynamic newspaper hero, the front-page **shelf exhibit** (a stacked-bar report chart of the library by section/status — see below), page-turn animation with direction (see below), sync-check hook, masthead strapline + "About" blurb, nav updated to **Front Page | Library | In the Galleries | Essays & Thoughts**, `slugify()` + collision handling (`assign_slugs`), `render_book_tile` / `render_book_page`, and the **In the Galleries** section: two new tables (`gallery_visits`, `gallery_artworks`), `_generate_galleries` producing `galleries/index.html` + `galleries/[slug].html`, and a `galleries-migrate` command that ingests the Obsidian `ART/` folder into the DB. **Utterances comments have been removed.** The hand-authored `archive.html` and `reading-list.html` have been **retired** (deleted) — `library.html` replaces them. Library tiles now link to real per-book pages.
- **Roadmap (not yet built — see v2 spec §6, §12):** front-page `my_notes` previews truncated with a `Read full entry →` link (`render_notes_preview`), the `essays/` section beyond its current index/tile/page render functions.
- The front page no longer has per-section book-card grids — the old `%%BOOKS_software%%` / `%%BOOKS_engineering%%` / `%%BOOKS_finance%%` / `%%BOOKS_philosophy%%` placeholders and `render_book_card` were removed when the hero + exhibit design landed. Do not assume they exist; the front page's only dynamic placeholders today are `%%NEWSPAPER_DYNAMIC%%` (hero), `%%SHELF_EXHIBIT%%` (report chart), `%%MASTHEAD_DATE%%`, and `%%FOOTER_DATE%%`.

Do **not** assume roadmap items exist; verify in the code before referencing them.

## Architecture: content vs. presentation (read this first)

**This is the most important thing to understand about this repo.** Two concerns are deliberately kept in separate files so they never clobber each other:

- **Content** (book data, the newspaper hero text, dates) lives in **`library.db`** (SQLite). It is rendered into the generated HTML + `library.md` by the generator `librarian.py`.
- **Presentation** (all layout, colours, the aged-newsprint texture, the sepia cover filters, the page-flip animation) lives in standalone, hand-edited files: **`styles.css`**, **`app.js`**, **`flip-init.js`**, **`page-transition.js`**, **`html2canvas.min.js`**, and the template skeletons under **`templates/`**.

Generated output (`index.html`, `library.md`, and — once built — `library.html` and everything under `books/`) is a thin skeleton that *links* the presentation files and *holds* the rendered content. **Do not hand-edit generated files**; the next `generate` will overwrite them. (Historically the styling was inline in `index.html` and `generate` repeatedly clobbered it — that is why the split exists.)

### How to make changes

| To change… | Edit… | Then… |
|---|---|---|
| A book's title/author/status/notes/ISBN | `library.db` (via `librarian.py` or the GUI) | `python librarian.py generate` |
| The newspaper hero stories/headlines | `library.db` hero fields (GUI hero form) | `python librarian.py generate` |
| Colours, layout, fonts, textures | `styles.css` | bump its `?v=N` in every template (see below), nothing else |
| Page-flip animation / behaviour | `page-transition.js`, `app.js`, `flip-init.js` | bump `page-transition.js`'s `?v=N` in every template (see below), nothing else |
| Front-page masthead / nav / strapline / about blurb / skeleton | `templates/index_base.html` | `python librarian.py generate` |
| Library-page banner / nav / skeleton | `templates/library_base.html` | `python librarian.py generate` |
| Per-book page masthead / nav / skeleton | `templates/book_base.html` | `python librarian.py generate` |

`generate` only ever writes the generated artifacts. It never touches the presentation files, so editing them is always safe.

### Cache-busting `styles.css` and `page-transition.js`

Both are linked from every template with a manual `?v=N` query string (e.g. `styles.css?v=4`, `page-transition.js?v=8`) purely to bust the browser cache — browsers cache static assets by URL, so editing the file's *content* without changing its *URL* means a returning visitor keeps being served their old cached copy. **Whenever you edit `styles.css` or `page-transition.js`, bump the corresponding `?v=N` in all five `templates/*.html` files** (`index_base.html`, `library_base.html`, `book_base.html`, `essay_base.html`, `essays_index_base.html`) before regenerating. This has silently bitten past sessions more than once — the file was correct on disk but the version tag wasn't bumped, so the change never reached a browser that had already visited.

**Golden rule:** never hand-edit `index.html`, `library.html`, `library.md`, or any file under `books/`.

## The generator (`librarian.py`)

```
python librarian.py add              # interactively add a book
python librarian.py list             # [--section …] [--status …]
python librarian.py update <id>      # edit a book
python librarian.py remove <id>      # delete a book
python librarian.py hero <id>        # set newspaper hero fields for a Reading book
python librarian.py cache-covers     # download Open Library covers locally (--force re-downloads all)
python librarian.py generate         # rebuild generated files from library.db (auto-caches new covers; --no-cache to skip)
```

### Cover caching (offline-proof covers)

Covers normally load from `covers.openlibrary.org` by ISBN at view time, so when that host has an outage every ISBN-based cover blanks out to the "No cover available" fallback. `cache-covers` downloads each book's cover into `book_covers_additional/<isbn>.jpg` and repoints its `local_cover_path` in the DB, so the pages link to local files and no longer depend on Open Library. Books that already have a curated local cover are skipped unless `--force`. `generate` runs the same cache pass automatically (best-effort, quiet) before building: it does nothing once all covers are cached, and bails out fast with a note if the host is unreachable, so it never hangs. Pass `generate --no-cache` to skip it. The shared core is `_cache_covers` / `_download_cover` in `librarian.py`.

`cmd_generate` reads the template(s) under `templates/` and writes the output files:

- **`index.html`** — from `templates/index_base.html`, filling `%%BOOKS_software%%`, `%%BOOKS_engineering%%`, `%%BOOKS_finance%%`, `%%BOOKS_philosophy%%`, `%%NEWSPAPER_DYNAMIC%%`, `%%MASTHEAD_DATE%%`, `%%FOOTER_DATE%%` via `render_book_card` / `render_hero`. `render_hero` derives the banner count ("N Volumes Under Active Review") and the masthead date (current Hong Kong / UTC+8 date) automatically.
- **`library.html`** — `_generate_library` reads `templates/library_base.html` and fills `%%BOOK_TILES%%`, `%%MASTHEAD_DATE%%`, `%%LIBRARY_COUNT%%`. It queries `status IN ('read','reading')` ordered alphabetically by title (`list` books excluded), assigns a stable URL slug per book via `slugify` + `assign_slugs` (collisions get `--2`, `--3`, …), and renders each as a `.book-tile` (`render_book_tile`) linking to `books/[slug].html`.
- **`books/[slug].html`** — `_generate_books` reads `templates/book_base.html` and writes one page per `read`/`reading` book (`render_book_page` fills `%%BOOK_CONTENT%%`, plus `%%BOOK_TITLE%%`). It uses the *same* query + `assign_slugs` as the library, so slugs/filenames match the tile links exactly. Each page shows the large sepia cover, title, author, section label, status chip, and full `my_notes` (no `ai_notes`, no comments), with a `← Back to Library` link. Stale pages (from removed/renamed books) are pruned each run. Asset/links use `../` since the pages live one level deep. **`books/` is entirely generated — never hand-edit it.**
- **`library.md`** — the sectioned Markdown export (`_generate_md`).

`librarian_gui.py` is a Tkinter GUI over the same DB; its "Save + Regenerate" button calls `cmd_generate`.

**`library.md` is generated output too** (an export of the DB) — don't hand-edit it. `library.db` is the sole source of truth; the one-time `BOOKS_DATA`/`migrate` seed has been removed from `librarian.py` now that the DB has diverged from it.

## Sections & book status classes

Sections: `software` (Software Related Books), `engineering` (Engineering & Mathematics), `finance` (Finance), `philosophy` (Greater Awareness & Philosophy).

> The former `quant` / "Quantitative Finance" section was renamed to the `finance` key / "Finance" label (key, DB rows, CHECK constraint, `%%BOOKS_finance%%` placeholder, and template all updated). The hand-authored legacy pages that still carried the old "Quantitative Finance" banner (`archive.html`, `reading-list.html`) have now been retired/deleted, replaced by the generated `library.html`.

| Status | Label | Class | On the website? |
|---|---|---|---|
| Read | Read | `status-read` | yes |
| Reading | Reading | `status-reading` | yes (+ front-page hero) |
| Reading List | Reading List | `status-list` | no — DB/CLI/GUI only |

## Design system

The look is FT broadsheet meets a 1970s/80s corporate annual report — see `styles.css` `:root` for the tokens. Paper stock is FT salmon (`--cream: #fff1e5`, hero band `#fbe4d2`), with warm rules (`--light-taupe`) and a single oxblood accent (`--accent`) for links/hovers — no other colour is added for emphasis. Base type is serif throughout (`Libre Baskerville`); display headings use `var(--display)` (`Newsreader`) rather than a fashion-serif like Playfair, and the masthead alone keeps `IM Fell English`. `.newspaper-content a` is deliberately unstyled (`color: inherit; text-decoration: none`) — no newspaper prints a blue underlined headline; hover affordance comes from the story block, not the link.

Book cover images are **muted plates, not greyscale** — `--plate` (`saturate(0.58) sepia(0.16) contrast(0.95) brightness(1.03)`) pulls colour back toward the paper stock without losing hue or detail, lifting toward `--plate-hover` on hover. This was an explicit correction mid-project: full desaturation was tried and rejected as straining and losing detail, in favour of the muted-but-legible palette real investor-report plates use.

## The shelf exhibit

`render_shelf_exhibit()` in `librarian.py` renders a pure-CSS stacked-bar chart on the front page (`%%SHELF_EXHIBIT%%`, between the hero and the About column): one column per section, segmented by status (read / reading / reading-list), bar heights as inline `style="height:…"` on `.seg` divs — no chart library, no `<canvas>`. It plots **by section and status, not by month** — `date_added` is dominated by the one-off migration date (40 of ~48 rows share one date), so a per-month "volumes read over time" chart would be fabricating a trend that isn't there. If real per-month reading data ever exists, that would be the natural next axis; don't add it speculatively.

## Page-flip direction

`page-transition.js` gives the peel a direction via `depth(url)`, which ranks a URL's place in the site's reading order (front page → Library → book pages → Essays). Navigating deeper peels normally (right edge, sweeping right→left). Navigating back toward the front **mirrors the whole frame**: the snapshot bitmap is flipped once (`mirrored()`) and drawn under a mirrored canvas transform, so the fold sweeps left→right and the curl lifts off the left edge, while the print still reads correctly (the two mirrors cancel). This was a deliberate design request — going "back" should feel like turning backward through the issue, not like the same forward turn playing in reverse.

The animation is skipped entirely under `prefers-reduced-motion: reduce`, and the transient canvas is capped at 1.5x DPR (not the full device ratio) since it only exists on screen for a few hundred milliseconds.

## Book covers

Covers load from Open Library by ISBN: `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`. The `<img>` `onerror` handler hides the image and adds `no-image` to the parent `.book-cover`, showing a "No cover available" fallback. Books with no ISBN use a `local_cover_path` (a file under `book_covers_additional/`) or the `no-image` fallback. Cover images are sepia-toned via CSS (`filter: sepia(0.35) saturate(1.1)` in `styles.css`).

## Sync check hook

`check_sync.py` runs as a PostToolUse hook (configured in `.claude/settings.json`) after edits to `index.html`. It verifies that cover ISBNs in the newspaper hero match the corresponding library cards. Because content now comes from one DB, mismatches shouldn't occur, but the check remains as a guard.

## Adding a new book (correct workflow)

1. `python librarian.py add` (or use the GUI) — enter title, author, section, status, ISBN, notes.
2. If status is **Reading** and it should appear in the newspaper hero: `python librarian.py hero <id>` (or the GUI hero form) to set slot/kicker/headline/deck/progress.
3. `python librarian.py generate` to rebuild the generated files.

Never add a book by hand-editing `index.html` — it is regenerated from the database.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
