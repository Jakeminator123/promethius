#!/usr/bin/env python3
"""
actions_by_position.py – actions vs. opportunities (max 2 000 händer/grupp)
===========================================================================

**Vad är nytt?**
• Räknar nu **opportunities** via kolumnerna `can_r`, `can_c`, `can_x`, `can_f` om de finns.
• Visar – per street & position – _utförda_, _möjliga_ och _andel (%)_ för
  raise (r), call (c), check (x) och fold (f).
• Om någon `can_*`-kolumn saknas antas opportunities = rows_considered.
• `--max-rows` begränsar analyserade händer (default 2 000).
• Resultat kan skrivas som tabell eller CSV.

Exempel
```
# Standard (alla streets, max 2 000 händer/grupp)
python actions_by_position.py

# Bara flop, högst 500 händer/grupp, spara till CSV
python actions_by_position.py --street flop --max-rows 500 --csv flop_stats.csv
```
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional, Dict

import pandas as pd
import textwrap

# ── 1. CLI ───────────────────────────────────────────────────────
ap = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
ap.add_argument("--db", help="Sökväg till heavy_analysis.db (valfritt – scriptet försöker hitta den automatiskt)")
ap.add_argument("--street", choices=["all", "preflop", "flop", "turn", "river"], default="all", help="Filtrera på specifik street (default: all)")
ap.add_argument("--max-rows", type=int, default=2000, help="Max antal rader som tas med per street/position (default: 2000)")
ap.add_argument("--csv", metavar="FIL", help="Spara resultatet som CSV i stället för att skriva tabell till skärmen")
ap.add_argument("--quiet", action="store_true", help="Dölj debug‑utskrifter")
args = ap.parse_args()

MAX_ROWS = max(1, args.max_rows)


def dbg(msg: str):
    if not args.quiet:
        print(msg, file=sys.stderr)

# ── 2. Hitta DB-filen om --db saknas ────────────────────────────

def locate_db(start: Path) -> Optional[Path]:
    cur = start
    while True:
        for cand in (cur / "heavy_analysis.db", cur / "local_data" / "database" / "heavy_analysis.db"):
            if cand.is_file():
                return cand
        if cur == cur.parent:
            return None
        cur = cur.parent

DB_PATH = Path(args.db).expanduser().resolve() if args.db else locate_db(Path.cwd())
if not DB_PATH or not DB_PATH.is_file():
    sys.exit("❌ Hittar ingen heavy_analysis.db – ange --db eller placera scriptet nära databasen.")

dbg(f"Öppnar DB-filen: {DB_PATH}")

# ── 3. Kolla vilka kolumner som finns ───────────────────────────
con = sqlite3.connect(DB_PATH)
cur = con.cursor()
cols = {row[1] for row in cur.execute("PRAGMA table_info(actions)")}

can_cols: Dict[str, str] = {act: f"can_{act}" for act in ("r", "c", "x", "f") if f"can_{act}" in cols}
missing_can = {act for act in ("r", "c", "x", "f") if act not in can_cols}

# Bygg SELECT‑lista dynamiskt
select_cols = ["street", "position", "action", "action_score", "decision_difficulty"] + list(can_cols.values())
query = f"SELECT {', '.join(select_cols)} FROM actions"

df = pd.read_sql_query(query, con)
con.close()

# ── 4. Filtrera på street om begärt ─────────────────────────────
if args.street != "all":
    df = df[df.street == args.street]
    if df.empty:
        sys.exit(f"❌ Inga rader för street='{args.street}'.")

# ── 5. Begränsa till max_rows per street/position ──────────────
limited: List[pd.DataFrame] = []
for (street, position), grp in df.groupby(["street", "position"], sort=False):
    limited.append(grp.head(MAX_ROWS))

df_lim = pd.concat(limited, ignore_index=True) if limited else pd.DataFrame(columns=df.columns)
if df_lim.empty:
    sys.exit("❌ Inga rader kvar efter begränsning.")

# ── 6. Grupp & aggregering ─────────────────────────────────────
rows = []
for (street, position), grp in df_lim.groupby(["street", "position"]):
    total = len(grp)
    performed = grp["action"].value_counts()

    def perf(act: str) -> int:
        return int(performed.get(act, 0))

    def opp(act: str) -> int:
        if act in can_cols:
            return int(grp[can_cols[act]].sum())
        # Om can_* saknas: varje rad räknas som möjlighet
        return total

    def pct(act: str) -> Optional[float]:
        o = opp(act)
        return perf(act) / o if o else None

    rows.append(
        dict(
            street=street,
            position=position,
            rows_considered=total,
            r_performed=perf("r"),
            r_opp=opp("r"),
            r_pct=pct("r"),
            c_performed=perf("c"),
            c_opp=opp("c"),
            c_pct=pct("c"),
            x_performed=perf("x"),
            x_opp=opp("x"),
            x_pct=pct("x"),
            f_performed=perf("f"),
            f_opp=opp("f"),
            f_pct=pct("f"),
            avg_score=grp["action_score"].mean(),
            avg_difficulty=grp["decision_difficulty"].mean(),
        )
    )

summary_df = pd.DataFrame(rows).sort_values(["street", "position"], key=lambda s: s.str.upper()).reset_index(drop=True)

# ── 7. Utskrift / export ───────────────────────────────────────
fmt_int = "{:,}".format
fmt_pct = lambda x: f"{x:.1%}" if x is not None else "n/a"
fmt_flt = lambda x: f"{x:.3f}" if pd.notna(x) else "n/a"

header = textwrap.dedent(
    f"""
    ── Actions vs. Opportunities per street & position ─────────────────────────
    Databas   : {DB_PATH.name}
    Street    : {args.street}
    Max‑rader : {MAX_ROWS} per street/position
    {'OBS! can_*‑kolumner saknas för ' + ', '.join(sorted(missing_can)) if missing_can else ''}
    ---------------------------------------------------------------------------
    """
)

if args.csv:
    csv_path = Path(args.csv).expanduser().resolve()
    summary_df.to_csv(csv_path, index=False)
    print(f"💾 CSV sparad: {csv_path}")
else:
    print("\n" + header)
    print(
        summary_df.to_string(
            index=False,
            formatters={
                "rows_considered": fmt_int,
                "r_performed": fmt_int,
                "r_opp": fmt_int,
                "r_pct": fmt_pct,
                "c_performed": fmt_int,
                "c_opp": fmt_int,
                "c_pct": fmt_pct,
                "x_performed": fmt_int,
                "x_opp": fmt_int,
                "x_pct": fmt_pct,
                "f_performed": fmt_int,
                "f_opp": fmt_int,
                "f_pct": fmt_pct,
                "avg_score": fmt_flt,
                "avg_difficulty": fmt_flt,
            },
            max_colwidth=20,
        )
    )