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
    ROUND(SUM(CASE WHEN action!='f' AND street='preflop' THEN 1 ELSE 0 END)*100.0 / 
          NULLIF(SUM(CASE WHEN street='preflop' THEN 1 ELSE 0 END), 0), 1)  AS avg_vpip,
    ROUND(SUM(CASE WHEN action='r' AND street='preflop' THEN 1 ELSE 0 END)*100.0 / 
          NULLIF(SUM(CASE WHEN street='preflop' THEN 1 ELSE 0 END), 0), 1)  AS avg_pfr,
    AVG(j_score)                                    AS avg_j_score,
    COUNT(action_order)                             AS total_actions,
    ROUND(COALESCE(AVG(preflop_score), AVG(CASE WHEN street='preflop' THEN j_score END)), 1)    AS avg_preflop_score,
    ROUND(COALESCE(AVG(postflop_score), AVG(CASE WHEN street!='preflop' THEN j_score END)), 1)  AS avg_postflop_score
FROM actions
WHERE player_id IS NOT NULL AND player_id!='';
"""

# ---------------------------------------------------------------------------
# Top‑25 players  – largely same compute as the API, with score columns present
# NOTE: This is not used anymore, we use TOP_PLAYERS_SQL_FMT instead
TOP_PLAYERS_SQL = """
WITH derived AS (
    SELECT 
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id)                                   AS hands_played,
        AVG(a.j_score)                                              AS avg_j_score,
        ROUND(SUM(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1 ELSE 0 END)*100.0 / 
              NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0), 1) AS vpip,
        ROUND(SUM(CASE WHEN a.action='r' AND a.street='preflop' THEN 1 ELSE 0 END)*100.0 / 
              NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0), 1) AS pfr,
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
    a.player_id,
    a.nickname,
    COUNT(DISTINCT a.hand_id)                           AS hands_played,
    COUNT(a.action_order)                               AS total_actions,
    ROUND(AVG(a.j_score),1)                             AS avg_j_score,
    
    /* VPIP och PFR - räkna korrekt över alla preflop-actions */
    ROUND(
        SUM(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0)
    ,1) AS vpip,
    
    ROUND(
        SUM(CASE WHEN a.action='r' AND a.street='preflop' THEN 1 ELSE 0 END) * 100.0 /
        NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0)
    ,1) AS pfr,
    
    ROUND(COALESCE(AVG(a.preflop_score), AVG(CASE WHEN a.street='preflop' THEN a.j_score END)),1) AS avg_preflop_score,
    ROUND(COALESCE(AVG(a.postflop_score), AVG(CASE WHEN a.street!='preflop' THEN a.j_score END)),1) AS avg_postflop_score,
    
    /* river calls */
    COUNT(CASE WHEN a.street='river'
                AND a.action_label='call' THEN 1 END)       AS river_calls,
    COUNT(CASE WHEN a.street='river'
                AND a.action_label='call'
                AND p.money_won>0 THEN 1 END)               AS river_calls_won
FROM   actions a
LEFT JOIN players   p ON p.hand_id=a.hand_id AND p.position=a.position
WHERE  a.player_id IS NOT NULL AND a.player_id!=''
GROUP  BY a.player_id, a.nickname;
"""


TOP_PLAYERS_SQL_FMT = """
WITH base AS (
    SELECT
        a.player_id,
        a.nickname,
        COUNT(DISTINCT a.hand_id)                           AS hands_played,
        ROUND(AVG(a.j_score),1)                             AS avg_j_score,
        
        /* VPIP och PFR - räkna korrekt över alla preflop-actions */
        ROUND(
            SUM(CASE WHEN a.action!='f' AND a.street='preflop' THEN 1 ELSE 0 END) * 100.0 /
            NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0)
        ,1) AS vpip,
        
        ROUND(
            SUM(CASE WHEN a.action='r' AND a.street='preflop' THEN 1 ELSE 0 END) * 100.0 /
            NULLIF(SUM(CASE WHEN a.street='preflop' THEN 1 ELSE 0 END), 0)
        ,1) AS pfr,
        
        ROUND(COALESCE(AVG(a.preflop_score), AVG(CASE WHEN a.street='preflop' THEN a.j_score END)),1) AS avg_preflop_score,
        ROUND(COALESCE(AVG(a.postflop_score), AVG(CASE WHEN a.street!='preflop' THEN a.j_score END)),1) AS avg_postflop_score,

        /* needed for win-rate */
        SUM(p.money_won)                                    AS total_winnings,
        AVG(h.big_blind)                                    AS avg_big_blind,

        /* counts for solver precision - removed due to missing column */
        0 AS solver_cnt,
        0 AS solver_yes_cnt,

        /* counts for river calldown accuracy */
        COUNT(CASE WHEN a.street='river'
                    AND a.action_label='call' THEN 1 END)       AS river_calls,
        COUNT(CASE WHEN a.street='river'
                    AND a.action_label='call'
                    AND p.money_won>0 THEN 1 END)               AS river_calls_won
    FROM   actions a
    LEFT JOIN players   p ON p.hand_id=a.hand_id AND p.position=a.position
    LEFT JOIN hand_info h ON h.hand_id=a.hand_id
    WHERE  a.player_id IS NOT NULL AND a.player_id!=''
    GROUP  BY a.player_id, a.nickname
    HAVING COUNT(DISTINCT a.hand_id) > 10
),

/* average raise-size per street + label → for deviance calc */
avg_sizes AS (
    SELECT street, action_label, AVG(size_frac) AS avg_size
    FROM   actions
    WHERE  action='r' AND size_frac IS NOT NULL
    GROUP  BY street, action_label
),

bet_dev AS (
    SELECT
        a.player_id,
        ROUND(AVG(
            ABS(a.size_frac - s.avg_size) / NULLIF(s.avg_size,0) * 100
        ),0) AS bet_deviance
    FROM   actions a
    JOIN   avg_sizes s
           ON s.street=a.street AND s.action_label=a.action_label
    WHERE  a.action='r' AND a.size_frac IS NOT NULL
    GROUP  BY a.player_id
),

tilt AS (
    /* performance drop after a losing hand */
    SELECT player_id,
           ROUND(100 - (
               AVG(CASE WHEN prev_money_won<0  THEN j_score END) /
               NULLIF(AVG(CASE WHEN prev_money_won>=0 THEN j_score END),0)
           )*100,0) AS tilt_factor
    FROM (
        SELECT a.player_id,
               a.j_score,
               LAG(p.money_won) OVER (PARTITION BY a.player_id ORDER BY a.hand_id)
                   AS prev_money_won
        FROM   actions a
        JOIN   players p ON p.hand_id=a.hand_id AND p.position=a.position
    )
    GROUP BY player_id
)

SELECT
    b.player_id,
    b.nickname,
    /* alias so React expects player.total_hands */
    b.hands_played                                   AS total_hands,
    b.avg_j_score,
    b.vpip,
    b.pfr,
    b.avg_preflop_score,
    b.avg_postflop_score,

    /* win-rate BB/100 */
    ROUND(CASE WHEN b.avg_big_blind>0
               THEN (b.total_winnings / b.avg_big_blind) /
                    b.hands_played * 100
          END, 2)                                    AS winrate_bb100,

    /* optional dashboard columns */
    ROUND(CASE WHEN b.solver_cnt>0
               THEN b.solver_yes_cnt*100.0 / b.solver_cnt
          END, 1)                                    AS solver_precision_score,
    ROUND(CASE WHEN b.river_calls>0
               THEN b.river_calls_won*100.0 / b.river_calls
          END, 0)                                    AS calldown_accuracy,
    d.bet_deviance,
    t.tilt_factor

FROM   base      b
LEFT JOIN bet_dev d ON d.player_id = b.player_id
LEFT JOIN tilt    t ON t.player_id = b.player_id
ORDER  BY total_hands DESC
LIMIT  {limit};
""".strip()


DDL_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_actions_player_street  ON actions(player_id, street);
CREATE INDEX IF NOT EXISTS idx_actions_street_action ON actions(street, action);
CREATE INDEX IF NOT EXISTS idx_actions_player_hand   ON actions(player_id, hand_id);
"""

def rebuild_tables(con: sqlite3.Connection) -> None:
    cur = con.cursor()
    
    try:
        # Kontrollera att actions-tabellen finns och har data
        count = cur.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        log.info(f"Found {count} rows in actions table")
        
        # Kontrollera att de nya kolumnerna finns
        cur.execute("PRAGMA table_info(actions)")
        columns = {row[1] for row in cur.fetchall()}
        
        if 'preflop_score' not in columns or 'postflop_score' not in columns:
            log.warning("Missing preflop_score or postflop_score columns in actions table")
            log.warning("Script 7 might not have completed successfully")
            # Fortsätt ändå för att skapa tabellerna med NULL-värden
        
    except Exception as e:
        log.error(f"Error checking actions table: {e}")
        raise

    # 1. dashboard_summary ---------------------------------------------------
    try:
        cur.executescript("DROP TABLE IF EXISTS dashboard_summary;")
        cur.execute(f"CREATE TABLE dashboard_summary AS {DASHBOARD_SQL}")
        log.info("✅ dashboard_summary created")
    except Exception as e:
        log.error(f"Failed to create dashboard_summary: {e}")
        raise

    # 2. top25_players -------------------------------------------------------
    try:
        cur.executescript("DROP TABLE IF EXISTS top25_players;")
        cur.execute(f"CREATE TABLE top25_players AS {TOP_PLAYERS_SQL_FMT.format(limit=25)}")
        cur.execute("CREATE INDEX idx_top25_player_id ON top25_players(player_id);")
        log.info("✅ top25_players created")
    except Exception as e:
        log.error(f"Failed to create top25_players: {e}")
        raise

    # 3. player_summary ------------------------------------------------------
    try:
        cur.executescript("DROP TABLE IF EXISTS player_summary;")
        cur.execute(f"CREATE TABLE player_summary AS {PLAYER_SUMMARY_SQL}")   # ← add CREATE TABLE
        cur.execute("CREATE INDEX idx_ps_player_id ON player_summary(player_id);")
        log.info("✅ player_summary created")
    except Exception as e:
        log.error(f"Failed to create player_summary: {e}")
        raise

    try:
        cur.executescript(DDL_INDEXES)
        con.commit()
        log.info("✅ Tables materialized successfully.")
    except Exception as e:
        log.error(f"Failed to create indexes: {e}")
        raise


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Materialise dashboard & player summary tables")
    parser.add_argument("--db", help="Path to heavy_analysis.db (defaults to utils.paths.HEAVY_DB)")
    args = parser.parse_args()

    try:
        con = get_db(args.db)
        rebuild_tables(con)
    except Exception as e:
        log.error(f"Script failed: {e}")
        sys.exit(1)
    finally:
        if 'con' in locals():
            con.close()
