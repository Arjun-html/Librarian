# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A personal reading library website for a university student (Electrical/Mechanical Engineering and Computer Science). It's a static site with no build step for viewing — but `index.html` is **generated**, not hand-written (see below). Open `index.html` in a browser to view it.

## Architecture: content vs. presentation (read this first)

**This is the most important thing to understand about this repo.** Two concerns are deliberately kept in separate files so they never clobber each other:

- **Content** (book data, the newspaper hero text, dates) lives in **`library.db`** (SQLite). It is rendered into `index.html` + `library.md` by the generator `librarian.py`.
- **Presentation** (all layout, colours, the aged-newsprint texture, the sepia cover filters, the page-flip animation) lives in standalone, hand-edited files: **`styles.css`**, **`app.js`**, **`flip-init.js`**, **`page-transition.js`**, **`html2canvas.min.js`**.

`index.html` is **generated output** — its `<head>` and `<body>` are a thin skeleton that links the presentation files and holds the rendered content. **Do not hand-edit `index.html`**; the next `generate` will overwrite it. (Historically the styling was inline in `index.html` and `generate` repeatedly clobbered it — that is why the split exists.)

### How to make changes

| To change… | Edit… | Then… |
|---|---|---|
| A book's title/author/status/notes/ISBN | `library.db` (via `librarian.py` or the GUI) | `python librarian.py generate` |
| The newspaper hero stories/headlines | `library.db` hero fields (GUI hero form) | `python librarian.py generate` |
| Colours, layout, fonts, textures | `styles.css` | nothing — it's loaded directly |
| Page-flip animation / behaviour | `page-transition.js`, `app.js`, `flip-init.js` | nothing — loaded directly |
| Masthead name / "Vol." / tagline / skeleton | `templates/index_base.html` | `python librarian.py generate` |

`generate` only ever writes `index.html` and `library.md`. It never touches the presentation files, so editing them is always safe.

## The generator (`librarian.py`)

```
python librarian.py migrate          # seed library.db from built-in BOOKS_DATA (once; --force to reset)
python librarian.py add              # interactively add a book
python librarian.py list             # [--section …] [--status …]
python librarian.py update <id>      # edit a book
python librarian.py remove <id>      # delete a book
python librarian.py hero <id>        # set newspaper hero fields for a Reading book
python librarian.py generate         # rebuild index.html + library.md from library.db
```

`cmd_generate` reads `templates/index_base.html`, fills placeholders (`%%BOOKS_software%%`, `%%BOOKS_engineering%%`, `%%BOOKS_quant%%`, `%%BOOKS_philosophy%%`, `%%NEWSPAPER_DYNAMIC%%`, `%%MASTHEAD_DATE%%`, `%%FOOTER_DATE%%`) via `render_book_card` / `render_hero`, and writes the two output files. `render_hero` derives the banner count ("N Volumes Under Active Review") and the masthead date (current Hong Kong / UTC+8 date) automatically.

`librarian_gui.py` is a Tkinter GUI over the same DB; its "Save + Regenerate" button calls `cmd_generate`.

**`library.md` is generated output too** (an export of the DB) — don't hand-edit it. `BOOKS_DATA` in `librarian.py` is only the one-time migration seed; the live source is `library.db`.

## Sections & book status classes

Sections: `software` (Software Related Books), `engineering` (Engineering & Mathematics), `quant` (Quantitative Finance), `philosophy` (Greater Awareness & Philosophy).

| Status | Class |
|---|---|
| Read | `status-read` |
| Reading | `status-reading` |
| Reading List | `status-list` |

## Book covers

Covers load from Open Library by ISBN: `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`. The `<img>` `onerror` handler hides the image and adds `no-image` to the parent `.book-cover`, showing a "No cover available" fallback. Books with no ISBN use a `local_cover_path` (a file under `book_covers_additional/`) or the `no-image` fallback. Cover images are sepia-toned via CSS (`filter: sepia(0.35) saturate(1.1)` in `styles.css`).

## Comments

Each book card's expanded view includes an Utterances widget mapping comments to GitHub Issues on `Arjun-html/Librarian` via `issue-term="pathname"`. The tag is emitted by `render_book_card`, so every card shares it automatically.

## Sync check hook

`check_sync.py` runs as a PostToolUse hook (configured in `.claude/settings.json`) after edits to `index.html`. It verifies that cover ISBNs in the newspaper hero match the corresponding library cards. Because content now comes from one DB, mismatches shouldn't occur, but the check remains as a guard.

## Adding a new book (correct workflow)

1. `python librarian.py add` (or use the GUI) — enter title, author, section, status, ISBN, notes.
2. If status is **Reading** and it should appear in the newspaper hero: `python librarian.py hero <id>` (or the GUI hero form) to set slot/kicker/headline/deck/progress.
3. `python librarian.py generate` to rebuild `index.html` + `library.md`.

Never add a book by hand-editing `index.html` — it is regenerated from the database.
