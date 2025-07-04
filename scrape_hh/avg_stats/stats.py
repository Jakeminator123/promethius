#!/usr/bin/env python3
"""
actions_by_position.py – "håll‑käften"‑översikt av actions vs opportunities
============================================================================

Dubbelklicka på skriptet – det hittar *heavy_analysis.db* i samma (eller
överliggande) mapp, analyserar högst `--max-rows` (default 2000) händer per
street/position, **BERÄKNAR opportunities med pokerlogik** och skriver en fet
terminaltabell (eller CSV med `--csv`).

Pokerregler (heuristik):
────────────────────────
* **Raise (r)** – alltid möjlig.
* **Bet/Kalla**: Vi kollar `state_prefix` (actions före spelaren på gatan)
  * finns *r* eller *b*  → det finns en insats att syna  → *call & fold* möjliga, *check* ej.
  * annars → ingen insats  → *check* möjlig, *call & fold* ej.
* **Pre‑flop Big Blind** utan raise får också *check* (standardregel). 
* *Fold* räknas endast när det finns bet att syna.

Tabellen visar – per street & position – antal *utförda* (performed), *möjliga*
(opportunity), samt procenten (performed / opportunity). 0 möjligheter ⇒ “n/a”.

Exempel:
========
```bash
python actions_by_position.py                       # dubbelklick ger samma
python actions_by_position.py --street flop --max-rows 500
python actions_by_position.py --csv all_stats.csv
```
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd
import textwrap

# ── 1. CLI ───────────────────────────────────────────────────────
ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--db", help="Sökväg till heavy_analysis.db")
ap.add_argument("--street", choices=["all", "preflop", "flop", "turn", "river"], default="all")
ap.add_argument("--max-rows", type=int, default=2000)
ap.add_argument("--csv", metavar="FIL")
ap.add_argument("--quiet", action="store_true")
ap.add_argument("-h", "--help", action="help", help="Visa denna hjälptext och avsluta")
args = ap.parse_args()

MAX_ROWS = max(1, args.max_rows)


def dbg(msg: str):
    if not args.quiet:
        print(msg, file=sys.stderr)

# ── 2. Hitta databasen ──────────────────────────────────────────

def locate_db(start: Path) -> Optional[Path]:
    cur = start
    while True:
        for cand in (
            cur / "heavy_analysis.db",
            cur / "local_data" / "database" / "heavy_analysis.db",
        ):
            if cand.is_file():
                return cand
        if cur == cur.parent:
            return None
        cur = cur.parent

DB_PATH = Path(args.db).expanduser().resolve() if args.db else locate_db(Path.cwd())
if not DB_PATH or not DB_PATH.is_file():
    sys.exit("❌ Hittar ingen heavy_analysis.db – placera skriptet nära databasen eller ange --db.")

dbg(f"Öppnar DB-filen: {DB_PATH}")

# ── 3. Läs rådata ───────────────────────────────────────────────
BASE_COLS = [
    "street",
    "position",
    "action",
    "state_prefix",
    "action_score",
    "decision_difficulty",
]
con = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(f"SELECT {', '.join(BASE_COLS)} FROM actions", con)
con.close()

# ── 4. Street-filter ────────────────────────────────────────────
if args.street != "all":
    df = df[df.street == args.street]
    if df.empty:
        sys.exit(f"❌ Inga rader för street='{args.street}'.")

# ── 5. Begränsa antal händer per grupp ─────────────────────────
parts: List[pd.DataFrame] = []
for (street, position), grp in df.groupby(["street", "position"], sort=False):
    parts.append(grp.head(MAX_ROWS))

df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
if df.empty:
    sys.exit("❌ Inga rader kvar efter begränsning.")

# ── 6. Beräkna opportunities på radnivå ─────────────────────────

def compute_opps(row: pd.Series) -> pd.Series:
    """Returnerar 4 boolar (r,c,x,f) som anger om action var möjlig."""
    prefix = (row.state_prefix or "").lower()
    position = (row.position or "").upper()
    street = (row.street or "").lower()

    bet_to_call = any(ch in prefix for ch in ("r", "b"))

    # raise alltid möjlig
    r_opp = 1

    # call/fold/check enligt regler ovan
    if bet_to_call:
        c_opp = 1
        f_opp = 1
        x_opp = 0
    else:
        # No bet: check allowed; fold/call inte logiskt (förutom kuriosa)
        c_opp = 0
        f_opp = 0
        x_opp = 1

    # Preflop BB utan raise: fold/call ej tillåtna, check ok (hanteras redan)
    # (BB kan i praktiken inte folda sin blind innan bet.)
    if street == "preflop" and position == "BB" and not bet_to_call:
        c_opp = 0  # call är själva blindposten
        f_opp = 0
        x_opp = 1

    return pd.Series({"r_opp": r_opp, "c_opp": c_opp, "x_opp": x_opp, "f_opp": f_opp})

opps_df = df.apply(compute_opps, axis=1)
df = pd.concat([df, opps_df], axis=1)

# ── 7. Aggregera per street & position ─────────────────────────
rows_out = []
for (street, position), grp in df.groupby(["street", "position"]):
    total = len(grp)
    count_perf = grp["action"].value_counts()

    def perf(act: str) -> int:
        return int(count_perf.get(act, 0))

    def opp(act: str) -> int:
        return int(grp[f"{act}_opp"].sum())

    def pct(act: str):
        o = opp(act)
        return perf(act) / o if o else None

    rows_out.append(
        dict(
            street=street,
            position=position,
            rows_considered=total,
            r_perf=perf("r"),
            r_opp=opp("r"),
            r_pct=pct("r"),
            c_perf=perf("c"),
            c_opp=opp("c"),
            c_pct=pct("c"),
            x_perf=perf("x"),
            x_opp=opp("x"),
            x_pct=pct("x"),
            f_perf=perf("f"),
            f_opp=opp("f"),
            f_pct=pct("f"),
            avg_score=grp["action_score"].mean(),
            avg_diff=grp["decision_difficulty"].mean(),
        )
    )

summary = pd.DataFrame(rows_out).sort_values(["street", "position"], key=lambda s: s.str.upper()).reset_index(drop=True)

# ── 8. Skriv resultat ──────────────────────────────────────────
fmt_int = "{:,}".format
fmt_pct = lambda x: f"{x:.1%}" if x is not None else "n/a"
fmt_flt = lambda x: f"{x:.3f}" if pd.notna(x) else "n/a"

header = textwrap.dedent(
    f"""
    ── HÅLL‑KÄFTEN‑TABELL (actions vs. opportunities) ──────────────────────────
    Databas   : {DB_PATH.name}
    Street    : {args.street}
    Max‑rader : {MAX_ROWS} per street/position
    ---------------------------------------------------------------------------
    """
)

if args.csv:
    out = Path(args.csv).expanduser().resolve()
    summary.to_csv(out, index=False)
    print(f"💾 CSV sparad: {out}")
else:
    print("\n" + header)
    print(
        summary.to_string(
            index=False,
            formatters={
                "rows_considered": fmt_int,
                "r_perf": fmt_int,
                "r_opp": fmt_int,
                "r_pct": fmt_pct,
                "c_perf": fmt_int,
                "c_opp": fmt_int,
                "c_pct": fmt_pct,
                "x_perf": fmt_int,
                "x_opp": fmt_int,
                "x_pct": fmt_pct,
                "f_perf": fmt_int,
                "f_opp": fmt_int,
                "f_pct": fmt_pct,
                "avg_score": fmt_flt,
                "avg_diff": fmt_flt,
            },
            max_colwidth=18,
        )
    )
