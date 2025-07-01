#!/usr/bin/env python3
"""Materialise small summary tables that the FastAPI layer can query instantly.

▪ dashboard_summary       – one‑row global aggregates
▪ top25_players           – 25 rows mirroring get_top_players_table()
▪ player_summary          – one row per player for /player/{id}/stats & comparison

Run this right after 7_input_scores.py in the ETL chain.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
import sys
import logging

# ---- shared path handling ---------------------------------------------------
# Allow:  python scrape_hh/scripts/8_materialise_dashboard.py  [--db PATH]
ROOT = Path(__file__).resolve().parents[2]  # project root
sys.path.append(str(ROOT))
from utils.paths import HEAVY_DB, IS_RENDER  # noqa

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)8s  %(message)s")

def get_db(path: Path | str | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else HEAVY_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    # Slight pragmas – these tables are tiny so WAL isn't strictly needed
    con.execute("PRAGMA journal_mode=WAL")
    return con

# ---------------------------------------------------------------------------
# Dashboard summary (single row)
DASHBOARD_SQL = """
SELECT 
    COUNT(DISTINCT player_id)                       AS total_players,
    COUNT(DISTINCT hand_id)                         AS total_hands,
    AVG(CASE WHEN action!='f' AND street='preflop' THEN 1 ELSE 0 END)*100  AS avg_vpip,
    AVG(CASE WHEN action='r'  AND street='preflop' THEN 1 ELSE 0 END)*100  AS avg_pfr,
    AVG(j_score)                                    AS avg_j_score,
    COUNT(action_order)                             AS total_actions
FROM actions
WHERE player_id IS NOT NULL AND player_id!='';
"""

# ---------------------------------------------------------------------------
# Top‑25 players  – largely same compute as the API, with score columns present
TOP_PLAYERS_SQL = """
WITH derived AS (
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id)                                   AS hands_played,
        AVG(a.j_score)                                              AS avg_j_score,
        AVG(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1 ELSE 0 END)*100 AS vpip,
        AVG(CASE WHEN a.action='r'  AND a.street='preflop' THEN 1 ELSE 0 END)*100 AS pfr,
        AVG(a.preflop_score)                                        AS avg_preflop_score,
        AVG(a.postflop_score)                                       AS avg_postflop_score,
        AVG(CASE WHEN a.street='preflop' THEN a.j_score END)        AS preflop_j_score,
        AVG(CASE WHEN a.street='flop'   THEN a.j_score END)         AS flop_score,
        AVG(CASE WHEN a.street='turn'   THEN a.j_score END)         AS turn_score,
        AVG(CASE WHEN a.street='river'  THEN a.j_score END)         AS river_score,
        SUM(p.money_won)                                            AS total_winnings,
        AVG(h.big_blind)                                            AS avg_big_blind
    FROM actions a
    LEFT JOIN players   p ON p.hand_id=a.hand_id AND p.position=a.position
    LEFT JOIN hand_info h ON h.hand_id=a.hand_id
    WHERE a.player_id IS NOT NULL AND a.player_id!=''
    GROUP BY a.player_id, a.nickname
    HAVING hands_played>10
)
SELECT *,
       ROUND(CASE WHEN avg_big_blind>0 THEN (total_winnings/avg_big_blind)/hands_played*100 END, 2) AS winrate_bb100
FROM derived
ORDER BY hands_played DESC
LIMIT 25;
"""

# ---------------------------------------------------------------------------
# Player summary – one row / player; mirrors get_player_stats()
PLAYER_SUMMARY_SQL = """
SELECT 
    a.player_id                                                   AS player_id,
    a.nickname                                                    AS nickname,
    COUNT(DISTINCT a.hand_id)                                     AS total_hands,
    COUNT(a.action_order)                                         AS total_actions,
    AVG(a.j_score)                                                AS avg_j_score,
    SUM(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1 ELSE 0 END) AS vpip_cnt,
    SUM(CASE WHEN a.action='r'  AND a.street='preflop' THEN 1 ELSE 0 END) AS pfr_cnt,
    SUM(CASE WHEN a.street='preflop' THEN 1 END)                 AS preflop_actions,
    ROUND(AVG(a.preflop_score),1)                                 AS avg_preflop_score,
    ROUND(AVG(a.postflop_score),1)                                AS avg_postflop_score
FROM actions a
WHERE a.player_id IS NOT NULL AND a.player_id!=''
GROUP BY a.player_id, a.nickname;
"""


TOP_PLAYERS_SQL_FMT = """
SELECT
    a.player_id,
    a.nickname,
    COUNT(DISTINCT a.hand_id)  AS hands_played,
    ROUND(AVG(a.j_score), 1)   AS avg_j_score,
    ROUND(AVG(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1.0 ELSE 0 END)*100,1) AS vpip,
    ROUND(AVG(CASE WHEN a.action='r'  AND a.street='preflop' THEN 1.0 ELSE 0 END)*100,1) AS pfr
FROM   actions a
WHERE  a.player_id IS NOT NULL AND a.player_id!=''
GROUP  BY a.player_id, a.nickname
HAVING hands_played > 10
ORDER  BY hands_played DESC
LIMIT  {limit}
""".strip()

DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_actions_player_street  ON actions(player_id, street);
CREATE INDEX IF NOT EXISTS idx_actions_street_action ON actions(street, action);
CREATE INDEX IF NOT EXISTS idx_actions_player_hand   ON actions(player_id, hand_id);
"""

def rebuild_tables(con: sqlite3.Connection) -> None:
    cur = con.cursor()

    # 1. dashboard_summary ---------------------------------------------------
    cur.executescript("DROP TABLE IF EXISTS dashboard_summary;")
    cur.execute(f"CREATE TABLE dashboard_summary AS {DASHBOARD_SQL}")

    # 2. top25_players -------------------------------------------------------
    cur.executescript("DROP TABLE IF EXISTS top25_players;")
    cur.execute(f"CREATE TABLE top25_players AS {TOP_PLAYERS_SQL_FMT.format(limit=25)}")
    cur.execute("CREATE INDEX idx_top25_player_id ON top25_players(player_id);")

    # 3. player_summary ------------------------------------------------------
    cur.executescript("DROP TABLE IF EXISTS player_summary;")
    cur.execute(f"CREATE TABLE player_summary AS {PLAYER_SUMMARY_SQL}")   # ← add CREATE TABLE
    cur.execute("CREATE INDEX idx_ps_player_id ON player_summary(player_id);")

    cur.executescript(DDL_INDEXES)

    con.commit()

    log.info("✅  Tables materialized.")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Materialise dashboard & player summary tables")
    parser.add_argument("--db", help="Path to heavy_analysis.db (defaults to utils.paths.HEAVY_DB)")
    args = parser.parse_args()

    con = get_db(args.db)
    try:
        rebuild_tables(con)
    finally:
        con.close()
