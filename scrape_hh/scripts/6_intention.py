#!/usr/bin/env python3
"""
6_intention.py - Smart JSON-baserat Intention System
──────────────────────────────────────────────────────────────────
Enkelt och smart system som utnyttjar JSON-filernas poker-kontext:

Street + Action_label → JSON-fil → Intention
• flop + cont → flop/cont.json → "strong-cbet" 
• turn + probe → turn/probe.json → "merge"
• river + donk → river/donk.json → "polarised-bluff-or-value"

Varje poker-situation har sin egen "personlighet"!
"""

from __future__ import annotations
import argparse, json, sqlite3, sys
from pathlib import Path

# ════════════════════════════════════════════════════════════════════
# Setup
# ════════════════════════════════════════════════════════════════════
# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from script_paths import ROOT, DST_DB

DB_PATH = DST_DB  # Använder centraliserad path-hantering

# JSON-filer kan finnas på olika ställen beroende på miljö
# Standard path
JSON_ROOT = ROOT / "utils" / "different_actions"

# Om standard path inte finns, prova alternativ
if not JSON_ROOT.exists():
    # Relativ från script
    alt_path = Path(__file__).parent.parent.parent / "utils" / "different_actions"
    if alt_path.exists():
        JSON_ROOT = alt_path
    else:
        # Render absolut path
        render_path = Path("/opt/render/project/src/utils/different_actions")
        if render_path.exists():
            JSON_ROOT = render_path

if not DB_PATH.exists():
    sys.exit(f"❌ {DB_PATH} saknas – bygg databasen först.")
if not JSON_ROOT.exists():
    sys.exit(f"❌ {JSON_ROOT} saknas – lägg JSON-filerna där.")

print(f"📁 Använder JSON från: {JSON_ROOT}")

# Assert för att hjälpa type checker
assert JSON_ROOT is not None

# ════════════════════════════════════════════════════════════════════
# Smart JSON-baserat System
# ════════════════════════════════════════════════════════════════════
def get_intention(street: str, action_label: str, j_score: float, 
                 invested: int, pot_before: int, debug: bool = False) -> str:
    """
    Smart intention från poker-kontext:
    1. Street + action_label → JSON-fil
    2. J_score → handstyrka (low/medium/high)  
    3. Invested/pot → storlek (small/medium/large)
    4. JSON mapping → intention
    """
    # Speciell hantering för check/call/fold
    if action_label.lower() in ['check', 'call', 'fold']:
        # Check behöver ingen intention
        if action_label.lower() == 'check':
            return "check"
        # Call och fold kan ha intentions baserat på handstyrka
        if action_label.lower() in ['call', 'fold']:
            # Kolla om JSON finns, annars använd enkel logik
            json_file = JSON_ROOT / street.lower() / f"{action_label.lower()}.json"
            if not json_file.exists():
                # Enkel fallback för call/fold
                if action_label.lower() == 'call':
                    if j_score > 66:
                        return "call-strong"
                    elif j_score > 33:
                        return "call-medium"
                    else:
                        return "call-weak"
                else:  # fold
                    if j_score > 66:
                        return "fold-strong"  # suspicious fold
                    elif j_score > 33:
                        return "fold-medium"
                    else:
                        return "fold-weak"
    
    # Steg 1: Ladda JSON för denna poker-situation
    json_file = JSON_ROOT / street.lower() / f"{action_label.lower()}.json"
    if not json_file.exists():
        if debug:
            print(f"⚠️  Ingen JSON: {json_file}")
        # Försök med generisk raise.json eller bet.json som fallback
        if "bet" in action_label.lower():
            fallback_file = JSON_ROOT / street.lower() / "raise.json"
            if fallback_file.exists():
                json_file = fallback_file
                if debug:
                    print(f"📎 Använder fallback: {fallback_file}")
            else:
                return f"{action_label}-unknown"
        else:
            return f"{action_label}-unknown"
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        if debug:
            print(f"❌ Fel vid läsning av {json_file}: {e}")
        return f"{action_label}-error"
    
    # Steg 2: Handstyrka från j_score
    if j_score <= 33:
        strength = "low"
    elif j_score <= 66:
        strength = "medium"
    else:
        strength = "high"
    
    # Steg 3: Storlek från ratio
    ratio = (invested or 0) / (pot_before or 1) if pot_before else 0
    
    # Matchar nu de 7 kategorierna från JSON-filerna:
    if ratio < 0.20:
        size = "tiny"
    elif ratio < 0.35:
        size = "small"
    elif ratio < 0.55:
        size = "medium"
    elif ratio < 0.85:
        size = "big"
    elif ratio < 1.10:
        size = "pot"
    elif ratio < 1.75:
        size = "over"
    else:
        size = "huge"
    
    # Script 6 använder fortfarande "small/medium/large" som gruppering
    # Mappa de 7 kategorierna till 3 grupper för bakåtkompatibilitet
    size_to_group = {
        "tiny": "small",
        "small": "small", 
        "medium": "medium",
        "big": "large",
        "pot": "large",
        "over": "large",
        "huge": "large"
    }
    size_group = size_to_group[size]
    
    if debug:
        print(f"🎯 {street}/{action_label}: j_score={j_score}→{strength}, "
              f"ratio={ratio:.2f}→{size} (group: {size_group})")
    
    # Steg 4: Hämta intention från JSON
    mappings = config.get("strength_mappings", {})
    
    # Försök först med detailed_mappings (7 kategorier)
    detailed_mappings = config.get("detailed_mappings", {})
    if strength in detailed_mappings and size in detailed_mappings[strength]:
        intention = detailed_mappings[strength][size]
        if intention:
            if debug:
                print(f"✅ detailed: {strength}×{size} → {intention}")
            return intention
    
    # Fallback till strength_mappings (3 grupper) för bakåtkompatibilitet
    if strength in mappings and size_group in mappings[strength]:
        intention = mappings[strength][size_group]
        if intention:
            if debug:
                print(f"✅ grouped: {strength}×{size_group} → {intention}")
            return intention
    
    # Fallback om mapping saknas
    fallback = f"{action_label}-{strength}-{size}"
    if debug:
        print(f"📎 Fallback: {fallback}")
    return fallback

def ensure_intention_column(con: sqlite3.Connection) -> None:
    """Säkerställer att intention-kolumnen finns."""
    cols = {c[1] for c in con.execute("PRAGMA table_info(actions)")}
    if "intention" not in cols:
        con.execute("ALTER TABLE actions ADD COLUMN intention TEXT")
        con.commit()
        print("➕ Lade till kolumn intention")

# ════════════════════════════════════════════════════════════════════
# Main Processing
# ════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Smart JSON Intention System")
    parser.add_argument("--debug", action="store_true", help="Debug output")
    parser.add_argument("--limit", type=int, help="Begränsa antal rader för testning")
    parser.add_argument("--reset", action="store_true", help="Återställ alla intentions (sätt till NULL)")
    args = parser.parse_args()

    # Öppna databas
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    ensure_intention_column(con)
    cur = con.cursor()

    # Om --reset flaggan är satt, återställ alla intentions
    if args.reset:
        cur.execute("UPDATE actions SET intention = NULL")
        con.commit()
        count = cur.rowcount
        print(f"🔄 Återställde {count:,} intentions till NULL")
        con.close()
        return

    # Hämta rader som behöver intentions - ta bort exkluderingen av check/call/fold
    sql = """
    SELECT rowid, hand_id, street, action_label, j_score,
           invested_this_action AS inv, pot_before AS pb
    FROM actions
    WHERE intention IS NULL 
      AND action_label IS NOT NULL 
      AND j_score IS NOT NULL
    ORDER BY hand_id, rowid
    """
    
    if args.limit:
        sql += f" LIMIT {args.limit}"
    
    rows = cur.execute(sql).fetchall()
    print(f"📊 Bearbetar {len(rows):,} actions med intentions...")

    # Bearbeta varje rad
    batch = []
    processed = 0
    stats = {}  # För att räkna olika action_labels

    for row in rows:
        action_label = row["action_label"]
        stats[action_label] = stats.get(action_label, 0) + 1
        
        intention = get_intention(
            street=row["street"],
            action_label=action_label, 
            j_score=row["j_score"],
            invested=row["inv"] or 0,
            pot_before=row["pb"] or 1,
            debug=args.debug
        )
        
        batch.append((intention, row["rowid"]))
        processed += 1
        
        # Batch commit varje 500:e rad
        if len(batch) >= 500:
            cur.executemany("UPDATE actions SET intention=? WHERE rowid=?", batch)
            con.commit()
            batch.clear()
            print(f"✓ {processed:,} intentions tillagda...")

    # Sista batchen
    if batch:
        cur.executemany("UPDATE actions SET intention=? WHERE rowid=?", batch)
        con.commit()

    # Visa statistik
    print("\n📈 Statistik över action_labels:")
    for label, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {label}: {count:,}")

    con.close()
    print(f"\n✅ Smart JSON Intention System klar: {processed:,} intentions tillagda")

if __name__ == "__main__":
    main()
