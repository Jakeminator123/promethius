#!/usr/bin/env python3
# scrape.py – hämtar HH för STARTING_DATE och segmenterar direkt + kör processing-scripts

from __future__ import annotations
import os, re, json, sqlite3, sys, subprocess, argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Generator, List
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parents[1]))
from utils.paths import PROJECT_ROOT, POKER_DB, LOG_DIR, IS_RENDER

# ────────────────────────────────────────────────────────────────
# 0. projektrot + konstanter
# ────────────────────────────────────────────────────────────────
ROOT = PROJECT_ROOT                                  # Använd centraliserad path
DB_PATH = str(POKER_DB) if IS_RENDER else str(POKER_DB.relative_to(ROOT))

print(f"🏠 Projektrot: {ROOT}")
print(f"💾 Database: {POKER_DB}")

load_dotenv(ROOT / ".env")                           # laddar login-variabler

# ────────────────────────────────────────────────────────────────
# 1. config.txt
# ────────────────────────────────────────────────────────────────
def read_cfg(path: Path) -> dict[str, str]:
    kv = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip().upper()] = v.strip()
    return kv

CFG  = read_cfg(ROOT / "config.txt")
DATE = CFG["STARTING_DATE"]

# Skriv ut API-URL för transparens
API_URL = CFG["BASE_URL"]
print(f"🌐 API: {API_URL}")
print(f"   Organizer: {CFG['ORGANIZER']}")
print(f"   Event: {CFG['EVENT']}")
print()

# ────────────────────────────────────────────────────────────────
# 1b. Loggning setup
# ────────────────────────────────────────────────────────────────
# LOG_DIR skapas redan av utils.paths

# Skapa logger för dubbletter och fel
logger = logging.getLogger("hand_import")
logger.setLevel(logging.INFO)

# Filhanterare för loggar
log_file = LOG_DIR / f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.INFO)

# Format för loggmeddelanden
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Konsol-handler för viktig info
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

print(f"📝 Loggfil: {log_file}")
print()

# ────────────────────────────────────────────────────────────────
# 2. segmentering (från segment_hands.py)
# ────────────────────────────────────────────────────────────────
def ensure_schema(con: sqlite3.Connection):
    con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS hand_meta(
            id TEXT PRIMARY KEY,
            hand_date TEXT,
            is_cash INTEGER,
            is_mtt  INTEGER,
            blinds_bb REAL,
            pot_type TEXT,
            eff_stack_bb REAL,
            chip_bb REAL,
            has_partial_scores INTEGER
        );
        CREATE TABLE IF NOT EXISTS partial_scores(
            id   TEXT PRIMARY KEY,
            json TEXT,
            FOREIGN KEY(id) REFERENCES hands(id)
        );
    """)

def parse_blinds(s: str | None):
    if not s: return None
    hi = int(s.split("b")[-1])
    return hi / 100 if hi > 1_000_000 else float(hi)

def bulk_from_objects(con: sqlite3.Connection, hands: Iterable[dict]):
    ensure_schema(con)
    meta_rows, ps_rows = [], []
    for h in hands:
        meta_rows.append((
            h["stub"],
            h["stub"][:10],
            int(h.get("is_cash") or 0),
            int(h.get("is_mtt")  or 0),
            parse_blinds(h.get("blinds")),
            h.get("pot_type"),
            h.get("effective_stack"),
            h.get("chip_value_in_displayed_currency"),
            int(bool(h.get("partial_scores")))
        ))
        if h.get("partial_scores"):
            ps_rows.append((h["stub"], json.dumps(h["partial_scores"])))

    cur = con.cursor()
    if meta_rows:
        cur.executemany("INSERT OR IGNORE INTO hand_meta VALUES (?,?,?,?,?,?,?,?,?)", meta_rows)
    if ps_rows:
        cur.executemany("INSERT OR IGNORE INTO partial_scores VALUES (?,?)", ps_rows)
    con.commit()

# ────────────────────────────────────────────────────────────────
# 2b. Validering av hand histories
# ────────────────────────────────────────────────────────────────
def validate_hand(hand: dict) -> tuple[bool, str | None]:
    """Validerar en hand och returnerar (is_valid, error_message)."""
    try:
        # Kontrollera obligatoriska fält
        if not hand.get("stub"):
            return False, "Saknar hand ID (stub)"
        
        if not hand.get("blinds"):
            return False, "Saknar blinds-information"
        
        # Kontrollera att det är antingen cash eller MTT
        is_cash = hand.get("is_cash", False)
        is_mtt = hand.get("is_mtt", False)
        if not (is_cash or is_mtt):
            return False, "Varken cash game eller MTT"
        
        return True, None
        
    except Exception as e:
        return False, f"Valideringsfel: {str(e)}"

def check_duplicate(con: sqlite3.Connection, hand_id: str) -> bool:
    """Kontrollerar om en hand redan finns i databasen."""
    cur = con.cursor()
    cur.execute("SELECT 1 FROM hands WHERE id = ?", (hand_id,))
    return cur.fetchone() is not None

# ────────────────────────────────────────────────────────────────
# 3. script-runner
# ────────────────────────────────────────────────────────────────
def find_processing_scripts() -> List[Path]:
    """Hittar alla script 1_*.py, 2_*.py etc i scripts/-mappen."""
    scripts_dir = ROOT / "scrape_hh" / "scripts"
    if not scripts_dir.exists():
        return []
    
    scripts = []
    for i in range(1, 10):  # leta efter 1_*.py till 9_*.py
        pattern = f"{i}_*.py"
        matches = list(scripts_dir.glob(pattern))
        scripts.extend(matches)
    
    return sorted(scripts)

def run_processing_scripts(skip_scripts: List[str] = None) -> bool:
    """Kör alla processing-scripts i ordning. Returnerar True om alla lyckades."""
    skip_scripts = skip_scripts or []
    scripts = find_processing_scripts()
    
    if not scripts:
        print("⚠️  Inga processing-scripts hittades")
        return True
    
    print(f"🛠️  Kör {len(scripts)} processing-scripts...")
    success_count = 0
    
    for script in scripts:
        script_name = script.name
        if script_name in skip_scripts:
            print(f"   ⏭️  {script_name} (hoppas över)")
            continue
            
        print(f"   🔧 {script_name}...", end=" ", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, str(script)], 
                cwd=ROOT,
                capture_output=True, 
                text=True, 
                timeout=300  # 5 min timeout per script
            )
            
            if result.returncode == 0:
                print("✅")
                success_count += 1
            else:
                print(f"❌ (kod {result.returncode})")
                if result.stderr:
                    print(f"      Fel: {result.stderr.strip()}")
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ (timeout)")
            return False
        except Exception as e:
            print(f"❌ ({e})")
            return False
    
    print(f"   ✅ Alla {success_count} scripts klara")
    return True

# ────────────────────────────────────────────────────────────────
# 4. API-klient
# ────────────────────────────────────────────────────────────────
@dataclass
class Api:
    base: str
    organizer: str
    event: str
    limit: int = 50

    def __post_init__(self):
        self.s = requests.Session()
        self._login(
            os.getenv("BATTLE_API_USERNAME"),
            os.getenv("BATTLE_API_PASSWORD")
        )

    def _login(self, user: str, pwd: str):
        url = f"{self.base}/admin/login/?next=/admin/"
        token = re.search(r'name="csrfmiddlewaretoken" value="(.+?)"',
                          self.s.get(url, timeout=20).text).group(1)
        self.s.post(f"{self.base}/admin/login/", timeout=20,
                    data={"username": user, "password": pwd,
                          "csrfmiddlewaretoken": token, "next": "/admin/"},
                    headers={"Referer": url}).raise_for_status()

    def iter_hands(self, date: str) -> Generator[tuple[int, dict], None, None]:
        epi = f"Ep{date}"
        url = (f"{self.base}/v1/solver/power_ranking/organizers/{self.organizer}"
               f"/events/{self.event}/episodes/{epi}/hands"
               f"?limit={self.limit}&offset=0")
        
        # Skriv ut första URL för transparens  
        print(f"🔗 Hämtar från: {url}")
        print()
        
        while url:
            offset = int(re.search(r"offset=(\d+)", url).group(1))
            js = self.s.get(url, timeout=60).json()
            for i, h in enumerate(js["results"]):
                yield offset + i, h                  # seq = offset + pos
            url = js["next"]

# ────────────────────────────────────────────────────────────────
# 5. databas-access
# ────────────────────────────────────────────────────────────────
class Store:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(db_path)
        self.con.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS hands(
                id TEXT PRIMARY KEY,
                hand_date TEXT,
                seq INTEGER,
                raw_json TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_date ON hands(hand_date);
            CREATE INDEX IF NOT EXISTS idx_seq  ON hands(hand_date, seq);
        """)

    def insert_batch(self, rows: Iterable[tuple[str, str, int, str]]):
        self.con.executemany(
            "INSERT OR IGNORE INTO hands(id, hand_date, seq, raw_json)"
            " VALUES (?,?,?,?)",
            rows)
        self.con.commit()

# ────────────────────────────────────────────────────────────────
# 6. main-flöde med batch-processing
# ────────────────────────────────────────────────────────────────
def main() -> None:
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("date", nargs="?", default=DATE, help="YYYY-MM-DD")
    parser.add_argument("--url", help="Överskriv BASE_URL")
    parser.add_argument("--db", help="Överskriv DB-sökväg")
    parser.add_argument("--skip-scripts", nargs="*", default=[],
                       help="Script att hoppa över (t.ex. --skip-scripts 1_build_heavy_analysis.py 2_preflop_scores.py)")
    parser.add_argument("--no-scripts", action="store_true",
                       help="Hoppa över alla processing-scripts")
    args = parser.parse_args()
    
    # Setup från config
    date = args.date
    batch_size = int(CFG.get("BATCH_SIZE", 500))
    api = Api(
        args.url or CFG["BASE_URL"], 
        CFG["ORGANIZER"], 
        CFG["EVENT"],
        limit=int(CFG.get("BATCH_LIMIT", 50))
    )
    store = Store(ROOT / (args.db or DB_PATH))

    print(f"📥 Startar hämtning för {date}")
    print(f"   Batch-storlek: {batch_size} händer ({batch_size//50} sidor)")
    print(f"   Database: {DB_PATH}")
    if args.skip_scripts:
        print(f"   Hoppar över scripts: {', '.join(args.skip_scripts)}")
    if args.no_scripts:
        print(f"   Scripts: INAKTIVERADE")
    print()
    
    rows: List[tuple] = []
    objs: List[dict]  = []
    total_seen = 0
    batch_count = 0
    duplicates = 0
    invalid_hands = 0

    for seq, hand in api.iter_hands(date):
        hand_id = hand.get("stub", "")
        
        # Validera hand
        is_valid, error_msg = validate_hand(hand)
        if not is_valid:
            invalid_hands += 1
            logger.warning(f"Ogiltig hand {hand_id}: {error_msg}")
            continue
        
        # Kontrollera dublett
        if check_duplicate(store.con, hand_id):
            duplicates += 1
            logger.info(f"Dublett hittad: {hand_id}")
            continue
        
        rows.append((hand["stub"], date, seq, json.dumps(hand)))
        objs.append(hand)

        if len(rows) >= batch_size:
            batch_count += 1
            
            # Spara rådata + segmentera
            store.insert_batch(rows)
            bulk_from_objects(store.con, objs)
            total_seen += len(rows)
            
            print(f"📦 Batch {batch_count}: {len(rows)} händer → Totalt: {total_seen:,}")
            
            # Kör processing-scripts
            if not args.no_scripts:
                scripts_ok = run_processing_scripts(args.skip_scripts)
                if not scripts_ok:
                    print(f"❌ Scripts misslyckades i batch {batch_count} - avbryter")
                    return
            
            rows.clear(); objs.clear()
            print()  # Tom rad mellan batches

    # Hantera sista batch
    if rows:
        batch_count += 1
        
        store.insert_batch(rows)
        bulk_from_objects(store.con, objs)
        total_seen += len(rows)
        
        print(f"📦 Sista batch {batch_count}: {len(rows)} händer → Totalt: {total_seen:,}")
        
        if not args.no_scripts:
            scripts_ok = run_processing_scripts(args.skip_scripts)
            if not scripts_ok:
                print(f"❌ Scripts misslyckades i sista batch")
                return

    print(f"\n🎉 KLART! {total_seen:,} händer hämtade i {batch_count} batches")
    print(f"   Sparade i: {DB_PATH}")
    
    # Logga sammanfattning
    logger.info(f"Import slutförd för {date}: {total_seen} händer importerade, {duplicates} dubbletter, {invalid_hands} ogiltiga")
    
    if duplicates > 0:
        print(f"   ⚠️  {duplicates} dubbletter hoppades över")
    if invalid_hands > 0:
        print(f"   ❌ {invalid_hands} ogiltiga händer hoppades över")
    
    print(f"\n📊 Se loggfil för detaljer: {log_file.name}")

if __name__ == "__main__":
    main()
