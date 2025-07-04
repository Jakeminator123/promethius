#!/usr/bin/env python3
"""Debug-script för att undersöka en specifik hand i databaserna"""

import sqlite3
import json
import sys
from pathlib import Path

# Import paths
sys.path.append(str(Path(__file__).resolve().parents[2]))
from utils.paths import POKER_DB, HEAVY_DB

def debug_hand(hand_id: str):
    print(f"\n🔍 Undersöker hand: {hand_id}\n")
    
    # Kolla poker.db
    if POKER_DB.exists():
        con = sqlite3.connect(POKER_DB)
        con.row_factory = sqlite3.Row
        
        # Hämta raw JSON
        row = con.execute("SELECT * FROM hands WHERE id = ?", (hand_id,)).fetchone()
        if row:
            print("📊 I poker.db:")
            hand = json.loads(row['raw_json'])
            print(f"   chip_value: {hand.get('chip_value_in_displayed_currency')}")
            print(f"   situation_string: {hand.get('situation_string')}")
            print(f"   big_blind: {hand.get('big_blind_amount')}")
            
            # Kolla partial_scores
            ps_row = con.execute("SELECT json FROM partial_scores WHERE id = ?", (hand_id,)).fetchone()
            if ps_row:
                ps = json.loads(ps_row['json'])
                print(f"\n   partial_scores noder:")
                for node in list(ps.keys())[:5]:  # Visa första 5
                    print(f"      {node}")
                if len(ps) > 5:
                    print(f"      ... och {len(ps)-5} till")
        else:
            print("   ❌ Hittades inte i poker.db")
        
        con.close()
    
    # Kolla heavy_analysis.db
    if HEAVY_DB.exists():
        con = sqlite3.connect(HEAVY_DB)
        con.row_factory = sqlite3.Row
        
        # Kolla hand_info
        info = con.execute("SELECT * FROM hand_info WHERE hand_id = ?", (hand_id,)).fetchone()
        if info:
            print(f"\n📊 I heavy_analysis.db:")
            print(f"   big_blind: {info['big_blind']}")
            
            # Kolla några actions
            actions = con.execute("""
                SELECT action_order, state_prefix, action, amount_to 
                FROM actions 
                WHERE hand_id = ? 
                LIMIT 5
            """, (hand_id,)).fetchall()
            
            print(f"\n   Första actions:")
            for a in actions:
                print(f"      {a['state_prefix']}{a['action']}{a['amount_to'] if a['action']=='r' else ''}")
        
        con.close()

if __name__ == "__main__":
    hand_id = sys.argv[1] if len(sys.argv) > 1 else "Hand251059665"
    debug_hand(hand_id) 