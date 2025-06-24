#!/usr/bin/env python3
"""
batch_preflop_analyzer.py  v1.9
────────────────────────────────────────────────────────────────────
• Läser HH från poker.db
• Matchar mot prefix-fri ranges_flat (action_sequence utan "PF:")
• Sparar i heavy_analysis.db → preflop_scores:

   hand_id | position | player | combo | seq | freq | best

    freq = NULL  → noden saknas i solver-DB
    freq = 0.0   → noden finns men solvern avråder från spelarens drag
    freq > 0     → solverns frekvens för spelarens drag

    best = 'y'   → spelaren valde ett av nodens högst frekventa drag
    best = 'n'   → det fanns ett bättre drag
    best = NULL  → noden saknas
"""

import json
import math
import re
import sqlite3
from pathlib import Path
import os

# Importera central path-hantering
import sys
ROOT_PROJECT = Path(__file__).resolve().parents[2]  # prom/
sys.path.append(str(ROOT_PROJECT))
from utils.paths import POKER_DB, HEAVY_DB

# ────────────── PROJEKTROT & KONFIGURATION ────────────────────
ROOT = Path(__file__).resolve().parent
while ROOT != ROOT.parent and not (ROOT / "config.txt").is_file():
    ROOT = ROOT.parent                        # kliv upp tills config.txt hittas

if not (ROOT / "config.txt").is_file():
    raise FileNotFoundError("Hittar ingen config.txt i någon överordnad mapp.")

# Läser key=value-rader i config.txt
CFG = dict(
    line.strip().split("=", 1)
    for line in (ROOT / "config.txt").read_text().splitlines()
    if "=" in line
)

# ────────────── SÖKVÄGAR ──────────────────────────────────────
SRC_DB    = POKER_DB
OUT_DB    = HEAVY_DB
RANGES_DB = ROOT_PROJECT / CFG.get("RANGES_PATH", "utils/trees_db/cash/poker_ranges.db")

SQLITE = {
    "HANDS":  SRC_DB,     # poker.db
    "RANGES": RANGES_DB,  # poker_ranges.db
    "OUT":    OUT_DB,     # heavy_analysis.db
}

# ────────────── KONSTANTER ────────────────────────────────────
POS_SYNONYM = {"UTG": {"UTG", "LJ"}, "LJ": {"UTG", "LJ"}}
RANKS   = "AKQJT98765432"
TOK_RE  = re.compile(r"r\d+|[fcx]", re.I)          # raise+tal | f/c/x
TOL     = 1e-9                                     # float-jämförelse

# ────────────── Hjälpfunktioner ───────────────────────────────
def canonical(combo: str) -> str:
    """'8h9s' → '9s8h' – högst rank först, suits gemener."""
    r1, s1, r2, s2 = combo[0].upper(), combo[1].lower(), combo[2].upper(), combo[3].lower()
    return f"{r1}{s1}{r2}{s2}" if RANKS.index(r1) <= RANKS.index(r2) else f"{r2}{s2}{r1}{s1}"

def tokenize(s: str):
    toks = TOK_RE.findall(s)
    return [t.lower() for t in toks] if "".join(toks).lower() == s.lower() else None

def compress_folds(tokens: list[str]) -> list[str]:
    """Kollapsar F-F ... i slutet → F (solver brukar spara så)."""
    while len(tokens) >= 2 and tokens[-1] == tokens[-2] == 'f':
        tokens.pop()
    return tokens

def to_seq(tokens: list[str]) -> str:
    return "-".join({"r": "R", "f": "F", "c": "C", "x": "X"}[t[0]] for t in tokens)

def like_pattern(seq: str) -> str:
    return "%" if not seq else (seq if seq.endswith("%") else seq + "%").upper()

def pos_variants(pos: str):
    return sorted(POS_SYNONYM.get(pos.upper(), {pos.upper()}))

# ────────────── SQL-hjälp ─────────────────────────────────────

def fetch_freq_and_max(conn, combo, pos, pat, act_token):
    """Hämtar både frequency och max_frequency i en enda query för bättre prestanda."""
    pl = pos_variants(pos)
    ph = ",".join("?" * len(pl))
    
    if act_token.startswith("r"):                   # spelaren 3-bettar
        row = conn.execute(f"""
            SELECT frequency, 
                   (SELECT MAX(frequency) FROM ranges_flat 
                    WHERE position IN ({ph}) AND action_sequence LIKE ? AND combo = ?) as max_freq
            FROM ranges_flat 
            WHERE position IN ({ph}) AND action_sequence LIKE ? AND combo = ? 
            AND action LIKE 'r%' 
            ORDER BY CAST(SUBSTR(action,2) AS REAL) LIMIT 1
        """, (*pl, pat, combo, *pl, pat, combo)).fetchone()
    else:                                           # f / c / x
        row = conn.execute(f"""
            SELECT frequency,
                   (SELECT MAX(frequency) FROM ranges_flat 
                    WHERE position IN ({ph}) AND action_sequence LIKE ? AND combo = ?) as max_freq
            FROM ranges_flat 
            WHERE position IN ({ph}) AND action_sequence LIKE ? AND combo = ? 
            AND action = ?
        """, (*pl, pat, combo, *pl, pat, combo, act_token)).fetchone()
    
    return (row[0], row[1]) if row else (None, None)

# ────────────── Huvudrutin ────────────────────────────────────
def main() -> None:
    # — output-DB ----------------------------------------------
    out = sqlite3.connect(SQLITE["OUT"])
    out.execute("""
        CREATE TABLE IF NOT EXISTS preflop_scores(
            hand_id  TEXT,
            position TEXT,
            player   TEXT,
            combo    TEXT,
            seq      TEXT,
            freq     REAL,
            best     TEXT,
            PRIMARY KEY (hand_id, position)
        );
    """)
    cols = {row[1] for row in out.execute("PRAGMA table_info(preflop_scores)")}
    if "player" not in cols:
        out.execute("ALTER TABLE preflop_scores ADD COLUMN player TEXT;")
    if "best" not in cols:
        out.execute("ALTER TABLE preflop_scores ADD COLUMN best TEXT;")

    done = {row[0] for row in out.execute("SELECT DISTINCT hand_id FROM preflop_scores")}

    # — käll-DB -------------------------------------------------
    hands = sqlite3.connect(SQLITE["HANDS"])
    rng   = sqlite3.connect(SQLITE["RANGES"])
    
    # Skapa optimala index för bättre prestanda
    rng.execute("CREATE INDEX IF NOT EXISTS idx_ranges_combo_pos_seq ON ranges_flat(combo, position, action_sequence)")
    rng.execute("CREATE INDEX IF NOT EXISTS idx_ranges_freq ON ranges_flat(combo, position, action_sequence, frequency)")

    batch = []
    processed_hands = 0

    for (raw_json,) in hands.execute("SELECT raw_json FROM hands"):
        hh = json.loads(raw_json)
        hand_id = hh.get("short_name") or hh.get("stub")
        if hand_id in done or len(hh["positions"]) != 6:
            continue         # redan behandlad eller ej 6-handad

        tokens = tokenize(hh["situation_string"].split("[", 1)[0])
        if tokens is None:
            continue

        actors = [seg.split(":", 2) for seg in hh["breadcrumb"].split(",")]
        # actors[i] = [position, stack, action]
        if len(actors) != len(tokens):
            continue         # inkonsekvent HH

        for idx, (pos, _stack, act_raw) in enumerate(actors):
            history = compress_folds(tokens[:idx].copy())
            seq     = to_seq(history)
            pat     = like_pattern(seq)
            combo   = canonical("".join(hh["positions"][pos]["hole_cards"]))
            player  = hh["positions"][pos]["name"] or ""

            freq, maxf = fetch_freq_and_max(rng, combo, pos, pat, act_raw.lower())

            best = (
                "y" if (freq is not None and maxf is not None and
                        math.isclose(freq, maxf, abs_tol=TOL))
                else ("n" if maxf is not None else None)
            )

            batch.append((hand_id, pos.upper(), player, combo, seq, freq, best))

        processed_hands += 1
        
        # Batch commit var 500:e hand för bättre prestanda
        if len(batch) >= 3000:  # 500 händer × 6 spelare = 3000 rader
            out.executemany(
                "INSERT OR IGNORE INTO preflop_scores "
                "(hand_id, position, player, combo, seq, freq, best) "
                "VALUES (?,?,?,?,?,?,?)",
                batch
            )
            out.commit()
            print(f"✓ {processed_hands:,} händer bearbetade...")
            batch.clear()

    # Commit sista batchen
    if batch:
        out.executemany(
            "INSERT OR IGNORE INTO preflop_scores "
            "(hand_id, position, player, combo, seq, freq, best) "
            "VALUES (?,?,?,?,?,?,?)",
            batch
        )
        out.commit()

    rng.close(); hands.close(); out.close()
    print(f"✅ v1.9 optimerad klar – {processed_hands:,} händer bearbetade med batch-commits.")

# ----------------------------------------------------------------------
if __name__ == "__main__":
    for p in SQLITE.values():
        if not p.exists():
            raise SystemExit(f"❌  saknar {p}")
    main()
