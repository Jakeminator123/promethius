#!/usr/bin/env python3
# 5_add_j_score.py
# ────────────────
# Läser heavy_analysis.db, lägger till/fyller kolumnen j_score (1–100)
# baserat på range.txt (preflop) eller Treys-styrka (postflop) + risk.

from __future__ import annotations
import argparse, sqlite3, math, re, sys, os
from pathlib import Path

# ─── 0. Import centraliserad path-hantering ─────────────────────────
sys.path.append(str(Path(__file__).resolve().parent))
from script_paths import ROOT, DST_DB

DEFAULT_DB = DST_DB  # Använder centraliserad path-hantering

# ─── 1. treys (valfritt) ────────────────────────────────────────────
try:
    from treys import Card, Evaluator
    _treys = Evaluator()
except ModuleNotFoundError:
    _treys = None

# ─── 2. verktyg för kortsträngar ────────────────────────────────────
_CARD_RE = re.compile(r"([2-9TJQKA])([SHDCshdc])")
RANKS    = "23456789TJQKA"

def clean_cards(s: str | None) -> str:
    """Plockar ut exakt två kort och returnerar t.ex. 'AdAc'."""
    cards = _CARD_RE.findall(s or "")
    if len(cards) < 2:
        return ""
    return "".join(r + q for r, q in cards[:2])

def canon(hole: str) -> str:
    """
    Normaliserar hålkort till en “handnyckel” som matchar range.txt.
    Exempel:
        'AdAc'      → 'AA'
        'As7s'/'7sAs' → 'A7s'
        'As7d'/'7dAs' → 'A7o'
    """
    if len(hole) != 4:
        return ""
    r1, s1, r2, s2 = hole
    if RANKS.index(r2) > RANKS.index(r1):
        r1, s1, r2, s2 = r2, s2, r1, s1
    if r1 == r2:
        return r1 + r2
    suited = "s" if s1.lower() == s2.lower() else "o"
    return r1 + r2 + suited

# ─── 3. ladda range.txt (om den finns) ──────────────────────────────
_RANGE_LIST: list[str] = []          # händer i styrkeordning
_RANGE_MAP: dict[str, float] = {}    # 'AJo' → 0.83 …

def load_range(path: str | None = None) -> None:
    """Laddar range.txt och fyller _RANGE_MAP med värden 0–1."""
    global _RANGE_LIST, _RANGE_MAP
    if _RANGE_LIST:
        return
    p = Path(path) if path else Path(__file__).with_name("range.txt")
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")
    hands = [h.strip() for h in re.split(r"[,\s]+", txt) if h.strip()]
    filt = [h for h in hands if re.fullmatch(r"[2-9TJQKA]{2}[so]?|[2-9TJQKA]{2}", h)]
    if len(filt) < 10:
        return
    _RANGE_LIST = filt
    top = len(filt) - 1
    _RANGE_MAP = {h: 1 - i / top for i, h in enumerate(filt)}

# ─── 4. Chen-formeln (fallback när hand ej finns i range.txt) ───────
CHEN_BASE = dict(zip(
    "AKQJT98765432",
    [10, 8, 7, 6, 5, 4.5, 4, 3.5, 3, 2.5, 2, 1.5, 1]))
CHEN_GAP  = [0, 0, 1, 2, 4, 5]

def chen_pct(hole: str) -> float:     # 0–1
    if len(hole) != 4:
        return 0.25
    r1, s1, r2, s2 = hole
    if RANKS.index(r2) > RANKS.index(r1):
        r1, s1, r2, s2 = r2, s2, r1, s1
    pts = CHEN_BASE[r1]
    if r1 == r2:
        pts = max(pts * 2, 5)
    if s1.lower() == s2.lower():
        pts += 2
    gap = RANKS.index(r1) - RANKS.index(r2) - 1
    pts -= CHEN_GAP[min(gap, 5)]
    if gap <= 1 and RANKS.index(r1) < RANKS.index("Q"):
        pts += 1
    return max(0, min(pts, 20)) / 20.0

def preflop_pct(hole: str) -> float:
    key = canon(hole)                       # ← MATCHNINGEN SKEr HÄR
    if key and key in _RANGE_MAP:           #             ↑
        return _RANGE_MAP[key]              # top-hand → 1.0
    return chen_pct(hole)

# ─── 5. Treys-styrka post-flop ──────────────────────────────────────
def treys_pct(hole: str, board: str) -> float:
    tot_cards = (len(hole) // 2) + (len(board) // 2)
    if not _treys or tot_cards < 5:
        return 0.5
    try:
        h = [Card.new(hole[i:i+2]) for i in (0, 2)]
        b = [Card.new(board[i:i+2]) for i in range(0, len(board), 2)]
        score = _treys.evaluate(h, b)
        return 1 - _treys.get_five_card_rank_percentage(score)
    except Exception:
        return 0.5

# ─── 6. riskjustering ───────────────────────────────────────────────
def risk(inv: int, pot_before: int) -> float:
    if pot_before == 0:
        return 1.0
    r = min(inv / pot_before, 5)            # cap = 5× pott
    return 1 - math.log1p(r) / math.log1p(5)

# ─── 7. SQL & logik ─────────────────────────────────────────────────
SQL_GET = """
SELECT rowid, street, holecards, board_cards,
       invested_this_action AS inv, pot_before AS pb
FROM   actions
WHERE  j_score IS NULL
"""
SQL_UPD = "UPDATE actions SET j_score=? WHERE rowid=?"

def score_row(r: sqlite3.Row) -> float:
    hole   = clean_cards(r["holecards"])
    board  = clean_cards(r["board_cards"])
    street = (r["street"] or "").lower()
    
    if street == "preflop":
        base = preflop_pct(hole)
        adj = 1.0  # Ingen risk-justering preflop - rakt av från range.txt
    else:
        base = treys_pct(hole, board)
        adj = risk(r["inv"] or 0, r["pb"] or 0)  # Risk-justering bara postflop
        
    return round(max(0, min(base, 1)) * adj * 99 + 1, 1)

def ensure_col(con: sqlite3.Connection):
    # säkerställ att tabellen finns
    ok = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='actions'"
    ).fetchone()
    if not ok:
        sys.exit("❌ heavy_analysis.db saknar tabellen 'actions' – kör build_heavy_analysis.py först.")
    # lägg till kolumnen vid behov
    cols = {c[1] for c in con.execute("PRAGMA table_info(actions)")}
    if "j_score" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN j_score REAL")
        print("➕ lade till kolumn j_score")

# ─── 8. main ────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-db", "--database", help="Path till heavy_analysis.db")
    ap.add_argument("--range", help="Egen path till range.txt")
    args = ap.parse_args()

    load_range(args.range)                              # range.txt
    db = Path(args.database).expanduser().resolve() if args.database else DEFAULT_DB
    if not db.exists():
        sys.exit(f"❌ hittar inte databasen: {db}")

    con = sqlite3.connect(db); con.row_factory = sqlite3.Row
    ensure_col(con); cur = con.cursor()

    batch, done = [], 0
    for row in cur.execute(SQL_GET):
        batch.append((score_row(row), row["rowid"]))
        if len(batch) >= 5000:
            cur.executemany(SQL_UPD, batch); con.commit()
            done += len(batch); batch.clear()
    if batch:
        cur.executemany(SQL_UPD, batch); con.commit(); done += len(batch)

    con.close()
    print(f"✅ {done:,} actions fick j_score")

if __name__ == "__main__":
    main()
