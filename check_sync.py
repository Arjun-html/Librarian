"""
Checks that every book cover ISBN in the newspaper hero section of index.html
matches the ISBN used in the corresponding main library book card (matched by
the img alt text, which is the book title).

Run automatically as a PostToolUse hook after edits to index.html.
Exits with code 1 and prints a warning if mismatches are found.
"""

import re
import sys
from pathlib import Path

HTML = Path(__file__).parent / "index.html"

if not HTML.exists():
    sys.exit(0)

content = HTML.read_text(encoding="utf-8")

COVER_RE = re.compile(
    r'src="https://covers\.openlibrary\.org/b/isbn/(\d+)-M\.jpg"[^>]*alt="([^"]+)"'
    r'|alt="([^"]+)"[^>]*src="https://covers\.openlibrary\.org/b/isbn/(\d+)-M\.jpg"'
)

def extract_isbns(html_fragment: str) -> dict[str, str]:
    """Return {alt_text: isbn} from all Open Library cover <img> tags."""
    result = {}
    for m in COVER_RE.finditer(html_fragment):
        if m.group(1):
            isbn, alt = m.group(1), m.group(2)
        else:
            isbn, alt = m.group(4), m.group(3)
        result[alt] = isbn
    return result

# Isolate the two regions
hero_match = re.search(
    r'<section class="newspaper-hero".*?</section>', content, re.DOTALL
)
library_match = re.search(
    r'<main id="library">.*?</main>', content, re.DOTALL
)

if not hero_match or not library_match:
    print("check_sync: could not locate hero or library section - skipping")
    sys.exit(0)

hero_isbns    = extract_isbns(hero_match.group(0))
library_isbns = extract_isbns(library_match.group(0))

mismatches = []
for title, hero_isbn in hero_isbns.items():
    if title not in library_isbns:
        # Library uses a local cover file for this book — nothing to compare, skip.
        continue
    if library_isbns[title] != hero_isbn:
        mismatches.append(
            f"  '{title}' -> hero ISBN {hero_isbn} != library ISBN {library_isbns[title]}"
        )

if mismatches:
    print("SYNC MISMATCH: newspaper hero and library cards are out of sync:")
    for m in mismatches:
        print(m)
    print("Update both locations to use the same ISBN.")
    sys.exit(1)
else:
    print("OK: Hero/library ISBNs in sync")
