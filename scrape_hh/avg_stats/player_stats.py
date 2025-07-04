#!/usr/bin/env python3
"""
player_stats.py – detaljerad spelar-statistik från heavy_analysis.db och poker.db
===============================================================================

Den här versionen fokuserar på att filtrera på specifika actions, t.ex. "checkraise", 
och beräkna medelvärdet för `action_score` för dessa specifika situationer, 
samt segmentera för "flop"-street. Skriptet visar också handhistorik från poker.db 
och beräknar ett genomsnitt för dessa förhållanden.

Flaggor:
--------
--action-label    : Filtrera på specifik action-label, t.ex. 'checkraise'.
--street          : Segmentera för en specifik street, t.ex. 'flop'.
--top              : Visa topp N spelare efter sortering
--min-hands        : Minsta antal händer per spelare
--j-score-min      : Minsta j_score för att inkludera en spelare
--csv              : Exportera till CSV
"""

import argparse
import sqlite3
import sys
from pathlib import Path
import pandas as pd
import json

# ── 1. CLI ───────────────────────────────────────────────────────
ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--db", help="Sökväg till heavy_analysis.db")
ap.add_argument("--street", choices=["all", "preflop", "flop", "turn", "river"], default="flop")
ap.add_argument("--action-label", help="Filtrera på specifik action-label, t.ex. 'checkraise'")
ap.add_argument("--min-hands", type=int, default=1, metavar="N", help="Minsta antal händer per spelare (default 1)")
ap.add_argument("--top", type=int, metavar="N", help="Visa endast topp N spelare efter sortering")
ap.add_argument("--j-score-min", type=float, default=55, help="Minsta j_score för att inkludera en spelare")
ap.add_argument("--sort", default="avg_action_score", help="Kolumn att sortera på (default 'avg_action_score')")
ap.add_argument("--csv", metavar="FIL", help="Spara resultatet som CSV")
ap.add_argument("--quiet", action="store_true")
ap.add_argument("-h", "--help", action="help", help="Visa denna hjälptext och avsluta")
args = ap.parse_args()


def dbg(msg: str) -> None:
    if not args.quiet:
        print(msg, file=sys.stderr)


# ── 2. Hitta databaserna genom att söka i projektstrukturen ─────
def locate_db(start: Path) -> Path:
    cur = start
    while True:
        for cand in (cur / "heavy_analysis.db", cur / "local_data" / "database" / "heavy_analysis.db"):
            if cand.is_file():
                return cand
        if cur == cur.parent:
            return None
        cur = cur.parent


def locate_poker_db(start: Path) -> Path:
    cur = start
    while True:
        for cand in (cur / "local_data" / "database" / "poker.db",):
            if cand.is_file():
                return cand
        if cur == cur.parent:
            return None
        cur = cur.parent


# Hitta både heavy_analysis.db och poker.db
DB_PATH = Path(args.db).expanduser().resolve() if args.db else locate_db(Path.cwd())
POKER_DB_PATH = locate_poker_db(Path.cwd())

if not DB_PATH or not DB_PATH.is_file():
    sys.exit("❌ Hittar ingen heavy_analysis.db – placera skriptet nära databasen eller ange --db.")

if not POKER_DB_PATH or not POKER_DB_PATH.is_file():
    sys.exit(f"❌ Hittar ingen poker.db i {POKER_DB_PATH} – kontrollera att filen finns där.")

dbg(f"Öppnar DB-filerna: {DB_PATH} och {POKER_DB_PATH}")

# ── 3. Läs rådata från heavy_analysis.db ─────────────────────────
COLS = [
    "hand_id", "action_order", "street", "position", "player_id", "nickname",
    "action", "amount_to", "stack_before", "stack_after", "invested_this_action", 
    "pot_before", "pot_after", "players_left", "is_allin", "action_score", 
    "state_prefix", "board_cards", "holecards", "size_frac", "size_cat", 
    "action_label", "ip_status", "j_score", "intention"
]
con = sqlite3.connect(DB_PATH)
df_actions = pd.read_sql_query(f"SELECT {', '.join(COLS)} FROM actions", con)
con.close()

# ── 4. Filtrera för street (flop) och action_label (checkraise) ─
if args.street != "all":
    df_actions = df_actions[df_actions.street == args.street]
    if df_actions.empty:
        sys.exit(f"❌ Inga rader för street='{args.street}'.")

if args.action_label:
    df_actions = df_actions[df_actions.action_label == args.action_label]
    if df_actions.empty:
        sys.exit(f"❌ Inga rader med action_label='{args.action_label}'.")

# ── 5. Filtrera spelare med j_score > 55 ────────────────────────
df_actions = df_actions[df_actions.j_score >= args.j_score_min]

# ── 6. Läs handhistorik från poker.db ─────────────────────────────
con = sqlite3.connect(POKER_DB_PATH)
df_hand_meta = pd.read_sql_query("SELECT id, raw_json FROM hands", con)
con.close()

# ── 7. Koppla ihop actions och handhistorik ─────────────────────
df_actions = df_actions.merge(df_hand_meta, left_on="hand_id", right_on="id", how="left")

# ── 8. Extrahera spelardata från raw_json ───────────────────────
def extract_player_info(raw_json):
    try:
        data = json.loads(raw_json)
        positions = data.get('positions', {})
        player_info = []
        for position, details in positions.items():
            player_info.append({
                'position': position,
                'nickname': details['name'],
                'hole_cards': details['hole_cards'],
                'stack': details['stack'],
                'avg_score': details.get('all_time_avg_score', 'N/A')
            })
        return player_info
    except json.JSONDecodeError:
        return []

df_actions['player_info'] = df_actions['raw_json'].apply(extract_player_info)

# ── 9. Beräkna genomsnittligt action_score för de valda situationerna ───────────────────
agg_stats = df_actions.groupby(["player_id", "nickname"]).agg(
    total_hands=("hand_id", "nunique"),
    avg_action_score=("action_score", "mean"),
    hand_history_names=("hand_id", lambda x: ', '.join(x.unique())),  # Visa upp till 10 unika handhistoriknamn
).reset_index()

# ── 10. Filtrera på minsta antal händer ─────────────────────────
agg_stats = agg_stats[agg_stats.total_hands >= args.min_hands]

# ── 11. Sortering & topp-N ───────────────────────────────────────
agg_stats = agg_stats.sort_values(by=args.sort, ascending=False)

if args.top:
    agg_stats = agg_stats.head(args.top)

# ── 12. Export / utskrift ───────────────────────────────────────
header = f"""
── Spelar-statistik för '{args.action_label}' på {args.street} ────────────────────────────────
Databas   : {DB_PATH.name} och {POKER_DB_PATH.name}
Street    : {args.street}
Sortering : {args.sort}
Min händer: {args.min_hands}
-------------------------------------------------------------------------------
"""

fmt_int = "{:,}".format
fmt_flt = lambda x: f"{x:.3f}" if pd.notna(x) else "n/a"

if args.csv:
    out = Path(args.csv).expanduser().resolve()
    agg_stats.to_csv(out, index=False)
    print(f"💾 CSV sparad: {out}")
else:
    print(header)
    print(
        agg_stats.to_string(
            index=False,
            formatters={
                "total_hands": fmt_int,
                "avg_action_score": fmt_flt,
                "hand_history_names": lambda x: x[:10],  # Visa upp till 10 handhistoriknamn
            },
            max_colwidth=18,
        )
    )
