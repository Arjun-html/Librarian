# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

A personal reading library website for a university student (Electrical/Mechanical Engineering and Computer Science). It's a static site with no build system — open `index.html` directly in a browser to view it.

## Dual source of truth

**This is the most important thing to understand about this repo.** Book data lives in two places that must be kept in sync:

- `library.md` — human-readable markdown, the authoritative source for book titles, authors, statuses, and personal notes
- `index.html` — the rendered website; contains the same data duplicated as HTML

When adding or updating a book, you must update both files. The "Currently Reading" hero section at the top of `index.html` is a third place to update if a book's status is "Reading".

## index.html architecture

The page has two main regions:

1. **Hero (`#currently-reading`)** — a manually maintained grid of `.reading-card` elements, one per book currently being read. This is separate from the main library and must be edited by hand.

2. **Main library (`#library`)** — four `<section class="library-section">` blocks (Software Related Books, Engineering & Mathematics, Quantitative Finance, Greater Awareness & Philosophy). Each book is a `.book-card` with a `.book-header` (always visible) and `.book-details` (hidden until clicked).

Book card expand/collapse is driven by the `expanded` CSS class toggled via a JS click handler. The JS is inline at the bottom of the file.

## Book status CSS classes

| Status | Class |
|---|---|
| Read | `status-read` |
| Reading | `status-reading` |
| Reading List | `status-list` |

## Book covers

Covers load from Open Library using the book's ISBN: `https://covers.openlibrary.org/b/isbn/{ISBN}-M.jpg`. Each `<img>` has an `onerror` handler that hides the image and adds `no-image` to the parent `.book-cover` div, showing a "No cover available" fallback. For books without ISBNs on Open Library, use `<div class="book-cover no-image"><span>No cover available</span></div>` directly.

## Comments

Each book card's expanded view includes an Utterances widget (`utteranc.es`) that maps comments to GitHub Issues on the `Arjun-html/Librarian` repo using `issue-term="pathname"`. Every book card uses the exact same script tag — comments are per-page-URL, not per-book, so all books on the same page share a URL and Utterances differentiates them by the GitHub issue title matching the pathname.

## Adding a new book

1. Add an entry to `library.md` under the correct section with Title, Author, Status, My Notes, and AI Notes fields following the existing format.
2. Add a `.book-card` div to the matching `<section>` in `index.html`, following the pattern of existing cards. Include the Utterances `<script>` block in `.comments-section`.
3. If status is "Reading", add a `.reading-card` to the hero grid.
4. Find the book's ISBN for the cover URL; if unavailable, use the `no-image` div pattern.
