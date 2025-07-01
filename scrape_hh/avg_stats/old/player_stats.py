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
ap.add_argument("--street",
                choices=["all", "preflop", "flop", "turn", "river"],
                default="preflop")
ap.add_argument("--min-hands", type=int, default=1, metavar="N",
                help="Minsta antal händer per spelare (default 1)")
ap.add_argument("--top", type=int, metavar="N",
                help="Visa endast topp N spelare efter sortering")
ap.add_argument("--sort", default="vpip_pct",
                help="Kolumn att sortera på (default vpip_pct)")
ap.add_argument("--asc", action="store_true",
                help="Sortera stigande i stället för fallande")
ap.add_argument("--player", nargs="*",
                help="En eller flera player_id eller nick att inkludera")
ap.add_argument("--csv", metavar="FIL",
                help="Spara resultatet som CSV")
ap.add_argument("--quiet", action="store_true")
ap.add_argument("-h", "--help", action="help",
                help="Visa denna hjälptext och avsluta")
args = ap.parse_args()


def dbg(msg: str) -> None:
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
    sys.exit("❌ Hittar ingen heavy_analysis.db – placera skriptet nära databasen "
             "eller ange --db.")

dbg(f"Öppnar DB-filen: {DB_PATH}")

# ── 3. Läs rådata ───────────────────────────────────────────────
COLS = [
    "hand_id",
    "player_id",
    "nickname",
    "street",
    "action",
    "invested_this_action",
    "action_score",
    "decision_difficulty",
]
con = sqlite3.connect(DB_PATH)
df = pd.read_sql_query(f"SELECT {', '.join(COLS)} FROM actions", con)
con.close()

# ── 4. Street-filter ────────────────────────────────────────────
if args.street != "all":
    df = df[df.street == args.street]
    if df.empty:
        sys.exit(f"❌ Inga rader för street='{args.street}'.")

# ── 5. Filtrera spelare (om angivet) ────────────────────────────
if args.player:
    df = df[df.player_id.isin(args.player) | df.nickname.isin(args.player)]
    if df.empty:
        sys.exit("❌ Inga matchande spelare efter filter.")

# ── 6. Beräkna metrics ─────────────────────────────────────────
def agg_metrics(g: pd.DataFrame) -> dict:
    hands_total = g.hand_id.nunique()

    # VPIP/PFR definieras bara för preflop
    if args.street == "preflop":
        invested = g[g.invested_this_action > 0]
        vpip_hands = invested.hand_id.nunique()
        pfr_hands = g[g.action == "r"].hand_id.nunique()
    else:
        vpip_hands = pfr_hands = None

    return {
        "hands_total": hands_total,
        "vpip_hands": vpip_hands,
        "pfr_hands": pfr_hands,
        "vpip_pct": (vpip_hands / hands_total) if vpip_hands else None,
        "pfr_pct": (pfr_hands / hands_total) if pfr_hands else None,
        "avg_action_score": g.action_score.mean(),
        "avg_decision_diff": g.decision_difficulty.mean(),
    }


summary = (
    df.groupby(["player_id", "nickname"], sort=False)
      .apply(agg_metrics)
      .apply(pd.Series)
      .reset_index()
)

# ── 7. Filtrera på min-hands ───────────────────────────────────
summary = summary[summary.hands_total >= args.min_hands]

# ── 8. Sortering & topp-N ───────────────────────────────────────
sort_col = args.sort
if sort_col not in summary.columns:
    sys.exit("❌ Ogiltig --sort='{0}'. Välj en av: {1}"
             .format(sort_col, ", ".join(summary.columns)))

summary = summary.sort_values(sort_col,
                              ascending=args.asc,
                              na_position="last")

if args.top:
    summary = summary.head(args.top)

# ── 9. Export / utskrift ───────────────────────────────────────
header = textwrap.dedent(f"""
    ── SPELAR-STATISTIK ────────────────────────────────────────────────────────────────
    Databas   : {DB_PATH.name}
    Street    : {args.street}
    Sortering : {sort_col} ({'stigande' if args.asc else 'fallande'})
    Min händer: {args.min_hands}
    -----------------------------------------------------------------------------
""")

fmt_int = "{:,}".format
fmt_pct = lambda x: f"{x:.1%}" if pd.notna(x) else "n/a"
fmt_flt = lambda x: f"{x:.3f}" if pd.notna(x) else "n/a"

if args.csv:
    out = Path(args.csv).expanduser().resolve()
    summary.to_csv(out, index=False)
    print(f"💾 CSV sparad: {out}")
else:
    print(header)
    print(
        summary.to_string(
            index=False,
            formatters={
                "hands_total": fmt_int,
                "vpip_hands": fmt_int,
                "pfr_hands": fmt_int,
                "vpip_pct": fmt_pct,
                "pfr_pct": fmt_pct,
                "avg_action_score": fmt_flt,
                "avg_decision_diff": fmt_flt,
            },
            max_colwidth=18,
        )
    )
