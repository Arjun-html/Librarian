# "In the Galleries" — plan

*Status: planning only, nothing built. Written up so we can pick this back up without re-deriving the design. Do not build from this without a green light — see Open questions at the end.*

## One-liner

A third generated section, alongside Library and Essays & Thoughts: a museum/gallery-visit journal, sourced from the `ART` folder in Arjun's Obsidian vault. Nav label: **In the Galleries**.

## The unit is the visit, not the artwork

Confirmed in conversation: this mirrors Essays' architecture (one generated page per unit, freely composed) but the unit is a **visit**, not an essay. A visit page shows everything seen on that outing — images plus Arjun's own notes — as one entry. There is no per-artwork page, no cross-visit search or index by artist/period. If a piece is unidentified, it just appears in its visit's entry as unidentified, the way the Obsidian notes already do ("Loose ends," "What to do next").

This also matches how the source material is already organized — the Obsidian vault groups by outing ("Blooming — HKMoA 2026," "Wong Tai Sin Temple and Chi Lin Nunnery — 21 June 2026," "Art Basel Hong Kong 2026"), not as a flat list of artworks, even though individual per-artwork notes exist today as a side effect of how the vault template works.

## Content scope — deliberately lean

Per-artwork, on the site:
- The reference plate — a clean museum-quality reproduction — **when one exists**. Public-domain Wikimedia Commons images for identified major works (Monet, Hokusai, Goya, Michelangelo, etc.).
- Arjun's own photo of the piece, captioned "As I saw it" — the old exhibition-review-page convention of running a wire/courtesy reproduction next to the critic's own account, which is what prompted this whole section.
- Name, artist/period if known, else "Unidentified."

**Explicitly not migrated:** the two-paragraph art-historical background and artist-biography prose that the richer Obsidian notes carry (e.g. `Water Lily Pond.md`). That stays Obsidian-only. The site's version is a personal notebook, not a catalogue essay — Arjun's own visit notes carry the voice instead.

## What actually exists in the source material (checked, not assumed)

- **3 visits documented so far:** `Blooming — HKMoA 2026` (10 artworks — the Monet/Hokusai/Chinese-export-painting exhibition), `Wong Tai Sin Temple and Chi Lin Nunnery — 21 June 2026` (4 objects, temple + nunnery combined in one note), `Art Basel Hong Kong 2026` (4 unattributed gallery-booth pieces).
- **~21 individual artwork notes** exist as a side effect of the vault's one-note-per-artwork template, each with a `Seen at` backlink to its visit.
- **Images: 21 of Arjun's own photos, only 6 Commons reference plates.** The reference/"as I saw it" pairing is only available for the well-attributed HKMoA loan pieces (Monet, Hokusai, Goya, Michelangelo, the two "Twelve Months of Flowers" panels). The temple objects and the unidentified Art Basel pieces have only Arjun's photo, sometimes not even a clean shot of the object itself (the Black Lacquer Dish note says the photo "caught the label but not the object"). **The reference image must be optional per artwork; the personal photo is the only thing close to guaranteed, and even that isn't always usable.**
- The "unidentified" convention is already established and should be carried over as-is: a piece can appear with no artist, no period, and a note about what would need confirming (the vault's own "Loose ends" / "What to do next" sections model this well).

## Proposed data model

Two new tables, not a repurposing of `books` — the shapes don't match (a book is one flat row with an ISBN-driven cover; a visit is one parent with a variable number of image-bearing children).

```sql
CREATE TABLE gallery_visits (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,          -- "Blooming: The Art of Gardens in East and West"
    venue       TEXT,                   -- "Hong Kong Museum of Art, Tsim Sha Tsui"
    visit_date  DATE NOT NULL,
    notes       TEXT,                   -- Arjun's own free-text notes on the outing
    sort_order  INTEGER
);

CREATE TABLE gallery_artworks (
    id             INTEGER PRIMARY KEY,
    visit_id       INTEGER NOT NULL REFERENCES gallery_visits(id),
    name           TEXT NOT NULL,       -- or "Unidentified — <short description>"
    artist         TEXT,                -- NULL when unidentified
    period         TEXT,                -- free text: "c. 1900", "Qianlong period", NULL if unknown
    reference_img  TEXT,                -- path under a new gallery_images/ dir; NULL if none exists
    own_photo_img  TEXT,                -- path under gallery_images/; NULL if no usable photo
    sort_order     INTEGER
);
```

## Generator/template additions (mirrors the Essays pipeline)

- `templates/galleries_index_base.html` — visit list, same idiom as `essays_index_base.html`.
- `templates/gallery_visit_base.html` — one visit's full page: title/venue/date banner, then each artwork as a card (reference plate + own photo side by side where both exist, own photo alone otherwise, "Unidentified" label where neither name nor artist is known), then Arjun's notes.
- `render_gallery_index(conn)` / `render_gallery_visit_page(visit)` in `librarian.py`, following the same shape as `render_essay_tile` / `render_essay_page`.
- Generated output: `galleries/index.html` + `galleries/[slug].html`, slugged via the existing `slugify()` / `assign_slugs()` machinery.
- Nav: **Front Page | Library | In the Galleries | Essays & Thoughts** (or wherever it reads best — order not yet decided) in all five templates plus this new one.
- `page-transition.js`'s `depth()` needs a rule for `/galleries/` so the reverse-flip direction is correct — slot it in alongside the `/books/` and `/essays/` cases (exact rank — before or after Essays in the reading order — not yet decided, see below).
- New `?v=N` bump on `styles.css` / `page-transition.js` per the project's existing cache-busting rule, once real changes land.

## Migration

A one-time script (parallel to how `BOOKS_DATA` seeded `library.db` originally) to read the Obsidian `ART` folder and populate the two new tables. Given the notes are hand-written Markdown, not structured data, this should be semi-automated — script does the mechanical extraction (title, venue, date, artist, image filenames), a human pass checks the result before it's treated as the source of truth. Do not attempt a fully-automatic one-shot parse and trust it blind.

## Design notes (not yet decided, flagging for later)

- Whether the artwork image pairing gets its own visual treatment distinct from the book covers' `--plate` muted-plate filter, since these are photographs of real objects/paintings, not print-shop book jackets. Worth a fresh look rather than reusing the book styling by default.
- Caption convention for the pairing — something like small italic captions under each image ("Reproduction: Art Institute of Chicago" / "As seen, 21 June 2026"), in keeping with how a broadsheet credits a wire photo.

## Non-goals for v1

- No per-artwork detail pages.
- No search or filter across artworks (by artist, period, venue, etc.).
- No import of the full art-historical prose from the richer Obsidian notes.
- No front-page hero/exhibit presence for this section, unless later requested — it stays nav-accessible only, same as Essays today.

## Open questions (decide before building)

1. Where does "In the Galleries" sit in the nav order, and in `depth()`'s reading-order ranking for the reverse page-flip?
2. Exact visual treatment for the reference/own-photo pairing (see Design notes above).
3. Anything else pulled over per artwork beyond name/artist/period — e.g. the collection/lender line HKMoA notes already carry ("Art Institute of Chicago, 1933.441")? Lean says no, but worth a final confirm since it's cheap context and already transcribed.
