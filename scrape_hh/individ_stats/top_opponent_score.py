#!/usr/bin/env python3
# top_opponent_score.py
#
# Skript som:
# 1. Läser rådata från poker.db (hand_players).
# 2. Beräknar för varje spelare:
#    • Totalt antal händer (antal unika hand_id i hand_players).
#    • Antal gemensamma händer med varje annan spelare.
#    • Hittar motståndaren med flest gemensamma händer och beräknar procentandel.
# 3. Skriver in resultaten i heavy_analysis.db i tabellen player_top_opponent.
#
# Körning:  
#   python -m database.heavy_calc_db.scripts.top_opponent_score --source poker.db --output heavy_analysis.db
#   python top_opponent_score.py --source poker.db --output heavy_analysis.db

import sqlite3
import sys
import argparse
import time
import gc
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Iterator

# Import database helper med robust felhantering
try:
    from . import db_io  # Relativ import when run as module
except ImportError:
    try:
        from database.heavy_calc_db.scripts import db_io  # Absolut import från projekt-rot
    except ImportError:
        try:
            import db_io  # Direkt import om vi kör från scripts-mappen
        except ImportError:
            print("❌ Could not import db_io. Make sure you're running from the correct directory.")
            sys.exit(1)

# 🆕 Konfigurera chunking för att undvika minnesöverbelastning
CHUNK_SIZE = 50000  # Bearbeta 50k rader åt gången
BATCH_SIZE = 1000   # Skriv 1000 spelare åt gången till databasen
PROGRESS_INTERVAL = 100  # Visa progress var 10k hand

def ensure_output_table(conn: sqlite3.Connection):
    """
    Skapar tabellen player_top_opponent i heavy_analysis.db om den inte finns.
    """
    conn.execute("""
    CREATE TABLE IF NOT EXISTS player_top_opponent (
        player_id      TEXT PRIMARY KEY,
        top_opponent   TEXT,
        hands_together INTEGER,
        percentage     REAL,
        total_hands    INTEGER,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    print("✅ Ensured player_top_opponent table exists")

def fetch_hand_players_chunked(conn: sqlite3.Connection) -> Iterator[List[Tuple[str, str]]]:
    """
    🆕 Hämta hand_players data i chunks för att undvika minnesöverbelastning.
    Returnerar en iterator med chunks av (hand_id, player_id) tuples.
    """
    try:
        # Först, räkna totalt antal rader
        count_cur = conn.execute("SELECT COUNT(*) FROM hand_players WHERE hand_id IS NOT NULL AND player_id IS NOT NULL;")
        total_rows = count_cur.fetchone()[0]
        print(f"📊 Total hand_players entries to process: {total_rows:,}")
        
        if total_rows == 0:
            print("✅ No hand_players data to process - empty database")
            return
            
        # Använd OFFSET/LIMIT för att hämta data i chunks
        offset = 0
        while offset < total_rows:
            cur = conn.execute("""
                SELECT hand_id, player_id 
                FROM hand_players 
                WHERE hand_id IS NOT NULL AND player_id IS NOT NULL
                ORDER BY hand_id, player_id
                LIMIT ? OFFSET ?
            """, (CHUNK_SIZE, offset))
            
            chunk = cur.fetchall()
            if not chunk:
                break
                
            print(f"📦 Processing chunk {offset//CHUNK_SIZE + 1}/{(total_rows-1)//CHUNK_SIZE + 1} ({len(chunk):,} rows)")
            yield chunk
            
            offset += CHUNK_SIZE
            
            # 🆕 Ge andra processer chans att köra
            time.sleep(0.1)
            
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("❌ Table 'hand_players' not found in source database")
            return
        raise

def build_interactions_chunked(hand_player_chunks: Iterator[List[Tuple[str, str]]]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]]]:
    """
    🆕 Tar chunks av hand_players data och bygger interactions incrementellt.
    Returnerar total_hands och interactions dictionaries.
    """
    print("🔄 Building player interactions (chunked processing)...")
    
    total_hands: Dict[str, int] = defaultdict(int)
    interactions: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    processed_rows = 0
    current_hand_players: Dict[str, List[str]] = defaultdict(list)
    
    # 🆕 Hantera tom iterator/databas
    chunk_count = 0
    for chunk in hand_player_chunks:
        if not chunk:
            continue
            
        chunk_count += 1
        
        # Bearbeta denna chunk
        for hand_id, player_id in chunk:
            current_hand_players[hand_id].append(player_id)
            processed_rows += 1
            
            if processed_rows % PROGRESS_INTERVAL == 0:
                print(f"⏳ Processed {processed_rows:,} hand_players entries...")
        
        # 🆕 Periodiskt bearbeta och rensa för att spara minne
        if len(current_hand_players) >= CHUNK_SIZE // 4:  # När vi har ~12.5k händer
            _process_hands_batch(current_hand_players, total_hands, interactions)
            current_hand_players.clear()
            gc.collect()  # Tvinga garbage collection
    
    # 🆕 Hantera tom databas direkt
    if chunk_count == 0:
        print("✅ No chunks to process - empty database or no data found")
        return total_hands, interactions
    
    # Bearbeta sista batchen
    if current_hand_players:
        _process_hands_batch(current_hand_players, total_hands, interactions)
    
    print(f"✅ Completed processing {processed_rows:,} entries from {chunk_count} chunks")
    print(f"📊 Found {len(total_hands):,} unique players from {processed_rows:,} entries")
    
    return total_hands, interactions

def _process_hands_batch(hands_to_players: Dict[str, List[str]], 
                        total_hands: Dict[str, int], 
                        interactions: Dict[str, Dict[str, int]]):
    """🆕 Hjälpfunktion för att bearbeta en batch av händer."""
    
    # Räkna total_hands per player
    for hand_id, players in hands_to_players.items():
        for pid in set(players):
            total_hands[pid] += 1

    # Beräkna interactions mellan spelare
    for players in hands_to_players.values():
        unique_players = list(set(players))
        n = len(unique_players)
        
        # 🆕 Hoppa över händer med för många spelare (ovanligt och dyrt)
        if n > 20:  # Mer än 20 spelare i en hand är ovanligt
            continue
            
        for i in range(n):
            p1 = unique_players[i]
            for j in range(i + 1, n):
                p2 = unique_players[j]
                interactions[p1][p2] += 1
                interactions[p2][p1] += 1

def compute_and_store_batched(heavy_conn: sqlite3.Connection,
                              total_hands: Dict[str, int],
                              interactions: Dict[str, Dict[str, int]]):
    """
    🆕 Beräknar och lagrar resultat i batches för bättre performance.
    """
    if not total_hands:
        print("✅ No players to process - database is empty")
        # 🆕 Säkerställ ändå att tabellen finns för framtida användning
        ensure_output_table(heavy_conn)
        return

    print(f"📝 Storing results for {len(total_hands):,} players in batches...")
    
    players = list(total_hands.items())
    batch_count = 0
    processed_count = 0
    
    # Bearbeta i batches
    for i in range(0, len(players), BATCH_SIZE):
        batch = players[i:i + BATCH_SIZE]
        batch_count += 1
        
        # Bygg batch av data för INSERT
        batch_data = []
        for player_id, tot in batch:
            other_counts = interactions.get(player_id, {})
            
            if not other_counts:
                # Inga motståndare
                batch_data.append((player_id, None, 0, 0, tot))
            else:
                # Hitta motståndare med högst antal gemensamma händer
                other_id, hands_together = max(other_counts.items(), key=lambda kv: kv[1])
                procent = (hands_together / tot) * 100 if tot > 0 else 0.0
                batch_data.append((player_id, other_id, hands_together, procent, tot))
                
                # Debug för spelare med hög collusion-procent
                if procent > 50:
                    print(f"🔍 High interaction: {player_id} played {procent:.1f}% with {other_id} ({hands_together}/{tot})")
        
        # 🆕 Batch INSERT
        heavy_conn.executemany(
            """
            INSERT OR REPLACE INTO player_top_opponent
              (player_id, top_opponent, hands_together, percentage, total_hands)
            VALUES (?, ?, ?, ?, ?)
            """,
            batch_data
        )
        
        processed_count += len(batch_data)
        
        # Commit varje batch och visa progress
        heavy_conn.commit()
        print(f"💾 Batch {batch_count} completed - {processed_count:,}/{len(players):,} players processed")
        
        # 🆕 Kort paus för att ge andra processer chans
        time.sleep(0.05)

    print(f"✅ Stored results for {processed_count:,} players")

# ============================================================================
# 🆕 BACKWARD COMPATIBILITY FUNCTIONS
# Dessa funktioner behålls för att inte förstöra andra delar av systemet
# som fortfarande anropar de gamla funktionsnamnen (t.ex. heavy_db_builder.py)
# ============================================================================

def fetch_hand_players(conn: sqlite3.Connection) -> List[Tuple[str, str]]:
    """
    🔄 Bakåtkompatibilitetsfunktion för heavy_db_builder.py
    Konverterar den nya chunked implementationen till gamla API:t.
    """
    print("⚠️ Using legacy fetch_hand_players - consider upgrading to chunked version")
    
    # 🆕 Snabb kontroll för tom databas
    try:
        count_cur = conn.execute("SELECT COUNT(*) FROM hand_players WHERE hand_id IS NOT NULL AND player_id IS NOT NULL;")
        total_rows = count_cur.fetchone()[0]
        if total_rows == 0:
            print("✅ Legacy: No hand_players data found - returning empty list")
            return []
    except sqlite3.OperationalError as e:
        if "no such table" in str(e):
            print("✅ Legacy: hand_players table doesn't exist - returning empty list")
            return []
        raise
    
    # Samla alla chunks till en lista (för små dataset)
    all_rows = []
    for chunk in fetch_hand_players_chunked(conn):
        all_rows.extend(chunk)
    
    print(f"✅ Legacy: Fetched {len(all_rows)} hand_players entries")
    return all_rows

def build_interactions(hand_player_rows: List[Tuple[str, str]]) -> Tuple[Dict[str, int], Dict[str, Dict[str, int]]]:
    """
    🔄 Bakåtkompatibilitetsfunktion för heavy_db_builder.py
    Konverterar gamla listan till chunked format och använder nya implementationen.
    """
    print("⚠️ Using legacy build_interactions - consider upgrading to chunked version")
    
    if not hand_player_rows:
        print("⚠️ No hand_players data to process")
        return {}, {}
    
    # Konvertera listan till chunks för nya implementationen
    def list_to_chunks(data_list, chunk_size=CHUNK_SIZE):
        for i in range(0, len(data_list), chunk_size):
            yield data_list[i:i + chunk_size]
    
    chunks = list_to_chunks(hand_player_rows)
    return build_interactions_chunked(chunks)

def compute_and_store(heavy_conn: sqlite3.Connection,
                      total_hands: Dict[str, int],
                      interactions: Dict[str, Dict[str, int]]):
    """
    🔄 Bakåtkompatibilitetsfunktion för heavy_db_builder.py
    Anropar den nya batch-optimerade versionen.
    """
    print("⚠️ Using legacy compute_and_store - consider upgrading to batched version")
    return compute_and_store_batched(heavy_conn, total_hands, interactions)

# ============================================================================

def main():
    """Main function with proper CLI argument handling like other heavy_calc_db scripts."""
    parser = argparse.ArgumentParser(
        description="Calculate top opponent statistics from poker.db and store in heavy_analysis.db"
    )
    parser.add_argument(
        "--source", "-s",
        help="Path to source database (poker.db). If not specified, uses environment variables or default paths."
    )
    parser.add_argument(
        "--output", "-o", 
        help="Path to output database (heavy_analysis.db). If not specified, uses environment variables or default paths."
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print("🔧 Starting top opponent calculation...")
        print(f"   Source: {args.source or 'auto-detect'}")
        print(f"   Output: {args.output or 'auto-detect'}")

    # Använd db_io för att hitta source database (poker.db)
    try:
        if args.source:
            source_path = Path(args.source)
            if not source_path.exists():
                print(f"❌ Source database not found: {source_path}")
                sys.exit(1)
        else:
            source_path = db_io.get_default_db()
            if not source_path:
                print("❌ Could not find source database (poker.db)")
                print("   Set SQLITE_DB environment variable or use --source argument")
                sys.exit(1)
        
        print(f"📖 Using source database: {source_path}")
        
    except Exception as e:
        print(f"❌ Error finding source database: {e}")
        sys.exit(1)

    # Hitta output database (heavy_analysis.db)
    if args.output:
        output_path = Path(args.output)
    else:
        # Default: samma mapp som source men med namnet heavy_analysis.db
        output_path = source_path.parent / "heavy_analysis.db"
    
    print(f"📝 Using output database: {output_path}")

    # Läs från source database och bygg interactions
    try:
        with db_io.connect(source_path) as conn_src:
            hand_player_chunks = fetch_hand_players_chunked(conn_src)
            # 🆕 Bygg interactions direkt från chunks
            total_hands, interactions = build_interactions_chunked(hand_player_chunks)
            
        if not total_hands:
            print("❌ No hand_players data found or processed from source database")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error reading from source database: {e}")
        sys.exit(1)

    # Skriv till output database
    try:
        conn_heavy = sqlite3.connect(output_path)
        
        # Skapa tabell om den saknas
        ensure_output_table(conn_heavy)

        # Beräkna och skriv in värdena
        compute_and_store_batched(conn_heavy, total_hands, interactions)

        print("✅ Top opponent calculation completed successfully!")
        
        # Visa statistik
        cursor = conn_heavy.execute("SELECT COUNT(*) FROM player_top_opponent")
        total_players = cursor.fetchone()[0]
        
        cursor = conn_heavy.execute("SELECT COUNT(*) FROM player_top_opponent WHERE percentage > 30")
        high_interaction = cursor.fetchone()[0]
        
        print(f"📊 Statistics:")
        print(f"   Total players processed: {total_players}")
        print(f"   Players with >30% interaction: {high_interaction}")
        
        if high_interaction > 0:
            print("🔍 Players with highest interaction rates:")
            cursor = conn_heavy.execute("""
                SELECT player_id, top_opponent, percentage, hands_together, total_hands
                FROM player_top_opponent 
                WHERE percentage > 30 
                ORDER BY percentage DESC 
                LIMIT 5
            """)
            for row in cursor:
                print(f"   {row[0]} → {row[1]}: {row[2]:.1f}% ({row[3]}/{row[4]} hands)")
        
        conn_heavy.close()
        
    except Exception as e:
        print(f"❌ Error writing to output database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
