# Project Specification — Arjun's Archives (Claude Librarian)

*A complete A‑to‑Z technical and design specification of the personal reading‑library website.*

**Spec version:** 2.2 — three work items, now all **shipped** (June 2026): Markdown rendering in `my_notes`, removal of the per-section book-card grid from `index.html`, and hero book links to per-book pages.

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

### ❌ Described in the v2.0 draft but NOT built (still roadmap)
- **Three randomised page-turn variants** (`slowDramatic` / `mediumCrisp` / `snapWithPeel`). These were added (cache-buster `v6`) then **reverted** to the single transition (`v7`). The codebase has **one** transition today.
- **Truncated `my_notes` preview + `Read full entry →` link** on the front page (`render_notes_preview`). Front-page cards still show the **full** `my_notes` *and* the `ai_notes` "About" block via expand/collapse — exactly as in v1.
- **`essays/` section** — no `essays/` directory, listing, or pages exist. Nav links to `essays/index.html` are dead.
- `%%ABOUT_BLURB%%` / `%%MASTHEAD_STRAPLINE%%` as **placeholders** — these are hard-coded in `templates/index_base.html`, and `cmd_generate` does not substitute them.

### ✅ v2.2 work items — all shipped (June 2026)

All three v2.2 tasks are now implemented, generated, and verified (including a live browser click-through):

1. **Markdown rendering in `my_notes`** — **Done.** `librarian.py` imports `markdown` (guarded; `_markdown = None` on `ImportError`) and a new `_notes_to_html()` helper pipes `my_notes` through `markdown.markdown(text, extensions=['extra'])` inside `render_book_page()`, falling back to blank-line (`\n\n`) splitting into HTML-escaped `<p>` chunks when the package is absent. Bold/italic/headings/lists/paragraph breaks now render on book pages. Dependency `Markdown 3.10.2` installed (see §17). No GUI change needed.

2. **Per-section book-card grid removed from `index.html`** — **Done.** The four `%%BOOKS_*%%` placeholder blocks (the whole `<main id="library">`) were deleted from `templates/index_base.html`; the `SECTIONS` loop and `render_book_card()` calls were removed from `cmd_generate()`; and `app.js` is now an empty stub. The hero and `about-publication` aside are untouched. The front page is masthead → hero → about aside only. (`render_book_card()`'s definition remains in `librarian.py` but is now unused.)

3. **Hero book clicks → per-book page** — **Done.** `render_hero()` computes the slug map itself (same read/reading query + `assign_slugs` as `_generate_books`, so hrefs match filenames) and wraps each hero book's cover image and headline in `<a href="books/<slug>.html">` across all three slots. The page-turn animation fires automatically (`page-transition.js` intercepts any internal `a[href]` click) — no JS change. Verified live: clicking the lead headline flips to `books/the-prize-the-epic-quest-for-oil-money-power.html`.

### ⚠️ Drift / quirks to be aware of
- The **live `library.db` has 41 books** (17 `read`, 7 `reading`, 17 `list`) and has diverged from the `BOOKS_DATA` seed (e.g. *I, Robot* is now `read`; *Money, War, Sex, Karma* added as `reading`). `BOOKS_DATA` is the one-time migration seed only — do not treat it as current content. A `library.db.bak-prequant` backup exists from the quant→finance rename.
- `ai_notes` is still authored and **still displayed on front-page cards** ("About" block); it is **omitted** on per-book pages. It is not "phased out" yet.

---

## 1. Executive Summary

**Arjun's Archives** is a personal website for a Year‑2 university student studying Electrical/Mechanical Engineering and Computer Science. It has three distinct sections:

1. **Front page (`index.html`)** — A Financial Times‑style newspaper front page: masthead, editorial hero featuring currently‑reading books, a brief "About" column, social links, and per-section book cards (expand/collapse, full notes). This is the only page that must look and feel exactly like a broadsheet front page. *(The v2 vision of truncating each card to a short preview + "Read full entry →" link is not yet built — see §0.)*
2. **Library (`library.html`)** — All books read or currently reading, sorted alphabetically, displayed as cover + title + author + status chip. Each book links to its own dedicated page. Books with `status = list` are excluded from the website entirely but remain in the database for CLI/GUI use.
3. **Essays & Thoughts (`essays/index.html`)** — A listing of personal essays and reflections. *(Design to be discussed separately; placeholder in this spec.)*

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
| `essays/index.html` | Essays listing *(see §15)* | TBD |
| `essays/[slug].html` | Individual essay pages | TBD |
| `styles.css` | All shared presentation (layout, colours, textures, sepia) | yes |
| `app.js` | Book‑card expand/collapse (index.html) | yes |
| `flip-init.js` | Early script: marks a page as arriving via flip | yes |
| `page-transition.js` | Page‑turn animation engine (three variants) | yes |
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

The generator now produces **four sets of outputs** in a single run:

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

## 12. Essays & Thoughts (`essays/`) — Placeholder

*Full design to be discussed separately. The following is the agreed skeleton only.*

- **`essays/index.html`** — a listing page: titles as a styled bullet/list, each linking to its essay page. Can be hand‑authored or generated from a manifest file.
- **`essays/[slug].html`** — individual essay pages, hand‑authored HTML or converted from Markdown.
- Essays may contain images (to be decided: inline `<img>` tags, or a managed `essays/images/` folder).
- Linked from `index.html` ("Essays & Thoughts" nav item and a front‑page teaser column).
- Typography consistent with the rest of the site (same font stack from `styles.css`).
- Page‑turn animation applies site‑wide, including essay pages.

---

## 13. Covers

- Primary: **Open Library** by ISBN — `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`.
- Fallback: `local_cover_path` pointing into `book_covers_additional/`.
- Broken images: `onerror` hides `<img>` and shows "No cover available" text.
- All covers sepia‑toned via CSS (`filter: sepia(0.35) saturate(1.1)`) on all pages.

---

## 14. The Desktop GUI (`librarian_gui.py`)

Unchanged from v1 except:
- **Save + Regenerate** runs `cmd_generate`, which rebuilds `index.html`, `library.html`, `books/*.html`, and `library.md`. The GUI status line and help text reflect this ("Regenerated index.html, library.html, books/ + library.md").
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

| Markdown (PyPI) | runtime | `librarian.py` | Converts `my_notes` Markdown to HTML for book pages |

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
- Essays are not DB‑driven (v2 scope); they are managed as files.
- Open Library and Google Fonts require network access; both degrade gracefully.

---

## 20. Open Roadmap / Next Steps

**Carried over from the v2.0 draft but not yet built** (see §0 for the authoritative status):
- Front-page `render_notes_preview` — truncate each card's `my_notes` and add a `Read full entry →` link to the per-book page.
- Reintroduce randomised page-turn variants (or deliberately keep the single transition — decide and record).
- `essays/` section: listing + individual pages (fix the currently-dead nav link), with a front-page teaser column. *Design still TBD.*
- Extend `test_librarian.py` to cover slug generation, `library.html`, and `books/` output.
- Decide the fate of `ai_notes` (keep on front page, or finally phase out of display).

**New / longer-term ideas:**
- Search / filter on `library.html`.
- Dark mode.
- RSS feed.
- Reseed or document the divergence between `BOOKS_DATA` and the live `library.db` (41 books).

---

*End of specification — v2.2*
