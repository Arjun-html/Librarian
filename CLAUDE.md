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

- **Built:** front page (`index.html`), `library.md` export, the SQLite source of truth, CLI + Tkinter GUI, dynamic newspaper hero, page-turn animation, sync-check hook. **Utterances comments have been removed.**
- **Roadmap (not yet built — see v2 spec §6, §10, §11):** `library.html`, per-book `books/[slug].html` pages, `slugify()` + collision handling, `render_book_tile` / `render_book_page` / `render_notes_preview`, masthead strapline + "About" blurb, three page-turn animation variants, nav updated to **Front Page | Library | Essays & Thoughts**.

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
| Colours, layout, fonts, textures | `styles.css` | nothing — it's loaded directly |
| Page-flip animation / behaviour | `page-transition.js`, `app.js`, `flip-init.js` | nothing — loaded directly |
| Masthead / nav / strapline / about blurb / skeleton | the relevant file in `templates/` | `python librarian.py generate` |

`generate` only ever writes the generated artifacts. It never touches the presentation files, so editing them is always safe.

**Golden rule:** never hand-edit `index.html`, `library.html`, `library.md`, or any file under `books/`.

## The generator (`librarian.py`)

```
python librarian.py migrate          # seed library.db from built-in BOOKS_DATA (once; --force to reset)
python librarian.py add              # interactively add a book
python librarian.py list             # [--section …] [--status …]
python librarian.py update <id>      # edit a book
python librarian.py remove <id>      # delete a book
python librarian.py hero <id>        # set newspaper hero fields for a Reading book
python librarian.py generate         # rebuild generated files from library.db
```

`cmd_generate` reads the template(s) under `templates/`, fills placeholders (`%%BOOKS_software%%`, `%%BOOKS_engineering%%`, `%%BOOKS_finance%%`, `%%BOOKS_philosophy%%`, `%%NEWSPAPER_DYNAMIC%%`, `%%MASTHEAD_DATE%%`, `%%FOOTER_DATE%%`) via `render_book_card` / `render_hero`, and writes the output files. `render_hero` derives the banner count ("N Volumes Under Active Review") and the masthead date (current Hong Kong / UTC+8 date) automatically.

`librarian_gui.py` is a Tkinter GUI over the same DB; its "Save + Regenerate" button calls `cmd_generate`.

**`library.md` is generated output too** (an export of the DB) — don't hand-edit it. `BOOKS_DATA` in `librarian.py` is only the one-time migration seed; the live source is `library.db`.

## Sections & book status classes

Sections: `software` (Software Related Books), `engineering` (Engineering & Mathematics), `finance` (Finance), `philosophy` (Greater Awareness & Philosophy).

> The former `quant` / "Quantitative Finance" section was renamed to the `finance` key / "Finance" label (key, DB rows, CHECK constraint, `%%BOOKS_finance%%` placeholder, and template all updated). Hand-authored legacy pages (`archive.html`, `reading-list.html`, slated for retirement in v2) still show the old "Quantitative Finance" banner; they are not DB-driven.

| Status | Label | Class | On the website? |
|---|---|---|---|
| Read | Read | `status-read` | yes |
| Reading | Reading | `status-reading` | yes (+ front-page hero) |
| Reading List | Reading List | `status-list` | no — DB/CLI/GUI only |

## Book covers

Covers load from Open Library by ISBN: `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`. The `<img>` `onerror` handler hides the image and adds `no-image` to the parent `.book-cover`, showing a "No cover available" fallback. Books with no ISBN use a `local_cover_path` (a file under `book_covers_additional/`) or the `no-image` fallback. Cover images are sepia-toned via CSS (`filter: sepia(0.35) saturate(1.1)` in `styles.css`).

## Sync check hook

`check_sync.py` runs as a PostToolUse hook (configured in `.claude/settings.json`) after edits to `index.html`. It verifies that cover ISBNs in the newspaper hero match the corresponding library cards. Because content now comes from one DB, mismatches shouldn't occur, but the check remains as a guard.

## Adding a new book (correct workflow)

1. `python librarian.py add` (or use the GUI) — enter title, author, section, status, ISBN, notes.
2. If status is **Reading** and it should appear in the newspaper hero: `python librarian.py hero <id>` (or the GUI hero form) to set slot/kicker/headline/deck/progress.
3. `python librarian.py generate` to rebuild the generated files.

Never add a book by hand-editing `index.html` — it is regenerated from the database.
