# Project Specification — Arjun's Archives (Claude Librarian)

*A complete A‑to‑Z technical and design specification of the personal reading‑library website.*

---

## 1. Executive summary

**Arjun's Archives** is a personal reading‑library website for a Year‑2 university student studying Electrical/Mechanical Engineering and Computer Science. It catalogues the books he has read, is currently reading, and intends to read, across four subject areas, and presents them in two distinct visual modes:

1. A **classic expandable library list** (the main `index.html` body) — each book is a card that opens to reveal personal notes, an "About" blurb, a cover image, and a per‑book comments widget.
2. A **Financial‑Times‑style newspaper "front page"** (the hero at the top of `index.html`, plus standalone `reading-list.html` and `archive.html` pages) — the books are typeset as editorial stories with a masthead, kickers, headlines, decks, bylines, drop caps, and B&W/sepia cover art.

The site is **static** (no server, no build step needed to *view* it — just open the HTML), but `index.html` and `library.md` are **generated artifacts**, produced by a Python program (`librarian.py`) from a **SQLite database** (`library.db`). A signature feature is a hand‑written **page‑turn animation** (`page-transition.js`) that captures the current screen with `html2canvas` and rolls it away like a turning newspaper sheet when navigating between pages.

The defining architectural principle is a **strict separation of content from presentation** so that regenerating the site can never clobber the hand‑crafted design.

---

## 2. What has been achieved

- A polished, distinctive, newspaper‑themed personal library site with a memorable aesthetic (aged newsprint texture, double rules, drop caps, sepia covers).
- A clean **content/presentation split** that solved a real historical problem: earlier, styling lived inline in `index.html` and was repeatedly destroyed by regeneration. Now content lives in a database and presentation lives in standalone files.
- A **single source of truth** (`library.db`) feeding multiple outputs (`index.html`, `library.md`).
- **Three ways to edit** the library: a CLI, a Tkinter desktop GUI, and direct DB editing — all sharing one engine.
- A **dynamic newspaper hero** that auto‑derives the "N Volumes Under Active Review" count and the current Hong Kong date at generation time.
- A bespoke, content‑preserving **page‑turn transition** between pages.
- Per‑book **comments** via GitHub‑Issues‑backed Utterances.
- A **PostToolUse sync‑check hook** guarding cover/ISBN consistency.
- A **smoke‑test script** exercising the DB and renderers.

---

## 3. Repository layout

| Path | Role | Hand‑edited? |
|---|---|---|
| `library.db` | **SQLite database — the single source of truth** for all book content | via tooling only |
| `librarian.py` | The generator/CLI engine (DB schema, rendering, commands, seed data) | yes |
| `librarian_gui.py` | Tkinter desktop GUI over the same engine | yes |
| `test_librarian.py` | Smoke tests for DB + renderers | yes |
| `check_sync.py` | PostToolUse hook: verifies hero/library ISBN consistency | yes |
| `templates/index_base.html` | Skeleton template with `%%PLACEHOLDERS%%` for the generator | yes |
| `index.html` | **Generated** front page (hero + library list) | **NO — overwritten by `generate`** |
| `library.md` | **Generated** Markdown export of the library | **NO — overwritten by `generate`** |
| `reading-list.html` | Standalone hand‑authored "Reading Queue" newspaper page | yes (self‑contained, inline CSS) |
| `archive.html` | Standalone hand‑authored "Archive" newspaper page (finished books) | yes (self‑contained, inline CSS) |
| `styles.css` | All presentation for `index.html` (layout, colours, textures, sepia) | yes |
| `app.js` | Book‑card expand/collapse interaction | yes |
| `flip-init.js` | Tiny early script: marks a page as "arriving via flip" to suppress fade | yes |
| `page-transition.js` | The newspaper page‑turn animation engine | yes |
| `html2canvas.min.js` | Vendored 3rd‑party library (v1.4.1) used to snapshot the viewport | vendored |
| `book_covers_additional/` | Local cover images for books without a usable ISBN cover | assets |
| `CLAUDE.md` | Project instructions for Claude Code | yes |
| `.claude/settings.json` | Hook configuration (the sync‑check) | yes |
| `.claude/settings.local.json` | Local permission allow‑list | yes |
| `book list.pdf` | Source reference list of books | asset |
| `*.png`, `.playwright-mcp/` | Screenshots / Playwright artifacts (git‑ignored) | artifacts |

---

## 4. Architecture: content vs. presentation (the core idea)

Two concerns are deliberately kept in separate files so a regeneration never overwrites design work:

- **Content** — book records, the newspaper hero text, and dates — lives in **`library.db`**. It is rendered into `index.html` + `library.md` by `librarian.py`.
- **Presentation** — all layout, colours, the aged‑newsprint texture, the sepia cover filters, the page‑flip animation — lives in standalone, hand‑edited files: `styles.css`, `app.js`, `flip-init.js`, `page-transition.js`, `html2canvas.min.js`.

`index.html` is **generated output**: its `<head>`/`<body>` are a thin skeleton (from `templates/index_base.html`) that *links* the presentation files and *holds* the rendered content. `generate` only ever writes `index.html` and `library.md`; it never touches the presentation files, so editing those is always safe.

### Where to make each kind of change

| To change… | Edit… | Then… |
|---|---|---|
| A book's title/author/status/notes/ISBN | `library.db` (CLI or GUI) | `python librarian.py generate` |
| The newspaper hero stories/headlines | `library.db` hero fields (GUI hero form / `hero` cmd) | `python librarian.py generate` |
| Colours, layout, fonts, textures | `styles.css` | nothing — loaded directly |
| Page‑flip animation / behaviour | `page-transition.js`, `app.js`, `flip-init.js` | nothing — loaded directly |
| Masthead name / "Vol." / tagline / skeleton | `templates/index_base.html` | `python librarian.py generate` |

---

## 5. Data model (`library.db`)

A single SQLite table, `books`, created by `ensure_schema()` in `librarian.py`:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | |
| `title` | TEXT NOT NULL | |
| `author` | TEXT NOT NULL | |
| `isbn` | TEXT | used to fetch an Open Library cover |
| `section` | TEXT NOT NULL | CHECK ∈ `software`, `engineering`, `quant`, `philosophy` |
| `status` | TEXT NOT NULL | CHECK ∈ `read`, `reading`, `list` |
| `my_notes` | TEXT | personal commentary |
| `ai_notes` | TEXT | the "About" blurb |
| `sort_order` | INTEGER DEFAULT 0 | ordering within a section |
| `hero_slot` | TEXT | CHECK ∈ `lead`, `side`, `bottom` (NULL = not on front page) |
| `hero_sort` | INTEGER DEFAULT 0 | ordering within a hero slot |
| `hero_kicker` | TEXT | small label above headline (e.g. "Derivatives") |
| `hero_headline` | TEXT | story headline (defaults to title) |
| `hero_deck` | TEXT | subheadline |
| `hero_byline_extra` | TEXT | extra byline text (e.g. "Progress: Halfway through") |
| `hero_body` | TEXT | lead‑story paragraph (lead slot only; gets a drop cap) |
| `hero_progress` | TEXT | progress chip (e.g. "Mid‑way") |
| `local_cover_path` | TEXT | path under `book_covers_additional/` when no ISBN cover |
| `date_added` | DATE DEFAULT CURRENT_DATE | |

### Sections

| Key | Display name |
|---|---|
| `software` | Software Related Books |
| `engineering` | Engineering & Mathematics |
| `quant` | Quantitative Finance |
| `philosophy` | Greater Awareness & Philosophy |

### Status → CSS class

| Status | Label | CSS class |
|---|---|---|
| `read` | Read | `status-read` |
| `reading` | Reading | `status-reading` |
| `list` | Reading List | `status-list` |

The live data originates from `BOOKS_DATA`, a large in‑file Python list in `librarian.py`, but that list is **only a one‑time migration seed**. After `migrate`, `library.db` is authoritative.

---

## 6. The generator / CLI (`librarian.py`)

A single‑file Python 3 program (stdlib only: `sqlite3`, `sys`, `html`, `datetime`, `pathlib`). Entry point dispatches on `sys.argv[1]`.

### Commands

```
python librarian.py migrate          # seed library.db from BOOKS_DATA (once; --force to reset)
python librarian.py add              # interactively add a book (prompts)
python librarian.py list             # list books [--section <s>] [--status <s>]
python librarian.py update <id>      # edit a book's fields (Enter to keep, "-" to clear)
python librarian.py remove <id>      # delete a book (confirms)
python librarian.py hero <id>        # set newspaper hero fields for a Reading book
python librarian.py generate         # rebuild index.html + library.md from library.db
```

Most mutating commands offer to run `generate` afterward.

### `cmd_generate()` — the heart of the build

1. Ensures the schema and reads `templates/index_base.html`.
2. Replaces placeholders:
   - `%%NEWSPAPER_DYNAMIC%%` → `render_hero(conn)`
   - `%%MASTHEAD_DATE%%` → current **Hong Kong (UTC+8)** date, formatted e.g. `Sunday, 26 June 2026, <i>Hong Kong</i>`
   - `%%BOOKS_software%%`, `%%BOOKS_engineering%%`, `%%BOOKS_quant%%`, `%%BOOKS_philosophy%%` → joined `render_book_card()` output per section, ordered by `sort_order, id`
   - `%%FOOTER_DATE%%` → local today's date
3. Writes `index.html`.
4. Calls `_generate_md(conn)` to write `library.md` (sectioned export + a static "Recommended Reading" block + totals/last‑updated footer).

### Rendering functions

- **`render_book_card(book)`** — emits the expandable `.book-card` (header with title/author/status badge/expand chevron; details with cover, "My Notes", "About", and the shared Utterances comments block). Notes/about blocks are omitted when empty.
- **`render_hero(conn)`** — selects `status='reading'` books with a `hero_slot`, ordered `lead → side → bottom` then `hero_sort`. Builds:
  - a `.section-banner` reading **"N Volume(s) Under Active Review"** where N is the count of all `reading` books;
  - a `.newspaper-top` grid: the `lead` story (2‑col, drop‑capped body) plus stacked `side` stories;
  - an optional `.newspaper-bottom-row` of `bottom` stories.
- **`_cover_div` / `_hero_cover_src`** — choose a cover source: `local_cover_path` if set, else Open Library `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`, else a "No cover available" fallback. An `onerror` handler hides broken images and applies the fallback.
- **`e()`** — HTML‑escapes text (quotes left intact).

---

## 7. The template (`templates/index_base.html`)

A thin HTML skeleton:

- `<head>` loads `flip-init.js` early, Google Fonts (Playfair Display, IM Fell English, Libre Baskerville, Inter), and `styles.css`.
- A sticky header/nav ("Arjun's Archives" logo + links to Reading, Reading List, Archive, Library).
- A `newspaper-hero` section containing the masthead (`The Arjun Dispatch`, Vol. I · No. 1, `%%MASTHEAD_DATE%%`, tagline "On the Desk") followed by `%%NEWSPAPER_DYNAMIC%%`.
- A `<main id="library">` with four `library-section`s, each holding a `%%BOOKS_*%%` placeholder.
- A footer with `%%FOOTER_DATE%%`.
- Scripts at the end: `app.js`, `html2canvas.min.js`, `page-transition.js?v=5`.

---

## 8. Presentation files

### `styles.css`
All styling for `index.html`. Highlights:
- **Design tokens** (`:root`): cream `#f9f7f4`, taupe, warm/dark gray, accent `#8b7a6f`, soft‑black.
- **Body texture**: an inline SVG `feTurbulence` fractal‑noise grain at low opacity.
- **Newspaper hero**: aged‑newsprint background (layered radial gradients for foxing + SVG grain), top hairline rules, double‑rule masthead, black section banner, CSS‑grid editorial layout (`.newspaper-top` 3‑col with a 2×2 lead span; `.newspaper-bottom-row` equal columns).
- **Story typography**: kickers, lead/side/small headlines (Playfair), italic decks (Libre Baskerville), uppercase bylines, justified body with a large `::first-letter` drop cap, bordered progress chip.
- **Sepia covers**: `filter: sepia(0.35) saturate(1.1)` on hero and card images.
- **Entrance animation** `newsEntrance`, suppressed by `.flip-arriving`.
- **Library cards**: white expandable cards; status‑tinted detail panels via `:has()`; `slideDown` reveal; responsive single‑column layout under 768px.

### `app.js`
Click handling for `.book-card` expand/collapse, ignoring clicks inside the comments/iframe so commenting doesn't toggle the card.

### `flip-init.js`
Runs in `<head>` before paint: if the page was reached within 4s via a flip (sessionStorage `arjun_flip_at`), adds `flip-arriving` to `<html>` to skip the entrance fade and avoid a flash.

### `page-transition.js` — the page‑turn animation
A self‑contained module that makes internal navigation look like turning a newspaper page:
- Pre‑captures the current viewport to a `<canvas>` with **html2canvas** (refreshes on scroll/resize; has an aged‑paper fallback if the library is absent).
- On clicking an internal link, loads the destination in a hidden full‑screen iframe beneath an overlay canvas, then animates the snapshot **peeling right→left as a single cylindrical curl** (per‑strip mapping with front‑face shadow, curling underside, cast shadow, and a specular bend line). Easing/duration differ for first vs. repeat turns (`T_FIRST` 1150ms / `T_REPEAT` 640ms, tracked in sessionStorage). When the animation completes it sets `window.location`.
- Ignores hash, external, mailto, and tel links.

### `html2canvas.min.js`
Vendored third‑party DOM‑to‑canvas rasterizer (v1.4.1), downloaded from cdnjs. The only runtime JS dependency beyond the project's own scripts.

---

## 9. Secondary pages (`reading-list.html`, `archive.html`)

These are **hand‑authored, self‑contained** newspaper pages (inline `<style>`, their own copy of the flip‑init snippet, and references to the shared `html2canvas.min.js` + `page-transition.js`). They are **not generated** by `librarian.py`.

- **`reading-list.html`** — "The Reading Queue": queued (`list`) books laid out as editorial stories grouped by discipline, each section with its own banner and grid variant (`newspaper-top`, `newspaper-top-2col`, multi‑column bottom rows). Covers use a grayscale/contrast filter; items show a "Queued" chip.
- **`archive.html`** — "The Archive": finished books, same broadsheet treatment.

> Note: because these are independent, their book content is maintained by hand and can drift from `library.db`; only `index.html`/`library.md` are DB‑driven.

---

## 10. Covers

- Primary source: **Open Library** by ISBN — `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`.
- Books without a usable ISBN cover use `local_cover_path` pointing into `book_covers_additional/` (e.g. signals & systems, microelectronics, sun & steel, the Prize, inside the black box, a practical guide to quant interviews, bayesian statistics).
- Broken images trigger an `onerror` handler that hides the `<img>` and shows a "No cover available" fallback.
- All covers are sepia‑toned via CSS on `index.html` (grayscale on the secondary pages).

---

## 11. Comments

Each library card's expanded view embeds an **Utterances** widget that maps comments to **GitHub Issues** on the `Arjun-html/Librarian` repo via `issue-term="pathname"`. The script tag is emitted by `render_book_card`, so every card shares one comment thread keyed by page path.

---

## 12. The desktop GUI (`librarian_gui.py`)

A **Tkinter** app that reuses the `librarian.py` engine (imports it; the engine's CLI is guarded by `__main__`, so importing is side‑effect‑free). Features:
- A left **Treeview** list of all books; a right **scrollable form** to add/edit.
- Fields for title, author, section (combobox), status (radio), ISBN, cover image (file picker that copies the chosen file into `book_covers_additional/` with a sanitized name; optional **Pillow** thumbnail preview if installed), My Notes, About/AI Notes.
- A collapsible **Newspaper hero** panel (slot/kicker/headline/deck/byline/progress/body) enabled only when status is "Reading".
- Buttons: New, **Save**, **Save + Regenerate** (calls `librarian.cmd_generate()`), Delete, Regenerate site.
- Handles `hero_sort` assignment automatically when a book is newly featured.

This gives a no‑terminal, no‑Claude workflow over the same database.

---

## 13. Sync‑check hook (`check_sync.py` + `.claude/settings.json`)

- Configured as a **PostToolUse** hook that runs `python check_sync.py` after `Edit`/`Write` to `index.html`.
- The script regex‑extracts `{alt_text: isbn}` from Open Library cover `<img>` tags within the hero section vs. the library section and reports any title whose hero ISBN disagrees with its library‑card ISBN (exit 1 + warning). Books using local covers are skipped.
- Now that content comes from one DB, mismatches shouldn't occur; the check remains a guard.

---

## 14. Tests (`test_librarian.py`)

A procedural smoke‑test script (run directly) that prints: total/by‑status counts, the first few raw rows, hero‑eligible books, a sample rendered card, a sample rendered hero fragment, per‑section counts, and cover‑source breakdown (ISBN vs. local vs. none). It validates DB connectivity and that the renderers run end‑to‑end.

---

## 15. Dependencies

| Dependency | Type | Used by | Purpose |
|---|---|---|---|
| **Python 3** (stdlib: `sqlite3`, `html`, `datetime`, `pathlib`, `sys`, `re`, `shutil`) | runtime/build | `librarian.py`, `check_sync.py`, tests | DB, rendering, hooks |
| **SQLite** (via `sqlite3`) | data store | engine | single source of truth |
| **Tkinter** (stdlib) | GUI | `librarian_gui.py` | desktop editor |
| **Pillow (PIL)** | optional | GUI | cover thumbnail preview (gracefully skipped if absent) |
| **html2canvas 1.4.1** | vendored JS | page transition | snapshot viewport for the page‑turn |
| **Google Fonts** | external CSS | all pages | Playfair Display, IM Fell English, Libre Baskerville, Inter |
| **Open Library covers API** | external | covers | book cover images by ISBN |
| **Utterances** | external JS | library cards | GitHub‑Issues‑backed comments |
| **Claude Code hooks** | tooling | `.claude/settings.json` | runs the sync check |

No package manager / lockfile is used; there is no build toolchain beyond running the Python script.

---

## 16. How it was built (history)

From the git log, the project evolved roughly as:

1. **`4bed0a2`** Initial `index.html` + `library.md`.
2. **`2a8543d`** Typography pass (Times New Roman headings) and rename to "Arjun's Library".
3. **`e41f236`** Rename header to "Arjun's Archives"; add `CLAUDE.md`.
4. **`5cccd90`** Fix quant‑finance cover ISBNs/alt text.
5. **`0edbca3`** Add the ISBN sync check + PostToolUse hook.
6. **`c1d6217`** Add the newspaper‑style `archive.html` and `reading-list.html`; switch the Prize cover to a local file.
7. **`58c298d` / `b52842f`** Add and merge the Tkinter GUI (`add-library-gui` branch).
8. **`a7178fd`** Swap grayscale covers for warm sepia.
9. **`f1ff2e8`** Add paper‑grain texture to the secondary pages; update `library.md`.
10. **`12a7ac9`** Make the masthead banner count and date dynamic.
11. **`d360ad5`** Gitignore screenshots/PDFs/Playwright artifacts.
12. **`54fdc3c`** Restore hand‑edited `index.html`; fix banner/date/tagline; ship the page‑turn animation.
13. **`594a0db`** *(current)* **Separate presentation from content so `generate` can't clobber design** — the decisive refactor that produced today's `templates/index_base.html` + standalone `styles.css`/JS architecture.

The recurring theme is the painful lesson that inline styling in a *generated* file gets destroyed on regeneration — ultimately resolved by the content/presentation split.

---

## 17. Standard workflows

**Add a book**
1. `python librarian.py add` (or the GUI).
2. If status is **Reading** and it should appear on the front page: `python librarian.py hero <id>` (or the GUI hero panel) to set slot/kicker/headline/deck/progress.
3. `python librarian.py generate` to rebuild `index.html` + `library.md`.

**Edit content** → change `library.db` via CLI/GUI → `generate`.
**Edit design** → edit `styles.css` / the JS directly → nothing else.
**Edit masthead skeleton** → edit `templates/index_base.html` → `generate`.

**Golden rule:** never hand‑edit `index.html` or `library.md` — both are regenerated from the database.

---

## 18. Notable constraints & quirks

- **Masthead date is Hong Kong (UTC+8)**; the footer date is the build machine's local date.
- The **"N Volumes Under Active Review"** count reflects *all* `reading` books, not just those shown in the hero.
- The hero only renders `reading` books that also have a `hero_slot`; setting hero fields on a non‑reading book warns but is allowed.
- `reading-list.html` and `archive.html` are **not** DB‑driven and must be maintained by hand.
- The page‑turn relies on html2canvas succeeding; it degrades to an aged‑paper fallback sheet otherwise.
- Comments require the visitor to authorize Utterances against GitHub.
- The Open Library and Google Fonts dependencies mean covers/fonts need network access; broken covers fall back gracefully.

---

*End of specification.*
