#!/usr/bin/env python3
"""
optimize_indexes.py - Skapar optimerade index för snabbare processing

Kör detta script efter att databaser är skapade men innan processing scripts körs.
Detta kommer dramatiskt förbättra prestandan för scripts 1-8.
"""

import sqlite3
from pathlib import Path
import sys
import time

# Import paths
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.paths import POKER_DB, HEAVY_DB

def create_indexes(db_path: Path, indexes: dict):
    """Skapar index på given databas."""
    print(f"\n🔧 Optimerar {db_path.name}...")
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    # Prestanda-pragma: bättre paralellism och snabba temporära tabeller
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA temp_store=MEMORY;")
    # Öka cache-storlek (negativt värde = KB, dvs 64 MB här)
    cur.execute("PRAGMA cache_size = -65536;")
    
    for index_name, index_sql in indexes.items():
        try:
            start = time.time()
            cur.execute(index_sql)
            elapsed = time.time() - start
            print(f"   ✅ {index_name} ({elapsed:.1f}s)")
        except sqlite3.OperationalError as e:
            if "already exists" in str(e):
                print(f"   ⏭️  {index_name} (finns redan)")
            else:
                print(f"   ❌ {index_name}: {e}")
    
    con.commit()
    # Låt SQLite analysera indexstatistiken direkt
    cur.execute("ANALYZE;")
    con.close()

def main():
    # Index för poker.db
    poker_indexes = {
        "idx_hands_id": "CREATE INDEX IF NOT EXISTS idx_hands_id ON hands(id)",
        "idx_hands_date": "CREATE INDEX IF NOT EXISTS idx_hands_date ON hands(hand_date)",
        "idx_hand_meta_id": "CREATE INDEX IF NOT EXISTS idx_hand_meta_id ON hand_meta(id)",
        "idx_hand_meta_date": "CREATE INDEX IF NOT EXISTS idx_hand_meta_date ON hand_meta(hand_date)",
        "idx_hand_meta_game_type": "CREATE INDEX IF NOT EXISTS idx_hand_meta_game_type ON hand_meta(is_cash, is_mtt)",
        "idx_partial_scores_id": "CREATE INDEX IF NOT EXISTS idx_partial_scores_id ON partial_scores(id)",
    }
    
    # Index för heavy_analysis.db
    heavy_indexes = {
        # För script 1 (build_heavy_analysis)
        "idx_hand_info_id": "CREATE INDEX IF NOT EXISTS idx_hand_info_id ON hand_info(hand_id)",
        "idx_hand_info_date": "CREATE INDEX IF NOT EXISTS idx_hand_info_date ON hand_info(hand_date)",
        
        # För script 2-6 (preflop/postflop scores, action labels etc)
        "idx_actions_player_id": "CREATE INDEX IF NOT EXISTS idx_actions_player_id ON actions(player_id)",
        "idx_actions_street": "CREATE INDEX IF NOT EXISTS idx_actions_street ON actions(street)",
        "idx_actions_position": "CREATE INDEX IF NOT EXISTS idx_actions_position ON actions(position)",
        "idx_actions_state_prefix": "CREATE INDEX IF NOT EXISTS idx_actions_state_prefix ON actions(state_prefix)",
        "idx_actions_composite": "CREATE INDEX IF NOT EXISTS idx_actions_composite ON actions(hand_id, position, street)",
        
        # För script 7 (input_scores) - KRITISKA för prestanda
        "idx_preflop_scores_lookup": "CREATE INDEX IF NOT EXISTS idx_preflop_scores_lookup ON preflop_scores(hand_id, position)",
        "idx_postflop_scores_lookup": "CREATE INDEX IF NOT EXISTS idx_postflop_scores_lookup ON postflop_scores(hand_id, node_string)",
        "idx_actions_scores": "CREATE INDEX IF NOT EXISTS idx_actions_scores ON actions(preflop_score, postflop_score)",
        
        # För script 8 (materialise_dashboard)
        "idx_actions_for_stats": "CREATE INDEX IF NOT EXISTS idx_actions_for_stats ON actions(player_id, street, action)",
        "idx_players_lookup": "CREATE INDEX IF NOT EXISTS idx_players_lookup ON players(hand_id, position)",
        
        # För hand_meta joins
        "idx_hand_meta_heavy": "CREATE INDEX IF NOT EXISTS idx_hand_meta_heavy ON hand_meta(id, is_cash, is_mtt)",
    }
    
    # Skapa index
    if POKER_DB.exists():
        create_indexes(POKER_DB, poker_indexes)
    else:
        print(f"⚠️  {POKER_DB} finns inte än")
    
    if HEAVY_DB.exists():
        create_indexes(HEAVY_DB, heavy_indexes)
    else:
        print(f"⚠️  {HEAVY_DB} finns inte än")
    
    print("\n✅ Index-optimering klar!")
    print("💡 Tips: Kör detta script innan processing scripts för bästa prestanda")

if __name__ == "__main__":
    main() 