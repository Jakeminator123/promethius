#!/usr/bin/env python3
"""
actions_by_position.py – summerar spelarnas beslut (r, c, x, f)
---------------------------------------------------------------

Ger en snabb översikt av hur ofta spelare tar olika beslut beroende på *street* och
*position* i tabellen **actions**.

Utskriften visar – för varje street‑/positions‑kombination –
  • totalt antal rader (actions)
  • andel (%) raise, call, check, fold
  • medelvärde av action_score & decision_difficulty

Exempel:
    $ python actions_by_position.py  # letar upp heavy_analysis.db automatiskt
    $ python actions_by_position.py --db /path/to/heavy_analysis.db --street preflop

Outputen är en tabell till STDOUT.  Du kan vidare dirigera den till CSV med
flaggan --csv, eller välja ALLA streets, eller filtrera på en enda.
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
ap = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
ap.add_argument(
    "--db",
    help="Sökväg till heavy_analysis.db (valfritt – scriptet försöker hitta den automatiskt)",
)
ap.add_argument(
    "--street",
    choices=["all", "preflop", "flop", "turn", "river"],
    default="all",
    help="Filtrera på specifik street (default: all)",
)
ap.add_argument(
    "--csv",
    metavar="FIL",
    help="Spara resultatet som CSV i stället för att skriva tabell till skärmen",
)
ap.add_argument("--quiet", action="store_true", help="Dölj debug‑utskrifter")
args = ap.parse_args()

def dbg(msg: str):
    if not args.quiet:
        print(msg, file=sys.stderr)

# ── 2. Hitta DB‑filen om --db saknas ────────────────────────────

def locate_db(start: Path) -> Optional[Path]:
    """Navigerar uppåt i filsystemet tills en heavy_analysis.db hittas."""
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


# absolut sökväg om args.db anges, annars heuristik
DB_PATH = (
    Path(args.db).expanduser().resolve()
    if args.db
    else locate_db(Path.cwd())
)
if not DB_PATH or not DB_PATH.is_file():
    sys.exit("❌ Hittar ingen heavy_analysis.db – ange --db eller placera scriptet nära databasen.")

dbg(f"Öppnar DB‑filen: {DB_PATH}")

# ── 3. Läs in data till pandas ──────────────────────────────────
con = sqlite3.connect(DB_PATH)
query = "SELECT street, position, action, action_score, decision_difficulty FROM actions"
df = pd.read_sql_query(query, con)
con.close()

# ── 4. Filtrera på street om begärt ─────────────────────────────
if args.street != "all":
    df = df[df.street == args.street]
    if df.empty:
        sys.exit(f"❌ Inga rader för street='{args.street}'.")

# ── 5. Grupp & aggregering ─────────────────────────────────────

group_cols: List[str] = ["street", "position"]
summary_rows: List[dict] = []

for (street, position), grp in df.groupby(group_cols):
    total = len(grp)
    vc = grp["action"].value_counts()

    def pct(act: str) -> float:
        return vc.get(act, 0) / total if total else 0.0

    summary_rows.append(
        dict(
            street=street,
            position=position,
            actions=total,
            r_pct=pct("r"),
            c_pct=pct("c"),
            x_pct=pct("x"),
            f_pct=pct("f"),
            avg_score=grp["action_score"].mean(),
            avg_difficulty=grp["decision_difficulty"].mean(),
        )
    )

summary_df = (
    pd.DataFrame(summary_rows)
    .sort_values(["street", "position"], key=lambda s: s.str.upper())
    .reset_index(drop=True)
)

# ── 6. Utskrift / export ───────────────────────────────────────
precision = 3

if args.csv:
    csv_path = Path(args.csv).expanduser().resolve()
    summary_df.to_csv(csv_path, index=False)
    print(f"💾 CSV sparad: {csv_path}")
else:
    # Snygga formatterare för kolumnerna
    fmt = {
        "actions": "{:,}".format,
        "r_pct": "{:.1%}".format,
        "c_pct": "{:.1%}".format,
        "x_pct": "{:.1%}".format,
        "f_pct": "{:.1%}".format,
        "avg_score": lambda x: f"{x:.{precision}f}" if pd.notna(x) else "n/a",
        "avg_difficulty": lambda x: f"{x:.{precision}f}" if pd.notna(x) else "n/a",
    }

    heading = textwrap.dedent(
        f"""
        ── Action‑fördelning per street & position ──────────────────────────────
        Databas  : {DB_PATH.name}
        Street   : {args.street}
        -----------------------------------------------------------------------
        """
    )
    print("\n" + heading)
    print(summary_df.to_string(index=False, formatters=fmt))

