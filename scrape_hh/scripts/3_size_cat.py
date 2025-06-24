#!/usr/bin/env python3
"""
add_size_cat.py – lägger till/fyller size_frac (REAL) + size_cat (TEXT)
i tabellen actions.

• Projektroten = första mapp uppåt som innehåller config.txt
• Databasen antas ligga i   <ROOT>/local_data/database/heavy_analysis.db
  – om inte: ange -db "C:/full/path/heavy_analysis.db"
"""

from __future__ import annotations
import argparse, sqlite3, sys
from math import inf
from pathlib import Path

# ────────────────────────────────────────────────────────────────────
# 0. Sök projektroten & database
# -------------------------------------------------------------------
# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from script_paths import ROOT, DST_DB

DEFAULT_DB = DST_DB  # Använder centraliserad path-hantering

# ────────────────────────────────────────────────────────────────────
# 1. Gränser för tiny / small / …   (ändra om du vill)
# -------------------------------------------------------------------
POST = {         # flop/turn/river  (relativt pot_before)
    "tiny" :(0.01,0.20), "small":(0.20,0.35), "medium":(0.35,0.55),
    "big"  :(0.55,0.85), "pot"  :(0.85,1.10), "over"  :(1.10,1.75),
    "huge" :(1.75,inf),
}
PRE  = {         # preflop  (antal BB = amount_to / BB)
    "tiny" :(0.01,1.50), "small":(1.50,2.25), "medium":(2.25,3.00),
    "big"  :(3.00,3.75), "pot"  :(3.75,4.50), "over"  :(4.50,6.00),
    "huge" :(6.00,inf),
}
SIZING = {"preflop": PRE, "flop": POST, "turn": POST, "river": POST}

def label(frac: float, street: str) -> str:
    for lbl,(lo,hi) in SIZING.get(street,POST).items():
        if lo <= frac < hi:
            return lbl
    return "unknown"

# ────────────────────────────────────────────────────────────────────
# 2. SQL-helpers
# -------------------------------------------------------------------
def ensure_cols(con: sqlite3.Connection) -> None:
    cols = {c[1] for c in con.execute("PRAGMA table_info(actions)")}
    if "size_frac" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN size_frac REAL")
        print("➕ lade till size_frac")
    if "size_cat" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN size_cat TEXT")
        print("➕ lade till size_cat")

SQL = """
SELECT a.rowid, a.street,
       a.amount_to, a.invested_this_action, a.pot_before,
       hi.big_blind
FROM actions a
JOIN hand_info hi ON hi.hand_id = a.hand_id
WHERE a.size_cat IS NULL
  AND (a.action LIKE 'r%' OR a.action LIKE 'b%')
"""

def frac(row: sqlite3.Row) -> float | None:
    st = row["street"].lower()
    if st == "preflop":
        bb = row["big_blind"]
        return row["amount_to"] / bb if bb else None
    pot = row["pot_before"]
    return row["invested_this_action"] / pot if pot else None

# ────────────────────────────────────────────────────────────────────
# 3. main
# -------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-db","--database",help="sökväg till heavy_analysis.db")
    args = ap.parse_args()

    db = Path(args.database).expanduser().resolve() if args.database else DEFAULT_DB
    if not db.exists():
        sys.exit(f"❌ Hittar inte databasen: {db}")

    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    ensure_cols(con)

    cur = con.cursor(); batch = []; done = 0
    for r in cur.execute(SQL):
        f = frac(r)
        lab = label(f,r["street"]) if f is not None else "unknown"
        batch.append((f, lab, r["rowid"]))
        if len(batch) >= 5000:
            con.executemany(
                "UPDATE actions SET size_frac=?, size_cat=? WHERE rowid=?", batch
            )
            con.commit(); done += len(batch); batch.clear()
            print(f"✓ {done:,} rader uppdaterade …")

    if batch:
        con.executemany(
            "UPDATE actions SET size_frac=?, size_cat=? WHERE rowid=?", batch
        )
        con.commit(); done += len(batch)

    con.close()
    print(f"✅ klart – {done:,} actions fick size_frac + size_cat")

if __name__ == "__main__":
    main()
