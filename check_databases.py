#!/usr/bin/env python3
"""
Kontrollerar status på databaserna
"""
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import POKER_DB, HEAVY_DB, IS_RENDER

def check_db_status(db_path: Path, db_name: str):
    print(f"\n📊 {db_name}:")
    print(f"   Path: {db_path}")
    
    if not db_path.exists():
        print(f"   ❌ Finns inte!")
        return
    
    size_mb = db_path.stat().st_size / (1024 * 1024)
    print(f"   ✅ Storlek: {size_mb:.1f} MB")
    
    try:
        con = sqlite3.connect(db_path)
        
        # Kolla tabeller
        tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"   📋 Tabeller: {len(tables)}")
        
        if db_name == "poker.db":
            # Kolla antal händer
            try:
                count = con.execute("SELECT COUNT(*) FROM hands").fetchone()[0]
                print(f"   🎲 Antal händer: {count:,}")
                
                # Senaste hand
                latest = con.execute("SELECT hand_date FROM hands ORDER BY hand_date DESC LIMIT 1").fetchone()
                if latest:
                    print(f"   📅 Senaste datum: {latest[0]}")
            except:
                print(f"   ⚠️  Kunde inte läsa hands-tabellen")
                
        elif db_name == "heavy_analysis.db":
            # Kolla antal händer i hand_info
            try:
                count = con.execute("SELECT COUNT(*) FROM hand_info").fetchone()[0]
                print(f"   🎲 Antal processade händer: {count:,}")
                
                # Kolla antal actions
                action_count = con.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
                print(f"   🎯 Antal actions: {action_count:,}")
                
                # Senaste hand
                latest = con.execute("SELECT hand_date FROM hand_info ORDER BY hand_date DESC LIMIT 1").fetchone()
                if latest:
                    print(f"   📅 Senaste datum: {latest[0]}")
            except Exception as e:
                print(f"   ⚠️  Kunde inte läsa tabellerna: {e}")
        
        con.close()
        
    except Exception as e:
        print(f"   ❌ Fel vid anslutning: {e}")

def main():
    print("🔍 Kontrollerar databaser...")
    print(f"🌍 Miljö: {'Render.com' if IS_RENDER else 'Lokal utveckling'}")
    print(f"🕐 Tid: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    check_db_status(POKER_DB, "poker.db")
    check_db_status(HEAVY_DB, "heavy_analysis.db")
    
    print("\n✅ Klar!")

if __name__ == "__main__":
    main() 