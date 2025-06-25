#!/usr/bin/env python3
"""
7_input_scores.py - Mappar scores till nya kolumner preflop_score och postflop_score
────────────────────────────────────────────────────────────────────────────────────

• Läser från heavy_analysis.db
• Skapar nya kolumner: preflop_score och postflop_score i actions-tabellen
• Mappar preflop_scores (freq) till preflop_score för preflop actions
• Mappar postflop_scores (action_score) till postflop_score för postflop actions
• Hanterar diskrepans i hand_id format (med/utan "Hand" prefix)
"""

from __future__ import annotations
import argparse, sqlite3, sys
from pathlib import Path

# ────────────────────────────────────────────────────────────────
# 0. Hitta projektrot och databas
# ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
while ROOT != ROOT.parent and not (ROOT / "config.txt").is_file():
    ROOT = ROOT.parent
if not (ROOT / "config.txt").is_file():
    sys.exit("❌ Hittar ingen config.txt uppåt i trädet")

DEFAULT_DB = ROOT / "local_data" / "database" / "heavy_analysis.db"

# ────────────────────────────────────────────────────────────────
# 1. Schema-uppdatering
# ────────────────────────────────────────────────────────────────
def ensure_score_columns(con: sqlite3.Connection):
    """Lägger till preflop_score, postflop_score och solver_best kolumner om de saknas."""
    cur = con.cursor()
    
    # Kolla vilka kolumner som finns
    cur.execute("PRAGMA table_info(actions)")
    existing_cols = {row[1] for row in cur.fetchall()}
    
    # Lägg till kolumner om de saknas
    if "preflop_score" not in existing_cols:
        cur.execute("ALTER TABLE actions ADD COLUMN preflop_score REAL")
        print("✅ Lade till kolumn: preflop_score")
    
    if "postflop_score" not in existing_cols:
        cur.execute("ALTER TABLE actions ADD COLUMN postflop_score REAL")
        print("✅ Lade till kolumn: postflop_score")
    
    if "solver_best" not in existing_cols:
        cur.execute("ALTER TABLE actions ADD COLUMN solver_best TEXT")
        print("✅ Lade till kolumn: solver_best")
    
    con.commit()

# ────────────────────────────────────────────────────────────────
# 2. Hjälpfunktioner för hand_id konvertering
# ────────────────────────────────────────────────────────────────
def normalize_hand_id(hand_id: str) -> str:
    """Tar bort 'Hand' prefix om det finns för att få bara numret."""
    if hand_id and hand_id.startswith("Hand"):
        return hand_id[4:]  # Ta bort "Hand"
    return hand_id

def denormalize_hand_id(hand_id: str) -> str:
    """Lägger till 'Hand' prefix om det saknas."""
    if hand_id and not hand_id.startswith("Hand"):
        return f"Hand{hand_id}"
    return hand_id

# ────────────────────────────────────────────────────────────────
# 3. Mapping-funktioner
# ────────────────────────────────────────────────────────────────
def map_preflop_scores(con: sqlite3.Connection) -> int:
    """
    Mappar preflop_scores (freq) till preflop_score kolumnen.
    Matchar på hand_id + position för preflop actions.
    Hanterar både "Hand249244191" och "249244191" format.
    """
    cur = con.cursor()
    
    # Hämta preflop actions som saknar scores
    sql_get_actions = """
    SELECT rowid, hand_id, position 
    FROM actions 
    WHERE street = 'preflop' 
      AND preflop_score IS NULL 
      AND action IN ('r', 'c', 'f')
    """
    
    actions = cur.execute(sql_get_actions).fetchall()
    if not actions:
        return 0
    
    # Hämta alla preflop_scores för effektivitet
    sql_get_scores = """
    SELECT hand_id, position, freq, best 
    FROM preflop_scores
    WHERE freq IS NOT NULL
    """
    
    scores = {}
    for hand_id, position, freq, best in cur.execute(sql_get_scores):
        # Spara både med och utan "Hand" prefix för flexibilitet
        score_data = (freq, best)
        scores[(hand_id, position)] = score_data
        scores[(denormalize_hand_id(hand_id), position)] = score_data
        scores[(normalize_hand_id(hand_id), position)] = score_data
    
    # Mappa scores till actions
    updates = []
    matched = 0
    not_matched = 0
    
    for rowid, hand_id, position in actions:
        # Prova olika varianter av hand_id
        keys_to_try = [
            (hand_id, position),
            (normalize_hand_id(hand_id), position),
            (denormalize_hand_id(hand_id), position)
        ]
        
        found = False
        for key in keys_to_try:
            if key in scores:
                freq, best = scores[key]
                updates.append((freq, best, rowid))
                matched += 1
                found = True
                break
        
        if not found:
            not_matched += 1
    
    # Uppdatera actions-tabellen
    if updates:
        cur.executemany(
            "UPDATE actions SET preflop_score = ?, solver_best = ? WHERE rowid = ?",
            updates
        )
        con.commit()
    
    print(f"   📊 Matchade: {matched:,} actions")
    print(f"   ❌ Ej matchade: {not_matched:,} actions")
    
    return len(updates)

def map_postflop_scores(con: sqlite3.Connection) -> int:
    """
    Mappar postflop_scores (action_score) till postflop_score kolumnen.
    Matchar på hand_id + node_string som ska motsvara state_prefix + action.
    """
    cur = con.cursor()
    
    # Hämta postflop actions som saknar scores
    sql_get_actions = """
    SELECT rowid, hand_id, state_prefix, action 
    FROM actions 
    WHERE street != 'preflop' 
      AND postflop_score IS NULL 
      AND action IN ('r', 'c', 'f', 'x')
    """
    
    actions = cur.execute(sql_get_actions).fetchall()
    if not actions:
        return 0
    
    # Hämta alla postflop_scores för effektivitet
    sql_get_scores = """
    SELECT hand_id, node_string, action_score 
    FROM postflop_scores
    WHERE action_score IS NOT NULL
    """
    
    scores = {}
    for hand_id, node_string, action_score in cur.execute(sql_get_scores):
        # Spara med alla varianter av hand_id
        scores[(hand_id, node_string)] = action_score
        scores[(normalize_hand_id(hand_id), node_string)] = action_score
        scores[(denormalize_hand_id(hand_id), node_string)] = action_score
    
    # Mappa scores till actions
    updates = []
    matched_direct = 0
    matched_prefix = 0
    not_matched = 0
    
    for rowid, hand_id, state_prefix, action in actions:
        # Bygg expected node_string genom att kombinera state_prefix + action
        node_string = state_prefix + action
        
        # Prova olika varianter av hand_id
        keys_to_try = [
            (hand_id, node_string),
            (normalize_hand_id(hand_id), node_string),
            (denormalize_hand_id(hand_id), node_string)
        ]
        
        found = False
        for key in keys_to_try:
            if key in scores:
                action_score = scores[key]
                updates.append((action_score, rowid))
                matched_direct += 1
                found = True
                break
        
        if not found:
            # Försök även med kortare noder (för prefix-matching)
            for stored_key, action_score in scores.items():
                stored_hand_id, stored_node = stored_key
                # Matcha hand_id (med flexibilitet för format)
                hand_id_matches = (
                    stored_hand_id == hand_id or
                    stored_hand_id == normalize_hand_id(hand_id) or
                    stored_hand_id == denormalize_hand_id(hand_id)
                )
                
                if hand_id_matches and node_string.startswith(stored_node):
                    updates.append((action_score, rowid))
                    matched_prefix += 1
                    found = True
                    break
        
        if not found:
            not_matched += 1
    
    # Uppdatera actions-tabellen
    if updates:
        cur.executemany(
            "UPDATE actions SET postflop_score = ? WHERE rowid = ?",
            updates
        )
        con.commit()
    
    print(f"   📊 Direkta matchningar: {matched_direct:,}")
    print(f"   📊 Prefix-matchningar: {matched_prefix:,}")
    print(f"   ❌ Ej matchade: {not_matched:,}")
    
    return len(updates)

def create_missing_indexes(con: sqlite3.Connection):
    """Skapar index för bättre prestanda."""
    cur = con.cursor()
    
    # Index för actions-tabellen
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_actions_hand_position 
        ON actions(hand_id, position)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_actions_hand_state_action 
        ON actions(hand_id, state_prefix, action)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_actions_preflop_score 
        ON actions(preflop_score)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_actions_postflop_score 
        ON actions(postflop_score)
    """)
    
    # Index för score-tabellerna
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_preflop_scores_hand_position 
        ON preflop_scores(hand_id, position)
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_postflop_scores_hand_node 
        ON postflop_scores(hand_id, node_string)
    """)
    
    con.commit()

# ────────────────────────────────────────────────────────────────
# 4. Statistik och validering
# ────────────────────────────────────────────────────────────────
def show_statistics(con: sqlite3.Connection, verbose: bool = False):
    """Visar statistik över mappade scores."""
    cur = con.cursor()
    
    # Räkna totala actions
    total_actions = cur.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    
    # Räkna preflop actions och scores
    preflop_actions = cur.execute(
        "SELECT COUNT(*) FROM actions WHERE street = 'preflop'"
    ).fetchone()[0]
    
    preflop_scored = cur.execute(
        "SELECT COUNT(*) FROM actions WHERE street = 'preflop' AND preflop_score IS NOT NULL"
    ).fetchone()[0]
    
    # Räkna postflop actions och scores
    postflop_actions = cur.execute(
        "SELECT COUNT(*) FROM actions WHERE street != 'preflop'"
    ).fetchone()[0]
    
    postflop_scored = cur.execute(
        "SELECT COUNT(*) FROM actions WHERE street != 'preflop' AND postflop_score IS NOT NULL"
    ).fetchone()[0]
    
    print(f"\n📊 STATISTIK:")
    print(f"   Totala actions: {total_actions:,}")
    print(f"   Preflop actions: {preflop_actions:,}")
    print(f"   Preflop med score: {preflop_scored:,} ({preflop_scored/preflop_actions*100:.1f}% if preflop_actions > 0 else 0)")
    print(f"   Postflop actions: {postflop_actions:,}")
    print(f"   Postflop med score: {postflop_scored:,} ({postflop_scored/postflop_actions*100:.1f}% if postflop_actions > 0 else 0)")
    
    if verbose:
        # Visa score-distribution
        print(f"\n📈 SCORE-DISTRIBUTION:")
        
        # Preflop score ranges
        cur.execute("""
            SELECT 
                ROUND(preflop_score, 2) as score_range,
                COUNT(*) as count
            FROM actions 
            WHERE preflop_score IS NOT NULL 
            GROUP BY ROUND(preflop_score, 2)
            ORDER BY score_range
            LIMIT 10
        """)
        
        preflop_results = cur.fetchall()
        if preflop_results:
            print("   Preflop scores (topp 10):")
            for score, count in preflop_results:
                print(f"     {score}: {count:,} actions")
        
        # Postflop score ranges
        cur.execute("""
            SELECT 
                CASE 
                    WHEN postflop_score < 20 THEN '0-20'
                    WHEN postflop_score < 40 THEN '20-40'
                    WHEN postflop_score < 60 THEN '40-60'
                    WHEN postflop_score < 80 THEN '60-80'
                    ELSE '80-100'
                END as score_range,
                COUNT(*) as count
            FROM actions 
            WHERE postflop_score IS NOT NULL 
            GROUP BY score_range
            ORDER BY score_range
        """)
        
        postflop_results = cur.fetchall()
        if postflop_results:
            print("\n   Postflop scores (distribution):")
            for score_range, count in postflop_results:
                print(f"     {score_range}: {count:,} actions")

def normalize_scores_to_100_scale(con: sqlite3.Connection) -> tuple[int, int]:
    """
    Normaliserar alla scores till 1-100 skala.
    
    Returns:
        tuple: (preflop_normalized, postflop_normalized) antal normaliserade scores
    """
    cur = con.cursor()
    
    print("📊 Analyserar score-distribution...")
    
    # Analysera preflop scores
    cur.execute("""
        SELECT MIN(preflop_score), MAX(preflop_score), AVG(preflop_score), COUNT(*)
        FROM actions 
        WHERE preflop_score IS NOT NULL
    """)
    preflop_stats = cur.fetchone()
    
    if preflop_stats and preflop_stats[3] > 0:  # Om vi har data
        min_pre, max_pre, avg_pre, count_pre = preflop_stats
        print(f"   Preflop: min={min_pre:.2f}, max={max_pre:.2f}, avg={avg_pre:.2f}, count={count_pre:,}")
        
        # Normalisera preflop scores till 1-100
        if max_pre != min_pre:  # Undvik division med noll
            cur.execute("""
                UPDATE actions 
                SET preflop_score = 1 + ((preflop_score - ?) / (? - ?)) * 99
                WHERE preflop_score IS NOT NULL
            """, (min_pre, max_pre, min_pre))
            preflop_normalized = cur.rowcount
        else:
            # Om alla scores är samma, sätt dem till 50
            cur.execute("""
                UPDATE actions 
                SET preflop_score = 50 
                WHERE preflop_score IS NOT NULL
            """)
            preflop_normalized = cur.rowcount
    else:
        preflop_normalized = 0
    
    # Analysera postflop scores
    cur.execute("""
        SELECT MIN(postflop_score), MAX(postflop_score), AVG(postflop_score), COUNT(*)
        FROM actions 
        WHERE postflop_score IS NOT NULL
    """)
    postflop_stats = cur.fetchone()
    
    if postflop_stats and postflop_stats[3] > 0:  # Om vi har data
        min_post, max_post, avg_post, count_post = postflop_stats
        print(f"   Postflop: min={min_post:.2f}, max={max_post:.2f}, avg={avg_post:.2f}, count={count_post:,}")
        
        # Normalisera postflop scores till 1-100
        if max_post != min_post:  # Undvik division med noll
            cur.execute("""
                UPDATE actions 
                SET postflop_score = 1 + ((postflop_score - ?) / (? - ?)) * 99
                WHERE postflop_score IS NOT NULL
            """, (min_post, max_post, min_post))
            postflop_normalized = cur.rowcount
        else:
            # Om alla scores är samma, sätt dem till 50
            cur.execute("""
                UPDATE actions 
                SET postflop_score = 50 
                WHERE postflop_score IS NOT NULL
            """)
            postflop_normalized = cur.rowcount
    else:
        postflop_normalized = 0
    
    con.commit()
    
    print(f"✅ Normaliserade {preflop_normalized:,} preflop scores till 1-100 skala")
    print(f"✅ Normaliserade {postflop_normalized:,} postflop scores till 1-100 skala")
    
    return preflop_normalized, postflop_normalized

# ────────────────────────────────────────────────────────────────
# 5. Main-funktion
# ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Mappar scores till nya preflop_score och postflop_score kolumner")
    parser.add_argument("--db", help="Sökväg till heavy_analysis.db")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--stats-only", action="store_true", help="Visa endast statistik")
    parser.add_argument("--normalize", action="store_true", help="Normalisera scores till 1-100 skala")
    args = parser.parse_args()
    
    db_path = Path(args.db).expanduser().resolve() if args.db else DEFAULT_DB
    
    if not db_path.exists():
        sys.exit(f"❌ Hittar inte databasen: {db_path}")
    
    # Kolla att nödvändiga tabeller finns
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    
    tables = [row[0] for row in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )]
    
    required_tables = ['actions', 'preflop_scores', 'postflop_scores']
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        sys.exit(f"❌ Saknar tabeller: {', '.join(missing_tables)}")
    
    if args.verbose:
        print(f"📊 Använder databas: {db_path}")
    
    # Visa endast statistik om så önskas
    if args.stats_only:
        show_statistics(con, args.verbose)
        con.close()
        return
    
    # Säkerställ att score-kolumnerna finns
    ensure_score_columns(con)
    
    if args.verbose:
        print("📈 Skapar index för bättre prestanda...")
    
    # Skapa index för bättre prestanda
    create_missing_indexes(con)
    
    # Räkna rader som behöver uppdateras
    cur = con.cursor()
    preflop_missing = cur.execute("""
        SELECT COUNT(*) FROM actions 
        WHERE street = 'preflop' AND preflop_score IS NULL
    """).fetchone()[0]
    
    postflop_missing = cur.execute("""
        SELECT COUNT(*) FROM actions 
        WHERE street != 'preflop' AND postflop_score IS NULL
    """).fetchone()[0]
    
    if args.verbose:
        print(f"📋 Preflop actions utan scores: {preflop_missing:,}")
        print(f"📋 Postflop actions utan scores: {postflop_missing:,}")
    
    # Mappa preflop scores
    if preflop_missing > 0:
        if args.verbose:
            print("🔄 Mappar preflop scores...")
        preflop_updated = map_preflop_scores(con)
        print(f"✅ Preflop: {preflop_updated:,} actions fick scores")
    else:
        preflop_updated = 0
        if args.verbose:
            print("⏭️  Preflop: inga scores att mappa")
    
    # Mappa postflop scores
    if postflop_missing > 0:
        if args.verbose:
            print("🔄 Mappar postflop scores...")
        postflop_updated = map_postflop_scores(con)
        print(f"✅ Postflop: {postflop_updated:,} actions fick scores")
    else:
        postflop_updated = 0
        if args.verbose:
            print("⏭️  Postflop: inga scores att mappa")
    
    # Slutrapport
    total_updated = preflop_updated + postflop_updated
    if total_updated > 0:
        print(f"🎉 Totalt: {total_updated:,} actions uppdaterade med scores")
    else:
        print("ℹ️  Inga nya scores att mappa")
    
    # Normalisera scores till 1-100 skala (körs alltid eller med --normalize flag)
    if args.normalize or total_updated > 0:
        print("\n🔧 Normaliserar scores till 1-100 skala...")
        normalize_scores_to_100_scale(con)
    
    # Visa statistik
    show_statistics(con, args.verbose)
    
    con.close()

if __name__ == "__main__":
    main() 