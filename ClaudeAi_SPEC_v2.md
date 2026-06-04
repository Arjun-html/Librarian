# Project Specification — Arjun's Archives (Claude Librarian)

*A complete A‑to‑Z technical and design specification of the personal reading‑library website.*

**Spec version:** 2.0 — updated to reflect expanded site vision (library.html, per-book pages, essays, nav, animation variants)

---

## 1. Executive Summary

**Arjun's Archives** is a personal website for a Year‑2 university student studying Electrical/Mechanical Engineering and Computer Science. It has three distinct sections:

1. **Front page (`index.html`)** — A Financial Times‑style newspaper front page: masthead, editorial hero featuring currently‑reading books, a brief "About" column, social links, and truncated previews of book entries. This is the only page that must look and feel exactly like a broadsheet front page.
2. **Library (`library.html`)** — All books read or currently reading, sorted alphabetically, displayed as cover + title + author + status chip. Each book links to its own dedicated page. Books with `status = list` are excluded from the website entirely but remain in the database for CLI/GUI use.
3. **Essays & Thoughts (`essays/index.html`)** — A listing of personal essays and reflections. *(Design to be discussed separately; placeholder in this spec.)*

The site is **static** (no server, no build step to view — just open the HTML), but `index.html`, `library.html`, and all files under `books/` are **generated artifacts** produced by `librarian.py` from `library.db`. The essays section uses flat Markdown/HTML files with a separate manifest.

The defining architectural principle remains **strict separation of content from presentation**: regenerating the site can never clobber hand‑crafted design.

A signature feature is the **page‑turn animation** (`page-transition.js`) that captures the current screen with `html2canvas` and rolls it away like a turning newspaper sheet. The animation now has **three randomised variants** to add character.

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
| `section` | TEXT NOT NULL | CHECK ∈ `software`, `engineering`, `quant`, `philosophy` |
| `status` | TEXT NOT NULL | CHECK ∈ `read`, `reading`, `list` |
| `my_notes` | TEXT | Personal commentary (100–400 words, hand‑written) |
| `ai_notes` | TEXT | "About" blurb (AI‑generated; being phased out from display) |
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

1. **`index.html`** — from `templates/index_base.html`, same placeholder substitution as v1, with two additions:
   - `%%ABOUT_BLURB%%` — a short editorial "About this publication" box (text stored in the template itself, hand‑edited).
   - Per book: the `my_notes` preview is truncated to ~150 characters with `…` and wrapped in an `<a href="books/[slug].html">Read full entry →</a>` link.

2. **`library.html`** — from `templates/library_base.html`:
   - Queries all books where `status IN ('read', 'reading')`, ordered alphabetically by title.
   - Renders each as a `.book-tile`: cover image (sepia), title, author, status chip.
   - Each tile links to `books/[slug].html`.
   - `status = list` books are excluded entirely.

3. **`books/[slug].html`** — one file per `read`/`reading` book, from `templates/book_base.html`:
   - Slug: `title` lowercased, spaces→hyphens, non‑alphanumeric stripped (e.g. *"The Prize"* → `the-prize`).
   - Contains: cover image (large, sepia), title, author, section label, status chip, `my_notes` (full text, no truncation).
   - Does **not** include `ai_notes` or Utterances comments (clean, personal‑notes focus).
   - A `← Back to Library` link returns to `library.html`.

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

### New Rendering Functions

- **`render_book_tile(book)`** — emits `.book-tile` HTML for `library.html`.
- **`render_book_page(book)`** — emits the full HTML body content for `books/[slug].html`, substituted into `templates/book_base.html`.
- **`render_notes_preview(text, max_chars=150)`** — truncates `my_notes` for display on `index.html`.

### Existing Rendering Functions (unchanged except where noted)

- **`render_book_card(book)`** — expandable card for `index.html` (now shows truncated notes + link). Utterances script tag **removed**.
- **`render_hero(conn)`** — newspaper hero for `index.html`.
- **`_cover_div` / `_hero_cover_src`** — cover source resolution.
- **`e()`** — HTML escaping.

---

## 7. Templates

### `templates/index_base.html` (updated)

Same structure as v1 with these additions:
- Nav links updated to: **Front Page | Library | Essays & Thoughts** (replacing old Reading / Archive links).
- A new `%%MASTHEAD_STRAPLINE%%` placeholder directly under the masthead date for the site's purpose statement (e.g. *"A personal record of books read, annotated, and lived with"*). Strapline text is stored in the template itself.
- An `%%ABOUT_BLURB%%` placeholder in the hero grid for a static "About this publication / About me" column (text in template, not DB).
- `render_book_card` now emits truncated `my_notes` preview + `Read full entry →` link.

### `templates/library_base.html` (new)

Thin skeleton for `library.html`:
- `<head>` loads same fonts, `styles.css`, `flip-init.js`.
- A newspaper‑style banner: **"The Arjun Dispatch — Library"**, no full masthead.
- A `%%BOOK_TILES%%` placeholder (grid of `.book-tile` elements).
- Scripts at end: `html2canvas.min.js`, `page-transition.js`.

### `templates/book_base.html` (new)

Thin skeleton for per‑book pages:
- `<head>` loads fonts, `styles.css`, `flip-init.js`.
- A minimal newspaper header (masthead name only, no date/strapline).
- A `%%BOOK_CONTENT%%` placeholder.
- A `← Back to Library` nav link.
- Scripts at end: `html2canvas.min.js`, `page-transition.js`.

---

## 8. Presentation Files

### `styles.css` (extended)

All existing rules (tokens, texture, hero, cards, covers) are preserved. New rules added:

**Library grid (`.book-tiles-grid`):**
- CSS Grid, auto‑fill with `minmax(160px, 1fr)` columns.
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

### `app.js` (updated)
Click handling for `.book-card` expand/collapse on `index.html`. The special-case guard that previously ignored clicks inside the Utterances iframe (so commenting didn't toggle the card) is **removed** — no iframe is present anymore.

### `flip-init.js` (unchanged)
Suppresses entrance fade on flip‑arriving pages.

### `page-transition.js` (updated — three animation variants)

The existing single cylindrical‑curl animation is refactored into **three named profiles**. At the start of each transition, one is chosen at random with equal probability:

| Variant | Character | Duration | Key difference |
|---|---|---|---|
| `slowDramatic` | Weighty, deliberate | ~1 100 ms | Current easing, unchanged feel |
| `mediumCrisp` | Snappy broadsheet flip | ~650 ms | Faster ease‑in, less curl depth |
| `snapWithPeel` | Hesitates then lifts | ~900 ms | 80 ms pause + slight `skewX` peel before the main rotation begins |

Implementation:

```javascript
const VARIANTS = ['slowDramatic', 'mediumCrisp', 'snapWithPeel'];

function pickVariant() {
  return VARIANTS[Math.floor(Math.random() * VARIANTS.length)];
}
```

Each variant is an object `{ duration, easingFn, preDelay, peelSkew }`. The animation loop reads these at runtime. All other logic (html2canvas capture, iframe preload, fallback) is unchanged.

The existing `T_FIRST` / `T_REPEAT` distinction is retired; variant duration takes precedence. First‑navigation still gets slightly more weight toward `slowDramatic` (60/20/20 split on first turn, equal thereafter) to preserve the memorable first impression.

---

## 9. Front Page (`index.html`) — UX Clarity Improvements

The following changes address the "is this really the front page?" problem:

1. **Masthead strapline** — one line of italicised small‑caps text immediately below the date: *"A personal record of books read, annotated, and lived with — by Arjun [Lastname]"*. Makes the site's purpose legible at a glance.

2. **"About this publication" column** — one of the newspaper grid columns in the hero is a static editorial box (hand‑edited in `templates/index_base.html`). Modelled on an FT "About our correspondents" sidebar. Contains: who Arjun is, what this site is for, links to GitHub/LinkedIn.

3. **Navigation** — the sticky header nav is updated to three clear destinations: **Front Page | Library | Essays & Thoughts**. The existing "Reading", "Archive", "Reading List" links are removed.

4. **Section kickers** — book entries in the hero use self‑explanatory kickers like "Currently Reading" rather than just the discipline name, so first‑time visitors understand what they're looking at.

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
5. `librarian.py generate` runs automatically, writing/overwriting `books/[slug].html` and updating `index.html` (with the truncated preview) and `library.html`.
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
- **My Notes field** is now the primary writing surface for book entries (100–400 words). The label is updated from "My Notes" to "My Entry / Notes" to signal its importance.
- **Save + Regenerate** now also generates the per‑book page for the saved book (and regenerates `library.html`).
- The GUI does not expose essay management (essays are edited as files directly).

---

## 15. Sync‑Check Hook (`check_sync.py`)

Unchanged. Guards ISBN consistency between hero and library sections of `index.html`.

---

## 16. Tests (`test_librarian.py`)

Extended to smoke‑test:
- Slug generation (uniqueness, special characters, collision handling).
- That `books/` directory is created and contains at least one `.html` file after `generate`.
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

| Claude Code hooks | tooling | `.claude/settings.json` | sync check |

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

## 20. Planned but Out of Scope for v2

- Full essays pipeline (manifest, generator, image management) — *discussed separately*.
- Search / filter on `library.html`.
- Dark mode.
- RSS feed.

---

*End of specification — v2.0*
