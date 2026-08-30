# Marginalia — plan

*Status: planning only, nothing built. Written up so we can pick this back up without re-deriving the design.*

## One-liner

A fourth generated section — the short-form companion to Essays & Thoughts. Nav label: **Marginalia**. Where Essays holds the long-form pieces, Marginalia holds the short ones: a paragraph, a quote-and-reaction, a diary-scale observation. The name comes from the practice of scrawling notes in a book's margin — apt for a reading journal, and it briefly lived here already as a discarded tagline ("From the Commonplace Book") before being cut as a duplicate of the black section banner.

## Why a separate section rather than folding into Essays

The source material already splits this way — Arjun's Obsidian vault has separate `Long form essays` and `Quick Thoughts` folders, not one flat list. The two registers are genuinely different lengths and different jobs: essays run 500–1500+ words and make an argument or tell a full story; the Quick Thoughts pieces run 60–430 words and capture one observation. Publishing them on the same page at the same visual weight would either bury the quick ones or bloat the essays list with fragments.

## Source material inventory (checked, not assumed)

The `Quick Thoughts` folder has 9 files. Two are excluded outright:
- `arjun-writing.md` is a Claude-skill definition (Arjun's writing-voice spec for AI-assisted drafting), not a personal note — not content.
- `Love....md` opens with Arjun's own header "FIX THESE ESSAYS!!!" — explicitly marked as unfinished/needs editing by him. Not publish-ready as-is.

The remaining 7 are real candidates, already skimmed for length/register:

| Note | ~Words | Notes |
|---|---|---|
| Man, Am I Lucky | ~230 | Names Marcus Aurelius directly — pairs naturally with *Meditations* already on the shelf |
| Why Did I Not Start 'X' Earlier | ~330 | Reading habit and life philosophy in one piece; strong |
| Paul Graham's Great Work | ~260 | Quotes-plus-reaction to an essay — the most literally "marginalia" of the set |
| Random Walk to Graphene | ~155 | A Prof. Andre Geim talk at HKU; title echoes *A Random Walk Down Wall Street*, already on the shelf |
| The Bond Way to Do It | ~60 | Shortest of the set — a small numbered list, genuinely marginal-note scale |
| Crypto Stuff | ~85 | Echoes the crypto interest already visible in the library (the Levine piece) |
| LinkedIn Post on Student Ambassador Work | ~400 | Different register — career/institutional voice, was written for LinkedIn. Borderline: may read as out of place next to the more personal pieces. Flagging, not recommending outright. |

None of these currently carry frontmatter (title/date/category) the way essay source files do — that would need adding when each is brought over, same as essays already require.

## This is architecturally simpler than Galleries

Essays are **not** a database table — they're flat Markdown files in `essays/src/*.md` with YAML frontmatter, parsed by `parse_essay()`. Marginalia should follow the exact same pattern rather than inventing a new content model: a `marginalia/src/*.md` folder, a `parse_marginalia_entry()` mirroring `parse_essay()`, reusing `ESSAY_CATEGORIES` or a similar small set. No schema migration, no new SQLite table — just a new folder + parser + templates, which matches the lighter-weight spirit of the content itself.

## Open question — the real design fork

Essays are one generated page per essay (`essays/[slug].html`), linked from an index. Does Marginalia work the same way, or does it read as **one continuous running page** — entries stacked in reverse-chronological order on a single page, the way an actual commonplace book or diary is paged through rather than clicked between?

Leaning toward the single running page — it matches "marginalia"/"notebook" as a physical object better than a grid of individual pages would, and at 60–430 words each, a dedicated page per entry feels like overkill. But this changes the generator shape enough that it's worth deciding deliberately rather than defaulting to copying the Essays pattern.

## Nice-to-have, not core scope

A few of these entries directly reference a book already on the shelf (Man, Am I Lucky → *Meditations*; Random Walk to Graphene's title playing on *A Random Walk Down Wall Street*). A small backlink from the entry to the book's page (`↳ see [Meditations](../books/meditations.html)`) would reinforce the site's whole reading-journal premise. Worth doing once the section exists; not a blocker to building it.

## Open questions

1. Single running page vs. one page per entry (see above) — this decides the generator shape.
2. Nav placement/order — where does Marginalia sit relative to In the Galleries and Essays & Thoughts, and what does that mean for `page-transition.js`'s `depth()` ranking (see `GALLERIES_PLAN.md` for the same question there — worth deciding both at once since they're adjacent).
3. Whether the LinkedIn Student Ambassador post belongs here at all, given its different register.
4. Whether entries need explicit dates shown, or just appear in the order Arjun wants them read (the vault files themselves aren't dated in frontmatter today).
