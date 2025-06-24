#!/usr/bin/env python3
# main.py – central startpunkt som först rensar och sedan startar scraping
# På Render startar också webservern för att ha allt i en robust process

from __future__ import annotations
import argparse
import sys
import os
import time
import datetime
import subprocess
import sqlite3
from pathlib import Path
import signal
import threading
from typing import Any
import psutil  # För process-hantering
import socket

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import PROJECT_ROOT, POKER_DB, IS_RENDER

# ── 1. Hitta projektroten och förbered import ──────────────────────────
ROOT = PROJECT_ROOT
DB_PATH = POKER_DB.relative_to(ROOT) if not IS_RENDER else POKER_DB

print(f"🏠 Projektrot: {ROOT}")
print(f"💾 Database: {POKER_DB}")

# ── CLEANUP-FUNKTIONER ──────────────────────────────────────────────────
def kill_old_processes():
    """Dödär gamla Python-processer som kör scraping/webserver"""
    if not IS_RENDER:
        return  # Bara på Render
        
    try:
        current_pid = os.getpid()
        killed_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Skippa vår egen process
                if proc.info['pid'] == current_pid:
                    continue
                    
                # Leta efter andra Python-processer som kör våra scripts
                if (proc.info['name'] in ['python', 'python3', 'python.exe'] and 
                    proc.info['cmdline'] and 
                    any('main.py' in str(cmd) or 'scrape.py' in str(cmd) or 'app.py' in str(cmd) 
                        for cmd in proc.info['cmdline'])):
                    
                    print(f"🔪 Dödär gammal process: PID {proc.info['pid']} - {' '.join(proc.info['cmdline'][:3])}")
                    proc.terminate()
                    killed_count += 1
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        if killed_count > 0:
            print(f"✅ Dödade {killed_count} gamla processer")
            time.sleep(2)  # Vänta så processer hinner dö
        else:
            print("✅ Inga gamla processer att döda")
            
    except Exception as e:
        print(f"⚠️  Kunde inte döda gamla processer: {e}")

def cleanup_database_locks():
    """Rensar SQLite WAL/SHM-filer och stänger låsningar - HITTAR ALLA DATABASER"""
    try:
        from utils.paths import POKER_DB, HEAVY_DB, DB_DIR
        
        print("🔍 Söker efter ALLA databas-filer rekursivt...")
        
        # Lista över alla databas-relaterade filer (kända paths)
        known_db_files = [
            POKER_DB,
            HEAVY_DB,
            POKER_DB.with_suffix('.db-wal'),
            POKER_DB.with_suffix('.db-shm'), 
            HEAVY_DB.with_suffix('.db-wal'),
            HEAVY_DB.with_suffix('.db-shm'),
        ]
        
        # Sök rekursivt efter ALLA databas-filer i hela data-området
        search_dirs = [DB_DIR]
        if IS_RENDER:
            search_dirs.append(Path('/var/data'))
        
        all_db_files = []
        for search_dir in search_dirs:
            if search_dir.exists():
                # Hitta alla filer som matchar våra databas-namn
                patterns = ['poker.db*', 'heavy_analysis.db*']
                for pattern in patterns:
                    all_db_files.extend(search_dir.rglob(pattern))
        
        # Kombinera kända + hittade filer
        unique_db_files = list(set(known_db_files + all_db_files))
        
        print(f"   📁 Hittade {len(unique_db_files)} databas-relaterade filer")
        for db_file in unique_db_files:
            if db_file.exists():
                print(f"      • {db_file}")
        
        # Försök stänga alla SQLite-connections först (bara .db-filer)
        for db_file in unique_db_files:
            if db_file.suffix == '.db' and db_file.exists():
                try:
                    # Öppna kort connection för att trigga WAL checkpoint
                    conn = sqlite3.connect(str(db_file))
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    conn.close()
                    print(f"   ✓ Checkpoint: {db_file.name}")
                except Exception as e:
                    print(f"   ⚠️  Checkpoint misslyckades för {db_file.name}: {e}")
        
        # Radera WAL/SHM-filer som kan vara låsta
        removed_count = 0
        for db_file in unique_db_files:
            if db_file.name.endswith(('.db-wal', '.db-shm')) and db_file.exists():
                try:
                    db_file.unlink()
                    print(f"   ✓ Raderade låst fil: {db_file}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ⚠️  Kunde inte radera {db_file}: {e}")
        
        if removed_count > 0:
            print(f"✅ Rensade {removed_count} låsta databas-filer")
        else:
            print("✅ Inga låsta databas-filer att rensa")
            
    except Exception as e:
        print(f"⚠️  Fel vid databas-rensning: {e}")

def force_cleanup_on_start():
    """Tvångsmässig cleanup vid start - dödär allt som kan störa"""
    if not IS_RENDER:
        return
        
    print("🧹 TVÅNGSRENSNING VID START (Render)")
    
    # 1. Döda gamla processer först
    kill_old_processes()
    
    # 2. Rensa databas-låsningar
    cleanup_database_locks()
    
    # 3. Extra väntetid för att allt ska hinna "sätta sig"
    print("⏱️  Väntar 5 sekunder så allt hinner rensas...")
    time.sleep(5)
    
    print("✅ Tvångsrensning klar - fortsätter med normal start")

os.chdir(ROOT)
from scrape_hh import scrape  # type: ignore[reportMissingImports]  # noqa: E402

# ── 2. Hjälpfunktioner ──────────────────────────────────────────────────
def load_config() -> dict[str, str]:
    kv: dict[str, str] = {}
    with open(ROOT / "config.txt", encoding="utf-8") as fh:
        for line in fh:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                kv[k.strip().upper()] = v.strip()
    return kv

CFG = load_config()
STARTING_DATE = CFG["STARTING_DATE"]

print(f"🌐 API: {CFG['BASE_URL']}")
print(f"   Organizer: {CFG['ORGANIZER']}")
print(f"   Event: {CFG['EVENT']}")
print()

def run_clean_start(skip_on_render: bool = True) -> bool:
    # På Render, skippa rensning om inte explicit begärt
    if IS_RENDER and skip_on_render:
        print("🚀 På Render - hoppar över rensning (använd skip_on_render=False för att tvinga)")
        return True
        
    try:
        print("🧹 Kör rensning...")
        result = subprocess.run([sys.executable, "clean_start.py"],
                                cwd=ROOT, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            print("✅ Rensning klar")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Rensning misslyckades: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("⏰ Rensning tog för lång tid - avbryter")
        return False
    except Exception as e:
        print(f"❌ Fel vid rensning: {e}")
        return False

def run_fetch_process(date_str: str, url: str | None, db: str | None,
                      skip_scripts: list[str] | None = None, no_scripts: bool = False) -> None:
    try:
        argv = ["scrape.py", date_str]
        if url:
            argv += ["--url", url]
        if db:
            argv += ["--db", db]
        if skip_scripts:
            argv += ["--skip-scripts"] + skip_scripts
        if no_scripts:
            argv += ["--no-scripts"]

        original_argv = sys.argv[:]
        sys.argv = argv

        scrape.main()

        sys.argv = original_argv

    except KeyboardInterrupt:
        print(f"\n⏹️  Scraping avbrutet för {date_str}")
        raise
    except Exception as e:
        print(f"❌ Fel vid scraping för {date_str}: {e}")
        raise

def run_single_fetch(date_str: str, url: str | None, db: str | None,
                     skip_scripts: list[str] | None = None, no_scripts: bool = False) -> None:
    if not run_clean_start():
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return

    run_fetch_process(date_str, url, db, skip_scripts, no_scripts)

def run_loop(start_date: str, url: str | None, db: str | None,
             sleep_s: int = 300, max_workers: int = 1,
             skip_scripts: list[str] | None = None, no_scripts: bool = False,
             no_clean: bool = False, in_thread: bool = False) -> None:
    # Smart första-deploy-detektion på Render
    if IS_RENDER and not no_clean:
        from utils.paths import POKER_DB, HEAVY_DB, DB_DIR
        
        # Marker-fil för att veta om första deployen är gjord
        marker_file = DB_DIR / ".first_deploy_done"
        
        if not marker_file.exists():
            print("🎉 FÖRSTA DEPLOYEN - rensar alla databaser för fresh start...")
            
            # Extra säkerhet: Döda alla processer och rensa låsningar
            kill_old_processes()
            cleanup_database_locks()
            
            # Hitta ALLA databas-filer rekursivt för total rensning
            print("🔍 Söker efter ALLA databas-filer för total rensning...")
            search_dirs = [DB_DIR]
            if IS_RENDER:
                search_dirs.append(Path('/var/data'))
            
            all_db_files = []
            for search_dir in search_dirs:
                if search_dir.exists():
                    # Hitta alla filer som matchar våra databas-namn
                    patterns = ['poker.db*', 'heavy_analysis.db*']
                    for pattern in patterns:
                        all_db_files.extend(search_dir.rglob(pattern))
            
            # Lägg till kända filer också
            known_db_files = [
                POKER_DB,
                HEAVY_DB,
                POKER_DB.with_suffix('.db-wal'),
                POKER_DB.with_suffix('.db-shm'),
                HEAVY_DB.with_suffix('.db-wal'),
                HEAVY_DB.with_suffix('.db-shm'),
            ]
            
            unique_db_files = list(set(known_db_files + all_db_files))
            
            print(f"   📁 Hittade {len(unique_db_files)} databas-filer att radera")
            
            deleted_count = 0
            for db_file in unique_db_files:
                if db_file.exists():
                    try:
                        db_file.unlink()
                        print(f"   ✓ Raderade {db_file}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ⚠️  Kunde inte radera {db_file}: {e}")
            
            print(f"✅ Raderade {deleted_count} databas-filer totalt")
            
            # Kör full rensning
            if not run_clean_start(skip_on_render=False):
                print("❌ Kritisk: Kan inte starta utan lyckad första rensning")
                sys.exit(1)
            
            # Skapa marker-fil så vi vet att första deployen är gjord
            marker_file.write_text(f"First deploy completed: {datetime.datetime.now().isoformat()}")
            print("✅ Första deployen klar - framtida restarts behåller data")
            
        else:
            print("♻️  Inte första deployen - behåller befintlig data (kontinuerlig drift)")
            # Läs när första deployen gjordes
            try:
                deploy_time = marker_file.read_text().strip()
                print(f"   {deploy_time}")
            except:
                pass
    elif not no_clean and not run_clean_start():
        # Lokal miljö - respektera --no-clean flaggan
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return

    day = datetime.date.fromisoformat(start_date)

    # Signal handling bara i main thread, inte i scraping thread
    if not in_thread:
        def signal_handler(signum: int, frame: Any) -> None:
            if IS_RENDER and signum == signal.SIGTERM:
                # På Render: Gör ordentlig cleanup innan vi avslutar
                print(f"\n🛑 Fick SIGTERM på Render - gör ordentlig cleanup...")
                
                try:
                    # Stäng databas-connections
                    cleanup_database_locks()
                    print("✅ Databas-cleanup klar")
                except:
                    pass
                
                print("✅ Graceful shutdown klar - avslutar")
                sys.exit(0)
            elif signum == signal.SIGTERM:
                print(f"\n🛑 Fick SIGTERM - avslutar...")
                sys.exit(0)
            else:
                print(f"\n🛑 Fick signal {signum} - stänger av gracefully...")
                sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    else:
        print("🔄 Scraping-thread: Hoppar över signal handling (bara main thread)")

    batch_size = CFG.get("BATCH_SIZE", "500")
    print(f"🔄 Startar loop från {start_date}")
    print(f"   Batch-storlek: {batch_size} händer per dag")

    while True:
        try:
            current_date = day.isoformat()

            # Kör scraping synkront för att undvika extra processfork och sänka CPU-toppar
            print(f"🔄 Startar scraping för {current_date}...")
            run_fetch_process(current_date, url, db, skip_scripts, no_scripts)
            print(f"✅ Scraping klar för {current_date}")

            day += datetime.timedelta(days=1)

            if day == datetime.date.today():
                print("🕑 Väntar 10 minuter innan nästa körning...")
                time.sleep(600)
            else:
                print(f"🕑 Väntar {sleep_s//60} min innan nästa körning...")
                time.sleep(sleep_s)

        except KeyboardInterrupt:
            print("\n⏹️  Loop avbruten av användare")
            break
        except Exception as e:
            print(f"❌ Fel i loop: {e}")
            print(f"⏭️  Hoppar över {day.isoformat()} och fortsätter...")
            day += datetime.timedelta(days=1)
            time.sleep(5)

# ── 3. CLI-parse ───────────────────────────────────────────────────
ap = argparse.ArgumentParser(
    description="Automatisk poker scraping system"
)
_ = ap.add_argument("--date", help="Startdatum (default = STARTING_DATE från config.txt)")
_ = ap.add_argument("--url", help="Överskriv BASE_URL")
_ = ap.add_argument("--db", help="Överskriv DB-sökväg")
_ = ap.add_argument("--workers", type=int, default=1,
                    help="Antal worker-processer (default: 1)")
_ = ap.add_argument("--sleep", type=int, default=300,
                    help="Sovtid i sekunder mellan körningar (default: 300)")
_ = ap.add_argument("--skip-scripts", nargs="*", default=[],
                    help="Script att hoppa över")
_ = ap.add_argument("--no-scripts", action="store_true",
                    help="Hoppa över alla processing-scripts")
_ = ap.add_argument("--no-clean", action="store_true",
                    help="Hoppa över rensning (rekommenderat på Render)")

args = ap.parse_args()

# ── 4. Kör vald handling ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Startar automatisk scraping...")
    
    # TVÅNGSMÄSSIG CLEANUP FÖRST (på Render)
    force_cleanup_on_start()
    
    # På Render, starta scraping i bakgrund och webserver som huvudprocess
    if IS_RENDER:
        # Scraping i bakgrundsprocess istället för webserver i thread
        def run_scraping_background():
            """Kör scraping i bakgrundsprocess"""
            print("🔄 Startar scraping i bakgrundsprocess...")
            time.sleep(15)  # Vänta så webservern hinner starta först
            
            start = args.date or STARTING_DATE
            run_loop(
                start, 
                args.url, 
                args.db, 
                args.sleep, 
                args.workers,
                args.skip_scripts, 
                args.no_scripts, 
                args.no_clean,
                in_thread=True  # Viktigt: Säg att detta körs i thread!
            )
        
        # Starta scraping i bakgrund
        import threading
        scraping_thread = threading.Thread(target=run_scraping_background, daemon=True)
        scraping_thread.start()
        print("✅ Scraping startad i bakgrund")
        
        # Webserver som HUVUDPROCESS (det som Render övvakar)
        print("🌐 Startar webserver som huvudprocess...")
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        
        # Skapa databaser först
        try:
            from utils.paths import POKER_DB, HEAVY_DB
            import sqlite3
            
            for db_path in [POKER_DB, HEAVY_DB]:
                if not db_path.exists():
                    print(f"📦 Skapar tom databas: {db_path}")
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    conn = sqlite3.connect(str(db_path))
                    conn.close()
        except Exception as e:
            print(f"⚠️  Databas-skapande fel: {e}")
        
        print(f"🌐 Webserver kör som huvudprocess på port {port}")
        print(f"🔗 URL: https://promethius.onrender.com")
        
        # KÖR WEBSERVER SOM HUVUDPROCESS - inget threading!
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info",
            access_log=True
        )
    else:
        # Lokal utveckling - kör scraping direkt
        start = args.date or STARTING_DATE
        run_loop(
            start, 
            args.url, 
            args.db, 
            args.sleep, 
            args.workers,
            args.skip_scripts, 
            args.no_scripts, 
            args.no_clean,
            in_thread=False
        )
