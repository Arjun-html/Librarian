# Project Specification — Arjun's Archives (Claude Librarian)

*A complete A‑to‑Z technical and design specification of the personal reading‑library website.*

**Spec version:** 2.4 — housekeeping pass: stale §0 roadmap items cleared, `ai_notes` fate resolved (removed), `render_book_card()` dead code noted for cleanup, §14 GUI status line corrected to include essays, §19 constraint added for essay slug stability.

---

## 0. Current Implementation Status (read this first)

The v2.0 draft was written partly aspirationally. This is what is **actually in the repository today**:

### ✅ Built and shipping
- Front page (`index.html`), generated from `templates/index_base.html` + `library.db`.
- Generated **`library.html`** — alphabetical grid of `.book-tile`s for every `read`/`reading` book, each linking to its per-book page. Grid is **capped at 4 columns**, responsive down to 2.
- Generated **`books/[slug].html`** per-book pages (large `-L` sepia cover, title, author, section label, status chip, full `my_notes`, `← Back to Library`). Stale pages are pruned each run.
- `slugify()` + `assign_slugs()` with `--2`, `--3` collision suffixes; library tiles and book filenames share one query so links always match.
- `library.md` export; SQLite source of truth; CLI (`librarian.py`) + Tkinter GUI (`librarian_gui.py`).
- Dynamic newspaper hero (auto volume count + Hong Kong date), aged-newsprint styling, sepia covers.
- Single bespoke **page-turn animation** (`page-transition.js`, cache-buster `?v=7`).
- Masthead strapline + "About this Publication" aside + nav (**Front Page | Library | Essays & Thoughts**) — all **static text in the templates**, not DB-driven placeholders.
- **Utterances comments fully removed.** Hand-authored `archive.html` / `reading-list.html` **retired** (deleted).
- PostToolUse sync-check hook (`check_sync.py`).
- Front-page tab title is **"Arjun's Dispatch"**; masthead name is **"The Arjun Dispatch"**; site/nav logo is **"Arjun's Archives"**.

### ❌ Deliberately not built (decided against)
- **Truncated `my_notes` preview + `Read full entry →` link** on the front page — superseded by the v2.2 decision to remove the per-section card grid entirely. The front page hero links directly to per-book pages instead.
- **`%%ABOUT_BLURB%%` / `%%MASTHEAD_STRAPLINE%%` as DB-driven placeholders** — static text in templates is intentional; no dynamic substitution needed.

### ❌ Reverted (not current)
- **Three randomised page-turn variants** (`slowDramatic` / `mediumCrisp` / `snapWithPeel`) — built (cache-buster `v6`), then reverted to single transition (`v7`). May be revisited.

### 🗑️ Dead code to clean up
- **`render_book_card()`** definition remains in `librarian.py` but is no longer called anywhere. Safe to delete.
- **`ai_notes` field** — still in `library.db` and still populated, but no longer displayed anywhere on the site (the front-page card grid that showed it was removed in v2.2; per-book pages never showed it). **Decision: remove from display permanently.** The field can stay in the DB as a reference without being rendered.

### ✅ v2.2 work items — all shipped (June 2026)

All three v2.2 tasks are now implemented, generated, and verified (including a live browser click-through):

1. **Markdown rendering in `my_notes`** — **Done.** `librarian.py` imports `markdown` (guarded; `_markdown = None` on `ImportError`) and a new `_notes_to_html()` helper pipes `my_notes` through `markdown.markdown(text, extensions=['extra'])` inside `render_book_page()`, falling back to blank-line (`\n\n`) splitting into HTML-escaped `<p>` chunks when the package is absent. Bold/italic/headings/lists/paragraph breaks now render on book pages. Dependency `Markdown 3.10.2` installed (see §17). No GUI change needed.

2. **Per-section book-card grid removed from `index.html`** — **Done.** The four `%%BOOKS_*%%` placeholder blocks (the whole `<main id="library">`) were deleted from `templates/index_base.html`; the `SECTIONS` loop and `render_book_card()` calls were removed from `cmd_generate()`; and `app.js` is now an empty stub. The hero and `about-publication` aside are untouched. The front page is masthead → hero → about aside only. (`render_book_card()`'s definition remains in `librarian.py` but is now unused.)

3. **Hero book clicks → per-book page** — **Done.** `render_hero()` computes the slug map itself (same read/reading query + `assign_slugs` as `_generate_books`, so hrefs match filenames) and wraps each hero book's cover image and headline in `<a href="books/<slug>.html">` across all three slots. The page-turn animation fires automatically (`page-transition.js` intercepts any internal `a[href]` click) — no JS change. Verified live: clicking the lead headline flips to `books/the-prize-the-epic-quest-for-oil-money-power.html`.

### ✅ v2.3 work items — all shipped (June 2026)

1. **Essays section** — **Done.** `_generate_essays()` + `parse_essay` / `render_essay_featured` / `render_essay_tile` / `render_essay_page` in `librarian.py`, plus `templates/essays_index_base.html` and `templates/essay_base.html`, and `.essay-featured` / `.essay-grid` / `.essay-tile` / `.essay-detail` CSS. Reads `essays/src/*.md`, renders Option B (featured hero + chronological grid), prunes stale pages. **Wired into `cmd_generate()`** — plain `python librarian.py generate` now rebuilds essays as the fifth output. Guarded `import yaml` (PyYAML) parses frontmatter with a minimal fallback. The header nav `Essays & Thoughts` link now resolves. Verified live in the browser.

2. **Mobile hamburger navigation** — **Done.** All five templates carry a `<button class="nav-hamburger">` plus a `.nav-links` wrapper; a shared `nav.js` toggles `nav-open` and closes the menu on link click. `styles.css` collapses the links into a vertical, newspaper-styled dropdown at `≤640px` and keeps them inline on desktop (the old "hide nav links on mobile" rule was removed). No external libraries. Verified live across desktop, mobile, and a nested essays page.

### ⚠️ Drift / quirks to be aware of
- The **live `library.db` has 41 books** (17 `read`, 7 `reading`, 17 `list`) and has diverged from the `BOOKS_DATA` seed. `BOOKS_DATA` is the one-time migration seed only — do not treat it as current content. A `library.db.bak-prequant` backup exists from the quant→finance rename.
- `ai_notes` remains in the DB schema for reference but is **not rendered anywhere on the site**. It is effectively inert.

---

## 1. Executive Summary

**Arjun's Archives** is a personal website for a Year‑2 university student studying Electrical/Mechanical Engineering and Computer Science. It has three distinct sections:

1. **Front page (`index.html`)** — A Financial Times‑style newspaper front page: masthead + strapline, an editorial hero featuring currently‑reading books (each linking to its per-book page), and an "About this Publication" aside with social links. This is the only page that must look and feel exactly like a broadsheet front page. *(The per-section book-card grid was removed in v2.2 — the full listing lives on `library.html`.)*
2. **Library (`library.html`)** — All books read or currently reading, sorted alphabetically, displayed as cover + title + author + status chip. Each book links to its own dedicated page. Books with `status = list` are excluded from the website entirely but remain in the database for CLI/GUI use.
3. **Essays & Thoughts (`essays/index.html`)** — A generated listing of personal essays (featured hero + chronological grid), each linking to its own `essays/[slug].html` page. Authored as Obsidian Markdown in `essays/src/`; built by `librarian.py generate`. *(See §12.)*

The site is **static** (no server, no build step to view — just open the HTML), but `index.html`, `library.html`, and all files under `books/` are **generated artifacts** produced by `librarian.py` from `library.db`. The essays section uses flat Markdown/HTML files with a separate manifest.

The defining architectural principle remains **strict separation of content from presentation**: regenerating the site can never clobber hand‑crafted design.

A signature feature is the **page‑turn animation** (`page-transition.js`) that captures the current screen with `html2canvas` and rolls it away like a turning newspaper sheet. It is currently a **single** transition profile (an earlier three-variant experiment was reverted — see §0 and §8).

---

## 2. What Has Been Achieved (Baseline — v1)

- Polished newspaper‑themed library site with aged‑newsprint texture, double rules, drop caps, sepia covers.
- Clean content/presentation split: content in `library.db`, presentation in standalone CSS/JS files.
- Single source of truth (`library.db`) feeding `index.html` and `library.md`.
- Three editing modes: CLI, Tkinter GUI, direct DB.
- Dynamic newspaper hero: auto‑derives "N Volumes Under Active Review" count and Hong Kong date.
- Bespoke page‑turn transition between pages.
- Per‑book comments via GitHub‑Issues‑backed Utterances. *(Removed in v2 — see §3.)*
- PostToolUse sync‑check hook guarding cover/ISBN consistency.
- Smoke‑test script exercising DB and renderers.

---

## 3. Repository Layout

| Path | Role | Hand‑edited? |
|---|---|---|
| `library.db` | **SQLite database — single source of truth** | via tooling only |
| `librarian.py` | Generator/CLI engine | yes |
| `librarian_gui.py` | Tkinter desktop GUI | yes |
| `test_librarian.py` | Smoke tests | yes |
| `check_sync.py` | PostToolUse hook: ISBN sync check | yes |
| `templates/index_base.html` | Skeleton for `index.html` | yes |
| `templates/library_base.html` | Skeleton for `library.html` | yes |
| `templates/book_base.html` | Skeleton for per‑book pages (`books/*.html`) | yes |
| `index.html` | **Generated** front page | **NO** |
| `library.html` | **Generated** library listing | **NO** |
| `books/[slug].html` | **Generated** per‑book pages (one per read/reading book) | **NO** |
| `library.md` | **Generated** Markdown export | **NO** |
| `essays/` | Source Markdown files + generated HTML | mixed — see §12 |
| `essays/src/[slug].md` | Source essay files written in Obsidian | yes — hand-authored |
| `essays/index.html` | **Generated** essays listing page | **NO** |
| `essays/[slug].html` | **Generated** individual essay pages | **NO** |
| `templates/essays_index_base.html` | Skeleton for `essays/index.html` | yes |
| `templates/essay_base.html` | Skeleton for `essays/[slug].html` | yes |
| `styles.css` | All shared presentation (layout, colours, textures, sepia, essay + nav styles) | yes |
| `app.js` | Empty stub (per‑section grid removed in v2.2) | yes |
| `nav.js` | Mobile hamburger nav toggle (shared, all pages) | yes |
| `flip-init.js` | Early script: marks a page as arriving via flip | yes |
| `page-transition.js` | Page‑turn animation engine (single transition) | yes |
| `html2canvas.min.js` | Vendored rasteriser (v1.4.1) | vendored |
| `book_covers_additional/` | Local cover images | assets |
| `CLAUDE.md` | Project instructions for Claude Code | yes |
| `.claude/settings.json` | Hook configuration | yes |

### Retired files (v1 → v2)

| File | Reason |
|---|---|
| `archive.html` | Replaced by generated `library.html` + `books/*.html` |
| `reading-list.html` | Reading‑list books no longer appear on the website |

### Utterances removal — exact codebase changes required

| Location | What to remove |
|---|---|
| `librarian.py` → `render_book_card()` | The `<script src="https://utteranc.es/client.js" ...>` tag and its surrounding container `<div class="comments-section">` |
| `app.js` | The `if` guard that checks `e.target.closest('utterances-timeline, .utterances')` (or similar) before toggling the card |
| `styles.css` | Any rule scoped to `.comments-section`, `.utterances`, or `utterances-timeline` |

---

## 4. Architecture: Content vs. Presentation

Two concerns are kept in separate files so regeneration never overwrites design work:

- **Content** — book records, hero text, dates — lives in **`library.db`**, rendered into HTML by `librarian.py`.
- **Presentation** — layout, colours, textures, animation — lives in hand‑edited files: `styles.css`, `app.js`, `flip-init.js`, `page-transition.js`, and the three template skeletons.

### Where to Make Each Kind of Change

| To change… | Edit… | Then… |
|---|---|---|
| A book's title / author / status / notes / ISBN | `library.db` (CLI or GUI) | `python librarian.py generate` |
| Newspaper hero stories / headlines | `library.db` hero fields | `python librarian.py generate` |
| Colours, layout, fonts, textures | `styles.css` | nothing |
| Page‑flip animation / behaviour | `page-transition.js` | nothing |
| Front page masthead skeleton | `templates/index_base.html` | `python librarian.py generate` |
| Library page skeleton | `templates/library_base.html` | `python librarian.py generate` |
| Per‑book page skeleton | `templates/book_base.html` | `python librarian.py generate` |

---

## 5. Data Model (`library.db`)

Single SQLite table `books`, created by `ensure_schema()`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `title` | TEXT NOT NULL | |
| `author` | TEXT NOT NULL | |
| `isbn` | TEXT | Open Library cover source |
| `section` | TEXT NOT NULL | CHECK ∈ `software`, `engineering`, `finance`, `philosophy` (the old `quant` key was renamed to `finance`) |
| `status` | TEXT NOT NULL | CHECK ∈ `read`, `reading`, `list` |
| `my_notes` | TEXT | Personal commentary (100–400 words, hand‑written) |
| `ai_notes` | TEXT | "About" blurb (AI‑generated). Still shown on front‑page cards; omitted on per‑book pages. (Originally slated for phase‑out, but still displayed.) |
| `sort_order` | INTEGER DEFAULT 0 | Ordering within a section |
| `hero_slot` | TEXT | CHECK ∈ `lead`, `side`, `bottom` (NULL = not on front page) |
| `hero_sort` | INTEGER DEFAULT 0 | Ordering within a hero slot |
| `hero_kicker` | TEXT | Small label above headline |
| `hero_headline` | TEXT | Story headline (defaults to title) |
| `hero_deck` | TEXT | Subheadline |
| `hero_byline_extra` | TEXT | Extra byline text |
| `hero_body` | TEXT | Lead‑story paragraph (lead slot; gets drop cap) |
| `hero_progress` | TEXT | Progress chip (e.g. "Mid‑way") |
| `local_cover_path` | TEXT | Path under `book_covers_additional/` |
| `date_added` | DATE DEFAULT CURRENT_DATE | |

### Sections

| Key | Display name |
|---|---|
| `software` | Software Related Books |
| `engineering` | Engineering & Mathematics |
| `finance` | Finance (quant finance -> finance) |
| `philosophy` | Greater Awareness & Philosophy |

### Status → Visibility

| Status | Label | Shown on website? |
|---|---|---|
| `read` | Read | ✅ library.html + books/[slug].html |
| `reading` | Currently Reading | ✅ index.html hero + library.html + books/[slug].html |
| `list` | Reading List | ❌ DB only — accessible via CLI/GUI |

---

## 6. The Generator / CLI (`librarian.py`)

### Commands

```
python librarian.py migrate          # seed library.db from BOOKS_DATA (once; --force to reset)
python librarian.py add              # interactively add a book
python librarian.py list             # list books [--section <s>] [--status <s>]
python librarian.py update <id>      # edit a book's fields
python librarian.py remove <id>      # delete a book (confirms)
python librarian.py hero <id>        # set newspaper hero fields for a Reading book
python librarian.py generate         # rebuild all generated files
```

### `cmd_generate()` — the build pipeline

The generator produces **five sets of outputs** in a single run — `index.html`, `library.html`, `books/[slug].html`, `essays/` (`_generate_essays`, see §12), and `library.md`:

1. **`index.html`** — from `templates/index_base.html`. `cmd_generate` substitutes exactly these placeholders: `%%NEWSPAPER_DYNAMIC%%`, `%%MASTHEAD_DATE%%`, `%%BOOKS_software%%` / `%%BOOKS_engineering%%` / `%%BOOKS_finance%%` / `%%BOOKS_philosophy%%`, and `%%FOOTER_DATE%%`.
   - The "About this Publication" box and masthead strapline are **static text in `index_base.html`** — there is **no** `%%ABOUT_BLURB%%` / `%%MASTHEAD_STRAPLINE%%` placeholder to fill.
   - **Not built:** the truncated `my_notes` preview + `Read full entry →` link. **v2.2:** the entire per-section card grid is removed instead — see §0 work items.

2. **`library.html`** — from `templates/library_base.html`:
   - Queries all books where `status IN ('read', 'reading')`, ordered alphabetically by title.
   - Renders each as a `.book-tile`: cover image (sepia), title, author, status chip.
   - Each tile links to `books/[slug].html`.
   - `status = list` books are excluded entirely.

3. **`books/[slug].html`** — one file per `read`/`reading` book, from `templates/book_base.html` (`_generate_books`):
   - Slug: `title` lowercased, spaces→hyphens, non‑alphanumeric stripped (e.g. *"The Prize"* → `the-prize`).
   - Fills `%%BOOK_TITLE%%` and `%%BOOK_CONTENT%%`.
   - Contains: cover image (large `-L` Open Library size, sepia), title, author, section label, status chip, `my_notes` (full text, no truncation; an empty-notes fallback message otherwise).
   - Does **not** include `ai_notes` or Utterances comments (clean, personal‑notes focus).
   - A `← Back to Library` link returns to `library.html`.
   - Stale `.html` files (from removed/renamed books) are pruned on every run.

4. **`library.md`** — same sectioned Markdown export as v1.

### Slug Generation (new utility function)

```python
import re, unicodedata

def slugify(title: str) -> str:
    title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode()
    title = title.lower().strip()
    title = re.sub(r'[^\w\s-]', '', title)
    title = re.sub(r'[\s_]+', '-', title)
    title = re.sub(r'-+', '-', title).strip('-')
    return title
```

Slug collisions (two books with the same title after slugification) are resolved by appending `--2`, `--3`, etc.

### Rendering Functions (as implemented)

- **`render_book_tile(book, slug)`** — emits `.book-tile` HTML (cover + title + author + status chip) for `library.html`, linking to `books/<slug>.html`. (Note: takes `slug` as a second argument.)
- **`render_book_page(book, slug)`** — emits the `<article class="book-detail">` body for `books/[slug].html`, substituted into `%%BOOK_CONTENT%%`. `my_notes` is rendered via **`_notes_to_html()`** (Markdown → HTML; see §0 work item 1).
- **`_notes_to_html(text)`** — converts `my_notes` Markdown to HTML using the `markdown` package (`extensions=['extra']`), with a blank-line `<p>`-splitting fallback if the package is unavailable.
- **`_tile_cover` / `_detail_cover` / `_cover_div` / `_hero_cover_src`** — cover source resolution (local path → ISBN → "No cover available"). `_detail_cover` uses the `-L` Open Library size and `../`-relative paths.
- **`slugify` / `assign_slugs`** — URL slug generation + collision handling.
- **`render_book_card(book)`** — formerly the expandable card for `index.html`. **Now unused** (the per-section grid was removed in v2.2); the definition remains in `librarian.py` but is no longer called.
- **`render_notes_preview(text, max_chars=150)`** — **NOT implemented** (roadmap; see §0).
- **`render_hero(conn)`** — newspaper hero for `index.html` (lead/side/bottom slots, dynamic volume count).
- **`e()`** — HTML escaping.

---

## 7. Templates

### `templates/index_base.html` (v2.2 updated)

- `<title>` is **"Arjun's Dispatch"**; masthead name is **"The Arjun Dispatch"**; nav logo is **"Arjun's Archives"**.
- Nav links: **Front Page | Library | Essays & Thoughts**.
- Masthead strapline hard-coded in the template (no `%%MASTHEAD_STRAPLINE%%` placeholder).
- `<aside class="about-publication">` "About this Publication" block with GitHub/LinkedIn links — hard-coded.
- **v2.2:** The four `%%BOOKS_software%%` / `%%BOOKS_engineering%%` / `%%BOOKS_finance%%` / `%%BOOKS_philosophy%%` placeholder blocks are **removed**. The hero (`%%NEWSPAPER_DYNAMIC%%`) and about aside are the only content below the masthead.

### `templates/library_base.html` (new)

Thin skeleton for `library.html`:
- `<head>` loads same fonts, `styles.css`, `flip-init.js`.
- A newspaper banner reusing the masthead ("The Arjun Dispatch", strapline *"The Library — Every Volume Read and Under Review"*, tagline *"The Complete Shelf, Set in Order"*) plus a `section-banner` filled by `%%LIBRARY_COUNT%%` (e.g. *"41 Volumes · Arranged A–Z by Title"*).
- Placeholders filled by `_generate_library`: `%%BOOK_TILES%%`, `%%MASTHEAD_DATE%%`, `%%LIBRARY_COUNT%%`.
- Scripts at end: `html2canvas.min.js`, `page-transition.js?v=7`.

### `templates/book_base.html` (new)

Thin skeleton for per‑book pages (lives one level deep, so all asset/nav links use `../`):
- `<head>` loads fonts, `../styles.css`, `../flip-init.js`; `<title>` filled by `%%BOOK_TITLE%%`.
- A minimal newspaper header (masthead name only, no date/strapline).
- Placeholders: `%%BOOK_TITLE%%`, `%%BOOK_CONTENT%%`.
- A `← Back to Library` nav link.
- Scripts at end: `../html2canvas.min.js`, `../page-transition.js?v=7`.

---

## 8. Presentation Files

### `styles.css` (extended)

All existing rules (tokens, texture, hero, cards, covers) are preserved. New rules added:

**Library grid (`.book-tiles-grid`):**
- CSS Grid, **capped at 4 columns**, responsive down to 2 on narrow viewports.
- Each `.book-tile`: cover image (fills tile, `object-fit: cover`, sepia filter), title below in Playfair Display, author in small Libre Baskerville italic, status chip (same classes as existing: `status-read`, `status-reading`).
- Hover state: slight lift (`transform: translateY(-3px)`), subtle shadow.

**Per‑book page (`.book-detail`):**
- Simple two‑column layout at desktop (cover left ~220px, notes right); single column on mobile.
- Notes in Libre Baskerville, justified, generous line‑height — optimised for reading personal essays.
- Section/status displayed as a small label row above the title.

**Nav bar (updated):**
- Three links: Front Page | Library | Essays & Thoughts.
- Same typographic treatment as existing nav.

**Masthead strapline:**
- Centred, small‑caps, Libre Baskerville italic, muted taupe colour — sits directly below the date line, above the double rule.

### `app.js` (v2.2 updated)
The book-card expand/collapse logic that served the per-section grid is **removed** (the grid itself is removed — see §7 / §0). `app.js` is now an **empty stub** (a comment only); it is still referenced by the `index.html` `<script>` tag but does nothing.

### `nav.js` (new — mobile navigation)
A shared script loaded by **all** templates (root path on `index`/`library`, `../nav.js` on `books/` and `essays/` pages). A single delegated `click` listener toggles `nav-open` on the `<nav>` when the hamburger (`.nav-hamburger`) is clicked, and removes it when a `.nav-links a` is clicked. It coexists with `page-transition.js` (which still handles the actual flip-navigation — `preventDefault` there does not stop `nav.js`'s bubble-phase listener). No external libraries.

**Responsive nav CSS (`styles.css`):** at `≤640px` the inline links collapse — `.nav-hamburger` shows, `.nav-links` hides, and `nav.nav-open .nav-links` becomes a vertical, newspaper-styled dropdown (same fonts/colours, stacked with rule separators; the header's existing `border-bottom` divides it from the page). Desktop (`≥641px`) keeps the links inline and hides the hamburger. The old `nav a { display: none; }` mobile rule (which simply hid the links) was removed.

### `flip-init.js` (unchanged)
Suppresses entrance fade on flip‑arriving pages.

### `page-transition.js` (single transition — variants reverted)

> **Reality check:** the three-variant design below was **built and then reverted**. Commit `006bd4c` added `slowDramatic` / `mediumCrisp` / `snapWithPeel` (cache-buster `v6`); commit `a97c79e` reverted to the **single** page-flip transition (cache-buster `v7`). All three templates currently load `page-transition.js?v=7`. The codebase has **one** transition profile today.

The shipped animation is a single cylindrical-curl page-turn: it captures the outgoing screen with `html2canvas` and rolls it away like a newspaper sheet, degrading to an aged-paper fallback if capture fails.

**Roadmap option (not current):** reintroduce multiple randomised profiles. The earlier experiment defined named profiles chosen at random per transition — e.g.:

| Variant | Character | Duration | Key difference |
|---|---|---|---|
| `slowDramatic` | Weighty, deliberate | ~1 100 ms | Current easing |
| `mediumCrisp` | Snappy broadsheet flip | ~650 ms | Faster ease‑in, less curl depth |
| `snapWithPeel` | Hesitates then lifts | ~900 ms | 80 ms pause + slight `skewX` peel before rotation |

If revisited, bump the `?v=` cache-buster across all three templates so browsers pick up the new script.

---

## 9. Front Page (`index.html`) — Current State (v2.2)

The front page has:
1. **Masthead** with strapline — *"A personal record of books read, annotated, and lived with"*.
2. **Newspaper hero** (`%%NEWSPAPER_DYNAMIC%%`) — lead/side/bottom slots for currently-reading books. **v2.2:** each hero book's headline and cover now link to `books/[slug].html` via the page-turn animation.
3. **"About this Publication" aside** — static editorial box with GitHub/LinkedIn links.
4. ~~Per-section book-card grid~~ — **removed in v2.2**. `library.html` handles the full listing.

The front page is intentionally lean: masthead → hero → about. Nothing else.

---

## 10. Library Page (`library.html`)

- **Replaces:** `archive.html` (retired) and `reading-list.html` (retired).
- **Generated** by `librarian.py` from `library.db`.
- **Content:** all `read` and `reading` books; `list` books excluded.
- **Order:** alphabetical by title (A → Z).
- **Layout:** grid of `.book-tile` elements (cover + title + author + status chip).
- **Interaction:** clicking any tile triggers the page‑turn animation and navigates to `books/[slug].html`.
- **Newspaper styling:** consistent font stack and colour tokens with `index.html`; a section banner at the top; no full front‑page masthead treatment needed.

---

## 11. Per‑Book Pages (`books/[slug].html`)

- **Generated** by `librarian.py`; directory is a generated artifact (never hand‑edit individual files).
- **One file per `read` or `reading` book.**
- **Content displayed:**
  - Cover image (large, sepia)
  - Title (Playfair Display, large)
  - Author + section label + status chip
  - Full `my_notes` text (hand‑written by Arjun, 100–400 words)
- **Content omitted:** `ai_notes`, Utterances comments widget.
- **Navigation:** `← Back to Library` link at top; page‑turn animation applies to this link too.
- **Slug stability:** once generated, a slug should not change (it would break any shared links). If a title is edited, re‑run `generate`; the old file is overwritten at the same slug as long as the title is the same.

### GUI Workflow for Adding a Book Entry

1. Open `librarian_gui.py`.
2. Select the book (or add it via "New").
3. Write or paste personal notes into the **My Notes** field (100–400 words).
4. Click **Save + Regenerate**.
5. `librarian.py generate` runs automatically, writing/overwriting `books/[slug].html` and updating `index.html` and `library.html`.
6. No manual hyperlinking needed — all links are generated.

---

## 12. Essays & Thoughts (`essays/`)

### Overview

Essays are authored in **Obsidian as Markdown files**, dropped into `essays/src/`, and converted to HTML by `librarian.py generate` (the same command that rebuilds books and library). The result is two generated outputs: `essays/index.html` (the listing) and one `essays/[slug].html` per essay. Neither is ever hand-edited.

The listing uses **Option B layout**: the most recently dated essay gets a full hero treatment (kicker, headline, deck) at the top; all other essays appear in a chronological two-column grid below showing title, category tag, and date.

---

### Frontmatter (YAML, required in every essay file)

Each `.md` file in `essays/src/` must begin with a YAML frontmatter block:

```yaml
---
title: "On building things that last"
date: 2026-06-01
category: engineering
deck: "A reflection on permanence, craft, and what it means to make something worth keeping."
---
```

| Field | Required | Notes |
|---|---|---|
| `title` | ✅ | Display title; also used for slug generation |
| `date` | ✅ | ISO format `YYYY-MM-DD`; determines ordering and featured selection |
| `category` | ✅ | One of `software`, `engineering`, `finance`, `philosophy` — same keys as books |
| `deck` | ✅ | One-sentence subtitle; shown in the featured hero and (on hover/expand) in the grid |

The essay body begins immediately after the closing `---`. Full Obsidian Markdown is supported: bold, italic, headings, blockquotes, lists, images. The `markdown` library with the `extra` extension (already installed) handles conversion — the same pipeline as `my_notes` on book pages.

---

### Slug generation

Same `slugify()` function used for books. `"On building things that last"` → `on-building-things-that-last`. Collision suffix `--2`, `--3` etc. Output file: `essays/on-building-things-that-last.html`.

**Slug stability rule:** renaming an essay's title in frontmatter changes its slug and breaks any shared links. Avoid title edits on published essays.

---

### Generator additions (`librarian.py`)

`cmd_generate()` gains a fifth output: **`_generate_essays(conn)`** (essays don't touch the DB — they read from `essays/src/*.md` directly).

```
essays/src/          ← scanned by _generate_essays()
essays/index.html    ← generated listing
essays/[slug].html   ← one per .md file
```

**`_generate_essays()` pipeline:**

1. Scan `essays/src/*.md`, parse YAML frontmatter + body from each.
2. Sort all essays by `date` descending (newest first).
3. The first essay (newest date) is the **featured essay**.
4. Render `essays/index.html` from `templates/essays_index_base.html`, substituting:
   - `%%ESSAYS_FEATURED%%` — the featured hero block (kicker = category display name, headline = title, deck = deck field, date).
   - `%%ESSAYS_GRID%%` — the remaining essays as `.essay-tile` cards, chronological, two columns.
   - `%%MASTHEAD_DATE%%` — same Hong Kong date as other pages.
   - `%%ESSAY_COUNT%%` — e.g. `"14 dispatches"`.
5. For each essay, render `essays/[slug].html` from `templates/essay_base.html`, substituting `%%ESSAY_TITLE%%` and `%%ESSAY_CONTENT%%`.
6. Prune stale `essays/*.html` files (slugs with no matching source `.md`).

**New rendering functions:**

- **`parse_essay(path)`** — reads a `.md` file, splits YAML frontmatter from body, returns a dict with `title`, `date`, `category`, `deck`, `slug`, `body_html`.
- **`render_essay_featured(essay)`** — emits the `.essay-featured` hero block for `essays/index.html`.
- **`render_essay_tile(essay)`** — emits a `.essay-tile` card (title, category chip, date) for the grid.
- **`render_essay_page(essay)`** — emits the `<article class="essay-detail">` body for individual pages.

---

### Templates

**`templates/essays_index_base.html`** (new):
- `<head>` loads fonts, `../styles.css`, `../flip-init.js`; `<title>` = `"Essays & Thoughts · Arjun's Dispatch"`.
- Masthead: same newspaper header as `library_base.html` — name + strapline `"Essays & Thoughts — Columns, Reflections & Dispatches"`.
- Section banner: `%%ESSAY_COUNT%%`.
- `%%ESSAYS_FEATURED%%` — full-width hero.
- A horizontal rule separating hero from grid.
- `%%ESSAYS_GRID%%` — two-column `.essay-grid`.
- Scripts: `../html2canvas.min.js`, `../page-transition.js?v=7`.

Note: `essays/index.html` lives one level deep (inside `essays/`), so all asset paths use `../`. Same pattern as `books/`.

**`templates/essay_base.html`** (new):
- `<head>` loads fonts, `../styles.css`, `../flip-init.js`; `<title>` = `%%ESSAY_TITLE%%`.
- Minimal newspaper header (masthead name only).
- `%%ESSAY_CONTENT%%` — full essay body.
- `← Back to Essays` nav link (to `../essays/index.html`).
- Scripts: `../html2canvas.min.js`, `../page-transition.js?v=7`.

---

### CSS additions (`styles.css`)

**Featured essay hero (`.essay-featured`):**
- Full-width block, top border double-rule, generous vertical padding.
- Kicker: small-caps category label (same treatment as hero book kickers on `index.html`).
- Headline: Playfair Display, large (~28px), tight line-height.
- Deck: Libre Baskerville italic, muted, ~15px.
- Date: small, taupe.
- The whole block is a link (`<a href="[slug].html">` — same-directory, since `essays/index.html` already lives in `essays/`) — page-turn fires automatically.

**Essay grid (`.essay-grid`):**
- CSS Grid, 2 columns, `gap: 0` — tiles separated by 0.5px border rules (same as the option B mockup).
- Odd tiles: `border-right: 0.5px solid` + `padding-right`.
- Even tiles: `padding-left`.
- Each `.essay-tile`: title in Playfair Display (~14px, tight), category chip (same `.status-read` pill style, coloured by category), date in small taupe.
- Hover: title underlines.

**Individual essay page (`.essay-detail`):**
- Single-column, max-width ~680px, centred.
- Title: Playfair Display, large.
- Deck (if present): italic, muted, below the title — acts as a standfirst.
- Byline row: category chip + date.
- Body: Libre Baskerville, justified, generous line-height — same as book notes. Markdown headings, blockquotes, lists all styled consistently.
- Images: `max-width: 100%`, sepia filter (`filter: sepia(0.2)`), centred.

---

### Categories (essays)

| Key | Display name | Chip colour |
|---|---|---|
| `software` | Software | same pill as book section |
| `engineering` | Engineering | same pill as book section |
| `finance` | Finance | same pill as book section |
| `philosophy` | Philosophy | same pill as book section |

The category key in essay frontmatter must match one of these exactly. Invalid category → `librarian.py generate` prints a warning and uses `"Uncategorised"` as fallback (does not abort the build).

---

### Standard workflow — writing and publishing an essay

1. Write the essay in Obsidian as a `.md` file with the required frontmatter.
2. Save the file into `essays/src/` (can be done from Obsidian by setting the vault or folder path, or by drag-and-drop).
3. Run `python librarian.py generate` (or click **Save + Regenerate** in the GUI — it calls the same command).
4. `essays/index.html` and `essays/[slug].html` are written automatically.
5. The dead nav link (`Essays & Thoughts` in the header) now resolves correctly.

To update an existing essay: edit the `.md` file in Obsidian, re-run generate. The slug is stable as long as the title doesn't change.

To unpublish: move the `.md` file out of `essays/src/` (e.g. to `essays/drafts/`), re-run generate. The stale HTML is pruned automatically.

---

### Images in essays

Store images in `essays/images/` and reference them in Markdown as `images/my-photo.jpg` (e.g. `![caption](images/my-photo.jpg)`). The generator does **not** rewrite image paths — the path you write is used verbatim in the generated page. Because each generated essay page lives in `essays/` (a sibling of `essays/images/`, **not** one level above it), the correct relative path is `images/…`, not `../images/…`. The generator does not copy or process image files — place them in `essays/images/` manually. Broken image paths degrade gracefully (browser shows alt text). *(Verified: the test essay loads `essays/images/workbench.jpg` via `images/workbench.jpg`.)*

---

### What essays do NOT have

- No comments (Utterances was removed site-wide).
- No DB entry — essays are entirely file-driven, not in `library.db`.
- No GUI panel — essays are managed as files, not through `librarian_gui.py`.
- No search or tag filtering on `essays/index.html` (roadmap).

---

## 13. Covers

- Primary: **Open Library** by ISBN — `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`.
- Fallback: `local_cover_path` pointing into `book_covers_additional/`.
- Broken images: `onerror` hides `<img>` and shows "No cover available" text.
- All covers sepia‑toned via CSS (`filter: sepia(0.35) saturate(1.1)`) on all pages.

---

## 14. The Desktop GUI (`librarian_gui.py`)

Unchanged from v1 except:
- **Save + Regenerate** runs `cmd_generate`, which rebuilds `index.html`, `library.html`, `books/*.html`, `essays/index.html`, `essays/*.html`, and `library.md` in a single pass.
- The GUI does not expose essay management (essays are edited as files directly).
- **Not done:** the **My Notes** field label is still literally **"My Notes"** (the v2.0 idea to rename it "My Entry / Notes" was not applied).

---

## 15. Sync‑Check Hook (`check_sync.py`)

Unchanged. Guards ISBN consistency between hero and library sections of `index.html`.

---

## 16. Tests (`test_librarian.py`)

**As shipped**, `test_librarian.py` is still the v1-style DB-inspection smoke script: it prints total counts, status breakdown, sample rows, hero-eligible books, and cover-source tallies. It does **not** yet cover the v2 generator.

**Roadmap (not built):**
- Slug generation (uniqueness, special characters, collision handling).
- That `books/` is created and contains at least one `.html` after `generate`.
- That `library.html` exists and excludes `list` books.

---

## 17. Dependencies

| Dependency | Type | Used by | Purpose |
|---|---|---|---|
| Python 3 (stdlib) | runtime | `librarian.py`, tests | DB, rendering |
| SQLite | data store | engine | source of truth |
| Tkinter | GUI | `librarian_gui.py` | desktop editor |
| Pillow (PIL) | optional | GUI | cover thumbnail preview |
| html2canvas 1.4.1 | vendored JS | page transition | viewport snapshot |
| Google Fonts | external CSS | all pages | Playfair Display, IM Fell English, Libre Baskerville, Inter |
| Open Library covers API | external | covers | book cover images |

| PyYAML (PyPI) | runtime | `librarian.py` | Parses YAML frontmatter from essay `.md` files |
| Markdown (PyPI) | runtime | `librarian.py` | Converts `my_notes` and essay bodies to HTML |

---

## 18. Standard Workflows

**Add a book and write your entry:**
1. `librarian_gui.py` → New → fill in title, author, section, status, ISBN.
2. Write personal notes in **My Entry / Notes** field.
3. Click **Save + Regenerate** → `library.html`, `books/[slug].html`, and `index.html` all update automatically.

**Feature a book on the front page (currently reading):**
1. Set status to `reading`.
2. Open the Newspaper Hero panel in the GUI → fill in slot, kicker, headline, deck, progress.
3. **Save + Regenerate**.

**Edit an entry:**
1. Select book in GUI → update **My Entry / Notes**.
2. **Save + Regenerate**.

**Edit design:**
→ Edit `styles.css` or JS files directly. No regeneration needed.

**Edit masthead / nav / strapline / about blurb:**
→ Edit the relevant template file → `python librarian.py generate`.

**Golden rule:** never hand‑edit `index.html`, `library.html`, `library.md`, or any file under `books/` — all are overwritten by `generate`.

---

## 19. Notable Constraints & Quirks

- Masthead date is **Hong Kong (UTC+8)**; footer date is the build machine's local date.
- "N Volumes Under Active Review" reflects all `reading` books, not just those shown in the hero.
- `list` books never appear on the website; they remain in the DB for personal tracking via CLI/GUI.
- The `books/` directory is entirely generated; the whole directory can be deleted and rebuilt with `generate`.
- Slug stability: editing a book's title changes its slug and therefore its URL. Avoid title edits on books you have shared links for.
- Page‑turn relies on html2canvas succeeding; degrades to aged‑paper fallback sheet otherwise.
- Essays are file-driven, not DB-driven. Moving a `.md` file out of `essays/src/` unpublishes it on next generate (stale HTML is pruned automatically).
- Essay slug stability: same rule as books — avoid renaming an essay's `title` in frontmatter once it's published, as this changes the slug and breaks shared links.
- Open Library and Google Fonts require network access; both degrade gracefully.

---

## 20. Open Roadmap / Next Steps

**Active roadmap:**
- Reintroduce randomised page-turn variants (`slowDramatic` / `mediumCrisp` / `snapWithPeel`) — or deliberately keep the single transition. Decision pending.
- Extend `test_librarian.py` to cover slug generation, `library.html`, `books/` output, and essay generation.
- Clean up dead code: delete `render_book_card()` from `librarian.py`.

**Longer-term ideas:**
- Search / filter on `library.html`.
- Dark mode.
- RSS feed.
- Document or clean up the divergence between `BOOKS_DATA` and the live `library.db`.

---

*End of specification — v2.4*
