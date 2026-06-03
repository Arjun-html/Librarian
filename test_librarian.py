"""Quick smoke tests for librarian.py"""

import sys
import sqlite3
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from librarian import get_db, render_book_card, render_hero, SECTIONS, STATUS_LABEL

ROOT = Path(__file__).parent
DB   = ROOT / 'library.db'

def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)

# ── 1. DB connectivity & row count ────────────────────────────────
section("1. Database row count")
conn = get_db()
total = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
print(f"Total books in DB: {total}")

by_status = conn.execute(
    "SELECT status, COUNT(*) FROM books GROUP BY status ORDER BY status"
).fetchall()
for row in by_status:
    print(f"  {STATUS_LABEL[row[0]]:<14}: {row[1]}")

# ── 2. First 3 books raw from DB ──────────────────────────────────
section("2. First 3 books (raw DB rows)")
books = conn.execute("SELECT * FROM books ORDER BY section, sort_order LIMIT 3").fetchall()
for b in books:
    print(f"  ID {b['id']:>2} | {b['title'][:45]:<45} | {b['author'][:30]:<30} | {b['section']:<12} | {STATUS_LABEL[b['status']]}")

# ── 3. Hero-eligible books ────────────────────────────────────────
section("3. Hero-eligible books (status=reading, hero_slot set)")
heroes = conn.execute(
    "SELECT id, title, hero_slot, hero_sort, hero_kicker FROM books "
    "WHERE status='reading' AND hero_slot IS NOT NULL "
    "ORDER BY CASE hero_slot WHEN 'lead' THEN 0 WHEN 'side' THEN 1 ELSE 2 END, hero_sort"
).fetchall()
for h in heroes:
    print(f"  [{h['hero_slot']:<6}] {h['title'][:45]:<45}  kicker: {h['hero_kicker']}")

# ── 4. Render first book card HTML ───────────────────────────────
section("4. Rendered HTML for book ID 1 (Python for Finance)")
b = conn.execute("SELECT * FROM books WHERE id=1").fetchone()
card_html = render_book_card(b)
# Print first 800 chars so it's readable
print(card_html[:800])
print("  ... [truncated]")

# ── 5. Hero HTML snippet ──────────────────────────────────────────
section("5. Hero section HTML (first 600 chars)")
hero_html = render_hero(conn)
print(hero_html[:600])
print("  ... [truncated]")

# ── 6. Books per section ──────────────────────────────────────────
section("6. Book count per section")
for sec in SECTIONS:
    n = conn.execute("SELECT COUNT(*) FROM books WHERE section=?", (sec,)).fetchone()[0]
    print(f"  {sec:<14}: {n} books")

# ── 7. ISBN coverage ──────────────────────────────────────────────
section("7. Cover source breakdown")
isbn_count  = conn.execute("SELECT COUNT(*) FROM books WHERE isbn IS NOT NULL").fetchone()[0]
local_count = conn.execute("SELECT COUNT(*) FROM books WHERE local_cover_path IS NOT NULL").fetchone()[0]
none_count  = conn.execute("SELECT COUNT(*) FROM books WHERE isbn IS NULL AND local_cover_path IS NULL").fetchone()[0]
print(f"  OpenLibrary ISBN : {isbn_count}")
print(f"  Local cover file : {local_count}")
print(f"  No cover         : {none_count}")

conn.close()
print("\nAll checks passed.")
