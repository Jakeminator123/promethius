#!/usr/bin/env python3
# pyright: ignore[reportImplicitRelativeImport]
"""
7_input_scores.py - Mappar preflop/postflop scores till actions-tabellen

Detta script:
1. Läser preflop scores från preflop_scores tabellen
2. Läser postflop scores från postflop_scores tabellen  
3. Mappar dessa till nya kolumner i actions tabellen
4. Normaliserar alla scores till 1-100 skala

Körs som sista steget efter att alla andra analyser är klara.
"""

from __future__ import annotations
import argparse
import sqlite3
import sys
from pathlib import Path
from typing import List, Tuple

# ────────────────────────────────────────────────────────────────
# 0. Import paths
# ────────────────────────────────────────────────────────────────
# Lägg till parent directory till path för import
sys.path.append(str(Path(__file__).resolve().parent))
# Import av script_paths - linter varnar men det fungerar korrekt
# eftersom vi lägger till sökvägen dynamiskt ovan
from script_paths import ROOT, DST_DB  # noqa: E402 # pylint: disable=import-error  # type: ignore

DEFAULT_DB = DST_DB  # Använder centraliserad path-hantering

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
      AND action IN ('r', 'c', 'f')  -- Bara actions som har scores i preflop_scores tabellen
    """
    
    actions = cur.execute(sql_get_actions).fetchall()
    if not actions:
        return 0
    
    # Hämta unika hand_ids som behöver scores
    unique_hand_ids = list(set(row[1] for row in actions))
    
    # Skapa varianter av hand_ids för flexibel matchning
    hand_id_variants = set()
    for hid in unique_hand_ids:
        hand_id_variants.add(hid)
        hand_id_variants.add(normalize_hand_id(hid))
        hand_id_variants.add(denormalize_hand_id(hid))
    
    # Hämta BARA relevanta preflop_scores
    placeholders = ','.join('?' for _ in hand_id_variants)
    sql_get_scores = f"""
    SELECT hand_id, position, freq, best 
    FROM preflop_scores
    WHERE freq IS NOT NULL
      AND hand_id IN ({placeholders})
    """
    
    scores = {}
    vars_per_id   = 1            # just hand_id
    MAX_SQL_VARS  = 999
    CHUNK         = MAX_SQL_VARS // vars_per_id      # 999 is safe

    hand_list = list(hand_id_variants)

    for off in range(0, len(hand_list), CHUNK):
        chunk = hand_list[off : off + CHUNK]

        placeholders = ",".join("?" for _ in chunk)
        sql = f"""
            SELECT hand_id, position, freq, best
            FROM   preflop_scores
            WHERE  freq IS NOT NULL
            AND  hand_id IN ({placeholders})
        """

        cur.execute(sql, chunk)                 # <-- exactly len(chunk) bindings

        for hand_id, position, freq, best in cur:
            score = (freq, best)
            scores[(hand_id,                     position)] = score
            scores[(denormalize_hand_id(hand_id), position)] = score
            scores[(normalize_hand_id(hand_id),   position)] = score
    
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
    
    # Uppdatera actions-tabellen i batches
    if updates:
        batch_size = 5000  # Större batch för snabbare processing
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            cur.executemany(
                "UPDATE actions SET preflop_score = ?, solver_best = ? WHERE rowid = ?",
                batch
            )
        con.commit()
    
    print(f"   📊 Matchade: {matched:,} actions")
    print(f"   ❌ Ej matchade: {not_matched:,} actions")
    
    return len(updates)

# Global set för att hålla koll på redan loggade händer
_logged_missing_hands = set()

def map_postflop_scores(con: sqlite3.Connection) -> int:
    """
    Mappar postflop_scores (action_score) till postflop_score kolumnen.
    Matchar på hand_id + node_string som ska motsvara state_prefix + action.
    """
    cur = con.cursor()
    
    # Hämta det senaste datumet som har postflop_scores
    latest_date = cur.execute("""
        SELECT MAX(h.hand_date) 
        FROM hand_info h
        INNER JOIN postflop_scores ps ON h.hand_id = ps.hand_id
    """).fetchone()[0]
    
    if not latest_date:
        print("   ℹ️  Inga postflop_scores hittades")
        return 0
    
    # Hämta postflop actions som saknar scores, MEN bara för händer som HAR partial_scores
    # OCH bara för det senaste datumet
    sql_get_actions = """
    SELECT DISTINCT a.rowid, a.hand_id, a.state_prefix, a.action, a.amount_to 
    FROM actions a
    INNER JOIN postflop_scores ps ON a.hand_id = ps.hand_id
    INNER JOIN hand_info h ON a.hand_id = h.hand_id
    WHERE a.street != 'preflop' 
      AND a.postflop_score IS NULL 
      AND a.action IN ('r', 'c', 'f', 'x')
      AND h.hand_date = ?
    LIMIT 10000  -- Höjd gräns för större batches
    """
    
    actions = cur.execute(sql_get_actions, (latest_date,)).fetchall()
    
    if not actions:
        # Om inga actions för senaste datumet, kolla de 3 senaste datumen
        sql_recent_dates = """
        SELECT DISTINCT hand_date 
        FROM hand_info 
        WHERE hand_date IS NOT NULL
        ORDER BY hand_date DESC 
        LIMIT 3
        """
        recent_dates = [row[0] for row in cur.execute(sql_recent_dates).fetchall()]
        
        if recent_dates:
            placeholders = ','.join('?' for _ in recent_dates)
            sql_get_actions_recent = f"""
            SELECT DISTINCT a.rowid, a.hand_id, a.state_prefix, a.action, a.amount_to 
            FROM actions a
            INNER JOIN postflop_scores ps ON a.hand_id = ps.hand_id
            INNER JOIN hand_info h ON a.hand_id = h.hand_id
            WHERE a.street != 'preflop' 
              AND a.postflop_score IS NULL 
              AND a.action IN ('r', 'c', 'f', 'x')
              AND h.hand_date IN ({placeholders})
            LIMIT 10000
            """
            actions = cur.execute(sql_get_actions_recent, recent_dates).fetchall()
    
    if not actions:
        return 0
    
    # Hämta unika hand_ids
    unique_hand_ids = list(set(row[1] for row in actions))
    
    # Skapa varianter av hand_ids
    hand_id_variants = set()
    for hid in unique_hand_ids:
        hand_id_variants.add(hid)
        hand_id_variants.add(normalize_hand_id(hid))
        hand_id_variants.add(denormalize_hand_id(hid))
    
    # Hämta ALLA postflop_scores för relevanta händer (inte bara exakt matchning)
    placeholders = ','.join('?' for _ in hand_id_variants)
    sql_get_scores = f"""
    SELECT hand_id, node_string, action_score 
    FROM postflop_scores
    WHERE action_score IS NOT NULL
      AND hand_id IN ({placeholders})
    """
    
    scores = {}
    # Dictionary för att hålla koll på alla node_strings per hand
    hand_nodes = {}
    
    for hand_id, node_string, action_score in cur.execute(sql_get_scores, list(hand_id_variants)):
        # Spara med alla varianter av hand_id
        scores[(hand_id, node_string)] = action_score
        scores[(normalize_hand_id(hand_id), node_string)] = action_score
        scores[(denormalize_hand_id(hand_id), node_string)] = action_score
        
        # Samla alla node_strings per hand för debugging
        for hid in [hand_id, normalize_hand_id(hand_id), denormalize_hand_id(hand_id)]:
            if hid not in hand_nodes:
                hand_nodes[hid] = []
            hand_nodes[hid].append(node_string)
    
    # Mappa scores till actions
    updates = []
    matched_direct = 0
    matched_prefix = 0
    matched_suffix = 0
    not_matched = 0
    debug_misses = []  # För att spara info om missade matchningar
    hands_without_scores = set()  # Händer som helt saknar partial_scores
    
    for rowid, hand_id, state_prefix, action, amount_to in actions:
        # Bygg expected node_string 
        # För raise, inkludera hela beloppet
        if action == 'r' and amount_to:
            node_string = state_prefix + f"r{amount_to}"
        else:
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
            # Försök hitta node_strings som slutar med vårt state_prefix + action
            # Detta hanterar fall där node_string i postflop_scores har mer prefix
            for (stored_hand_id, stored_node), action_score in scores.items():
                if stored_hand_id in [hand_id, normalize_hand_id(hand_id), denormalize_hand_id(hand_id)]:
                    if stored_node.endswith(node_string):
                        updates.append((action_score, rowid))
                        matched_suffix += 1
                        found = True
                        break
        
        if not found:
            # Försök prefix-matching som tidigare
            for (stored_hand_id, stored_node), action_score in scores.items():
                if stored_hand_id in [hand_id, normalize_hand_id(hand_id), denormalize_hand_id(hand_id)]:
                    if node_string.startswith(stored_node):
                        updates.append((action_score, rowid))
                        matched_prefix += 1
                        found = True
                        break
        
        if not found:
            not_matched += 1
            # Kolla om handen har några nodes alls
            if hand_id not in _logged_missing_hands:
                available_nodes = hand_nodes.get(hand_id, [])
                if not available_nodes:
                    available_nodes = hand_nodes.get(normalize_hand_id(hand_id), [])
                if not available_nodes:
                    available_nodes = hand_nodes.get(denormalize_hand_id(hand_id), [])
                    
                if not available_nodes:
                    # Denna hand saknar partial_scores helt
                    hands_without_scores.add(hand_id)
                    _logged_missing_hands.add(hand_id)
                elif len(debug_misses) < 3:  # Bara visa 3 exempel på faktiska missmatchningar
                    debug_misses.append({
                        'hand_id': hand_id,
                        'expected': node_string,
                        'available': available_nodes[:3]
                    })
                    _logged_missing_hands.add(hand_id)
    
    # Visa debug-info
    if hands_without_scores and len(hands_without_scores) <= 5:
        print(f"\n   ⚠️  {len(hands_without_scores)} händer saknar partial_scores helt: {', '.join(list(hands_without_scores)[:5])}")
    elif hands_without_scores:
        print(f"\n   ⚠️  {len(hands_without_scores)} händer saknar partial_scores helt")
    
    if debug_misses:
        print("\n   🔍 Exempel på faktiska missmatchningar:")
        for miss in debug_misses:
            print(f"      {miss['hand_id']}: sökte '{miss['expected']}'")
            print(f"         Tillgängliga: {miss['available']}")
    
    # Uppdatera actions-tabellen i batches
    if updates:
        batch_size = 5000  # Större batch för snabbare processing
        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]
            cur.executemany(
                "UPDATE actions SET postflop_score = ? WHERE rowid = ?",
                batch
            )
        con.commit()
    
    print(f"   📊 Direkta matchningar: {matched_direct:,}")
    print(f"   📊 Suffix-matchningar: {matched_suffix:,}")
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
    pre_pct = (preflop_scored / preflop_actions * 100) if preflop_actions else 0
    print(f"   Preflop med score: {preflop_scored:,} ({pre_pct:.1f}%)")
    print(f"   Postflop actions: {postflop_actions:,}")
    post_pct = (postflop_scored / postflop_actions * 100) if postflop_actions else 0
    print(f"   Postflop med score: {postflop_scored:,} ({post_pct:.1f}%)")
    
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
    Konverterar scores från 0-1 skala till 0-100 skala genom att multiplicera med 100.
    
    Returns:
        tuple: (preflop_normalized, postflop_normalized) antal normaliserade scores
    """
    cur = con.cursor()
    
    print("📊 Konverterar scores till 0-100 skala...")
    
    # Först, kolla om preflop scores behöver konverteras (är mellan 0-1)
    cur.execute("""
        SELECT COUNT(*), MIN(preflop_score), MAX(preflop_score), AVG(preflop_score)
        FROM actions 
        WHERE preflop_score IS NOT NULL
    """)
    pre_stats = cur.fetchone()
    
    preflop_normalized = 0
    if pre_stats and pre_stats[0] > 0:  # Om vi har data
        count_pre, min_pre, max_pre, avg_pre = pre_stats
        print(f"   Preflop före konvertering: min={min_pre:.2f}, max={max_pre:.2f}, avg={avg_pre:.2f}")
        
        # Om max är <= 1.0, antar vi att det är 0-1 skala och multiplicerar med 100
        if max_pre <= 1.0:
            cur.execute("""
                UPDATE actions 
                SET preflop_score = preflop_score * 100
                WHERE preflop_score IS NOT NULL
            """)
            preflop_normalized = cur.rowcount
            print(f"   ✅ Konverterade {preflop_normalized:,} preflop scores från 0-1 till 0-100")
        else:
            print(f"   ℹ️  Preflop scores redan i 0-100 skala")
    
    # Samma för postflop scores
    cur.execute("""
        SELECT COUNT(*), MIN(postflop_score), MAX(postflop_score), AVG(postflop_score)
        FROM actions 
        WHERE postflop_score IS NOT NULL
    """)
    post_stats = cur.fetchone()
    
    postflop_normalized = 0
    if post_stats and post_stats[0] > 0:  # Om vi har data
        count_post, min_post, max_post, avg_post = post_stats
        print(f"   Postflop före konvertering: min={min_post:.2f}, max={max_post:.2f}, avg={avg_post:.2f}")
        
        # Om max är <= 1.0, antar vi att det är 0-1 skala och multiplicerar med 100
        if max_post <= 1.0:
            cur.execute("""
                UPDATE actions 
                SET postflop_score = postflop_score * 100
                WHERE postflop_score IS NOT NULL
            """)
            postflop_normalized = cur.rowcount
            print(f"   ✅ Konverterade {postflop_normalized:,} postflop scores från 0-1 till 0-100")
        else:
            print(f"   ℹ️  Postflop scores redan i 0-100 skala")
    
    con.commit()
    
    # Visa statistik efter konvertering
    if preflop_normalized > 0 or postflop_normalized > 0:
        print("\n📊 Efter konvertering:")
        
        if preflop_normalized > 0:
            cur.execute("""
                SELECT MIN(preflop_score), MAX(preflop_score), AVG(preflop_score)
                FROM actions WHERE preflop_score IS NOT NULL
            """)
            min_pre, max_pre, avg_pre = cur.fetchone()
            print(f"   Preflop: min={min_pre:.1f}, max={max_pre:.1f}, avg={avg_pre:.1f}")
        
        if postflop_normalized > 0:
            cur.execute("""
                SELECT MIN(postflop_score), MAX(postflop_score), AVG(postflop_score)
                FROM actions WHERE postflop_score IS NOT NULL
            """)
            min_post, max_post, avg_post = cur.fetchone()
            print(f"   Postflop: min={min_post:.1f}, max={max_post:.1f}, avg={avg_post:.1f}")
    
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
    
    # Temporärt stäng av full sync för snabbare bulk-updates
    con.execute("PRAGMA synchronous=OFF")
    
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
    
    # Mappa postflop scores i loop tills inga kvar (chunkad 1000 i funktionen)
    postflop_updated_total = 0
    while True:
        cur = con.cursor()
        remaining = cur.execute("SELECT COUNT(*) FROM actions WHERE street!='preflop' AND postflop_score IS NULL AND action IN ('r','c','f','x')").fetchone()[0]
        if remaining == 0:
            break
        if args.verbose:
            print(f"🔄 Mappar postflop scores (kvar {remaining:,})…")
        postflop_updated = map_postflop_scores(con)
        if postflop_updated == 0:
            # Inga fler matchningar möjliga – bryt för att undvika evig loop
            break
        postflop_updated_total += postflop_updated

    if postflop_updated_total:
        print(f"✅ Postflop: {postflop_updated_total:,} actions fick scores")
    
    # Slutrapport
    total_updated = preflop_updated + postflop_updated_total
    if total_updated > 0:
        print(f"🎉 Totalt: {total_updated:,} actions uppdaterade med scores")
    else:
        print("ℹ️  Inga nya scores att mappa")
    
    # Normalisera scores endast om --normalize flaggan anges
    if args.normalize:
        print("\n🔧 Normaliserar scores till 1-100 skala...")
        normalize_scores_to_100_scale(con)
    
    # Visa statistik
    show_statistics(con, args.verbose)
    
    # Återställ PRAGMA och checkpointa WAL
    try:
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        pass

    con.close()

if __name__ == "__main__":
    main() 