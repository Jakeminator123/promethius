#!/usr/bin/env python3
"""
main.py - Central startpunkt för poker scraping system

Huvudfunktioner:
- Hanterar initial cleanup och setup
- Startar scraping-loop för kontinuerlig datainsamling  
- På Render: Kombinerar scraping med webserver
- Hanterar graceful shutdown och process-management
"""

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

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import PROJECT_ROOT, POKER_DB, IS_RENDER

# ────────────────────────────────────────────────────────────────
# Konfiguration och setup
# ────────────────────────────────────────────────────────────────

ROOT = PROJECT_ROOT
DB_PATH = POKER_DB.relative_to(ROOT) if not IS_RENDER else POKER_DB

print(f"🏠 Projektrot: {ROOT}")
print(f"💾 Database: {POKER_DB}")

os.chdir(ROOT)
from scrape_hh import scrape  # type: ignore[reportMissingImports]  # noqa: E402

def load_config() -> dict[str, str]:
    """Läser konfiguration från config.txt."""
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

# ────────────────────────────────────────────────────────────────
# Cleanup och process-hantering
# ────────────────────────────────────────────────────────────────

def kill_old_processes() -> None:
    """Försöker döda gamla Python-processer (endast för Render)."""
    if not IS_RENDER:
        return
    
    # psutil inte tillgängligt på Render - skulle kunna implementeras senare
    print("⏭️  Hoppar över process-cleanup (psutil inte tillgängligt)")

def cleanup_database_locks() -> None:
    """Rensar SQLite WAL/SHM-filer och stänger låsningar."""
    try:
        from utils.paths import POKER_DB, HEAVY_DB, DB_DIR
        
        print("🔍 Söker efter databas-filer...")
        
        # Sök efter databas-filer
        search_dirs = [DB_DIR]
        if IS_RENDER:
            search_dirs.append(Path('/var/data'))
        
        all_db_files = []
        patterns = ['poker.db*', 'heavy_analysis.db*']
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for pattern in patterns:
                    all_db_files.extend(search_dir.rglob(pattern))
        
        # Lägg till kända databas-filer
        known_db_files = [
            POKER_DB, HEAVY_DB,
            POKER_DB.with_suffix('.db-wal'), POKER_DB.with_suffix('.db-shm'),
            HEAVY_DB.with_suffix('.db-wal'), HEAVY_DB.with_suffix('.db-shm'),
        ]
        
        unique_db_files = list(set(known_db_files + all_db_files))
        
        print(f"   📁 Hittade {len(unique_db_files)} databas-filer")
        
        # Checkpoint aktiva databaser
        _checkpoint_databases(unique_db_files)
        
        # Radera WAL/SHM-filer
        _remove_lock_files(unique_db_files)
        
    except Exception as e:
        print(f"⚠️  Fel vid databas-rensning: {e}")

def _checkpoint_databases(db_files: list[Path]) -> None:
    """Gör WAL checkpoint på alla aktiva databaser."""
    for db_file in db_files:
        if db_file.suffix == '.db' and db_file.exists():
            try:
                conn = sqlite3.connect(str(db_file))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.close()
                print(f"   ✓ Checkpoint: {db_file.name}")
            except Exception as e:
                print(f"   ⚠️  Checkpoint misslyckades för {db_file.name}: {e}")

def _remove_lock_files(db_files: list[Path]) -> None:
    """Raderar WAL/SHM låsfiler."""
    removed_count = 0
    for db_file in db_files:
        if db_file.name.endswith(('.db-wal', '.db-shm')) and db_file.exists():
            try:
                db_file.unlink()
                print(f"   ✓ Raderade: {db_file.name}")
                removed_count += 1
            except Exception as e:
                print(f"   ⚠️  Kunde inte radera {db_file.name}: {e}")
    
    if removed_count > 0:
        print(f"✅ Rensade {removed_count} låsfiler")
    else:
        print("✅ Inga låsfiler att rensa")

def force_cleanup_on_start() -> None:
    """Tvångsmässig cleanup vid start (endast Render)."""
    if not IS_RENDER:
        return
        
    print("🧹 TVÅNGSRENSNING VID START (Render)")
    
    kill_old_processes()
    cleanup_database_locks()
    
    print("⏱️  Väntar 5 sekunder...")
    time.sleep(5)
    
    print("✅ Tvångsrensning klar")

def handle_first_deploy() -> bool:
    """Hanterar första deploy på Render med total databas-rensning."""
    from utils.paths import POKER_DB, HEAVY_DB, DB_DIR
    
    marker_file = DB_DIR / ".first_deploy_done"
    
    if marker_file.exists():
        print("♻️  Kontinuerlig drift - behåller befintlig data")
        try:
            deploy_time = marker_file.read_text().strip()
            print(f"   {deploy_time}")
        except Exception:
            pass
        return True
    
    print("🎉 FÖRSTA DEPLOYEN - total databas-rensning...")
    
    # Extra säkerhet
    kill_old_processes()
    cleanup_database_locks()
    
    # Hitta och radera alla databas-filer
    db_files_deleted = _delete_all_database_files()
    
    print(f"✅ Raderade {db_files_deleted} databas-filer")
    
    # Kör full rensning
    if not run_clean_start(skip_on_render=False):
        print("❌ KRITISK: Första rensning misslyckades")
        return False
    
    # Skapa marker
    marker_file.write_text(f"First deploy completed: {datetime.datetime.now().isoformat()}")
    print("✅ Första deployen klar")
    
    return True

def _delete_all_database_files() -> int:
    """Raderar alla databas-filer för fresh start."""
    from utils.paths import POKER_DB, HEAVY_DB, DB_DIR
    
    search_dirs = [DB_DIR]
    if IS_RENDER:
        search_dirs.append(Path('/var/data'))
    
    all_db_files = []
    patterns = ['poker.db*', 'heavy_analysis.db*']
    
    for search_dir in search_dirs:
        if search_dir.exists():
            for pattern in patterns:
                all_db_files.extend(search_dir.rglob(pattern))
    
    # Lägg till kända filer
    known_db_files = [
        POKER_DB, HEAVY_DB,
        POKER_DB.with_suffix('.db-wal'), POKER_DB.with_suffix('.db-shm'),
        HEAVY_DB.with_suffix('.db-wal'), HEAVY_DB.with_suffix('.db-shm'),
    ]
    
    unique_db_files = list(set(known_db_files + all_db_files))
    deleted_count = 0
    
    for db_file in unique_db_files:
        if db_file.exists():
            try:
                db_file.unlink()
                print(f"   ✓ Raderade {db_file.name}")
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠️  Kunde inte radera {db_file.name}: {e}")
    
    return deleted_count

# ────────────────────────────────────────────────────────────────
# Scraping-operationer
# ────────────────────────────────────────────────────────────────

def run_clean_start(skip_on_render: bool = True) -> bool:
    """Kör clean_start.py script för initial rensning."""
    if IS_RENDER and skip_on_render:
        print("🚀 På Render - hoppar över rensning")
        return True
        
    try:
        print("🧹 Kör rensning...")
        result = subprocess.run(
            [sys.executable, "clean_start.py"],
            cwd=ROOT, 
            capture_output=True, 
            text=True, 
            timeout=60
        )

        if result.returncode == 0:
            print("✅ Rensning klar")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Rensning misslyckades: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Rensning tog för lång tid")
        return False
    except Exception as e:
        print(f"❌ Fel vid rensning: {e}")
        return False

def run_fetch_process(
    date_str: str, 
    url: str | None, 
    db: str | None,
    skip_scripts: list[str] | None = None, 
    no_scripts: bool = False
) -> None:
    """Kör scraping för ett specifikt datum."""
    try:
        # Förbered arguments för scrape.py
        argv = ["scrape.py", date_str]
        
        if url:
            argv.extend(["--url", url])
        if db:
            argv.extend(["--db", db])
        if skip_scripts:
            argv.extend(["--skip-scripts"] + skip_scripts)
        if no_scripts:
            argv.append("--no-scripts")

        # Kör scrape.main() direkt istället för subprocess
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

def run_single_fetch(
    date_str: str, 
    url: str | None, 
    db: str | None,
    skip_scripts: list[str] | None = None, 
    no_scripts: bool = False
) -> None:
    """Kör scraping för ett enda datum med cleanup först."""
    if not run_clean_start():
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return

    run_fetch_process(date_str, url, db, skip_scripts, no_scripts)

def sleep_with_heartbeat(seconds: int, message: str = "Väntar...") -> None:
    """Sleep med periodisk loggning för att hålla processen vid liv på Render."""
    interval = 30  # Logga var 30:e sekund
    elapsed = 0
    
    while elapsed < seconds:
        remaining = seconds - elapsed
        sleep_time = min(interval, remaining)
        
        if elapsed > 0 and elapsed % 60 == 0:  # Logga varje minut
            print(f"   ⏱️  {message} ({elapsed//60} av {seconds//60} minuter)")
        
        time.sleep(sleep_time)
        elapsed += sleep_time

# ────────────────────────────────────────────────────────────────
# Signal handling
# ────────────────────────────────────────────────────────────────

def setup_signal_handlers() -> None:
    """Sätter upp signal handlers för graceful shutdown."""
    def signal_handler(signum: int, frame: Any) -> None:
        if IS_RENDER and signum == signal.SIGTERM:
            print("\n🛑 SIGTERM på Render - graceful shutdown...")
            
            try:
                cleanup_database_locks()
                print("✅ Databas-cleanup klar")
            except Exception:
                pass
            
            print("✅ Graceful shutdown klar")
            sys.exit(0)
        else:
            print(f"\n🛑 Signal {signum} - avslutar...")
            sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

# ────────────────────────────────────────────────────────────────
# Huvudloop
# ────────────────────────────────────────────────────────────────

def run_scraping_loop(
    start_date: str, 
    url: str | None, 
    db: str | None,
    sleep_s: int = 300,
    skip_scripts: list[str] | None = None, 
    no_scripts: bool = False,
    no_clean: bool = False, 
    in_thread: bool = False
) -> None:
    """Huvudloop för kontinuerlig scraping."""
    
    # Initial setup och cleanup
    if not _setup_initial_state(no_clean, in_thread):
        return
    
    # Setup signal handling (endast i main thread)
    if not in_thread:
        setup_signal_handlers()
    else:
        print("🔄 Scraping-thread: Hoppar över signal handling")

    # Börja scraping-loop
    day = datetime.date.fromisoformat(start_date)
    batch_size = CFG.get("BATCH_SIZE", "500")
    
    print(f"🔄 Startar scraping-loop från {start_date}")
    print(f"   Batch-storlek: {batch_size} händer per dag")

    while True:
        try:
            current_date = day.isoformat()
            
            print(f"🔄 Scraping för {current_date}...")
            run_fetch_process(current_date, url, db, skip_scripts, no_scripts)
            print(f"✅ Scraping klar för {current_date}")

            day += datetime.timedelta(days=1)
            
            # Olika väntetider beroende på om vi kommit ikapp dagens datum
            if day == datetime.date.today():
                print("🕑 Väntar 10 minuter (ikapp dagens datum)...")
                sleep_with_heartbeat(600, "Väntar innan nästa körning")
            else:
                print(f"🕑 Väntar {sleep_s//60} min...")
                next_date = day.isoformat()
                sleep_with_heartbeat(sleep_s, f"Väntar innan {next_date}")

        except KeyboardInterrupt:
            print("\n⏹️  Loop avbruten av användare")
            break
        except Exception as e:
            print(f"❌ Fel i loop för {day.isoformat()}: {e}")
            print(f"⏭️  Hoppar över och fortsätter...")
            day += datetime.timedelta(days=1)
            time.sleep(5)

def _setup_initial_state(no_clean: bool, in_thread: bool) -> bool:
    """Sätter upp initial state för scraping-loop."""
    if IS_RENDER and not no_clean:
        # Render: Hantera första deploy
        if not handle_first_deploy():
            print("❌ Första deploy misslyckades")
            return False
    elif not no_clean and not run_clean_start():
        # Lokal: Respektera --no-clean flaggan
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return False
    
    return True

# ────────────────────────────────────────────────────────────────
# Render-specifik webserver-hantering
# ────────────────────────────────────────────────────────────────

def start_render_environment(
    start_date: str,
    url: str | None,
    db: str | None, 
    sleep_s: int,
    skip_scripts: list[str],
    no_scripts: bool,
    no_clean: bool
) -> None:
    """Startar scraping + webserver för Render deployment."""
    
    def run_scraping_background() -> None:
        """Kör scraping i bakgrund."""
        print("🔄 Startar scraping i bakgrund...")
        time.sleep(15)  # Låt webservern starta först
        
        try:
            run_scraping_loop(
                start_date, url, db, sleep_s, skip_scripts, 
                no_scripts, no_clean, in_thread=True
            )
        except Exception as e:
            print(f"❌ KRITISKT FEL i scraping-tråd: {e}")
            import traceback
            traceback.print_exc()
            print("⚠️  Scraping-tråden dog! Webservern fortsätter köra men ingen ny data hämtas.")
    
    # Starta scraping i bakgrundsthread
    scraping_thread = threading.Thread(target=run_scraping_background, daemon=True)
    scraping_thread.start()
    print("✅ Scraping startad i bakgrund")
    
    # Skapa databaser om de inte finns
    _ensure_databases_exist()
    
    # Starta webserver som huvudprocess
    _start_webserver()

def _ensure_databases_exist() -> None:
    """Skapar tomma databaser om de inte finns."""
    try:
        from utils.paths import POKER_DB, HEAVY_DB
        
        for db_path in [POKER_DB, HEAVY_DB]:
            if not db_path.exists():
                print(f"📦 Skapar tom databas: {db_path.name}")
                db_path.parent.mkdir(parents=True, exist_ok=True)
                conn = sqlite3.connect(str(db_path))
                conn.close()
                
    except Exception as e:
        print(f"⚠️  Databas-skapande fel: {e}")

def _start_webserver() -> None:
    """Startar webserver som huvudprocess på Render."""
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🌐 Webserver som huvudprocess på port {port}")
    print(f"🔗 URL: https://promethius.onrender.com")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
        access_log=True
    )

# ────────────────────────────────────────────────────────────────
# CLI och main
# ────────────────────────────────────────────────────────────────

def create_argument_parser() -> argparse.ArgumentParser:
    """Skapar argument parser för CLI."""
    parser = argparse.ArgumentParser(
        description="Automatisk poker scraping system"
    )
    
    parser.add_argument("--date", help="Startdatum (default från config.txt)")
    parser.add_argument("--url", help="Överskriv BASE_URL")
    parser.add_argument("--db", help="Överskriv DB-sökväg")
    parser.add_argument("--workers", type=int, default=1,
                       help="Antal worker-processer (default: 1)")
    parser.add_argument("--sleep", type=int, default=300,
                       help="Sovtid mellan körningar i sekunder (default: 300)")
    parser.add_argument("--skip-scripts", nargs="*", default=[],
                       help="Script att hoppa över")
    parser.add_argument("--no-scripts", action="store_true",
                       help="Hoppa över alla processing-scripts")
    parser.add_argument("--no-clean", action="store_true",
                       help="Hoppa över initial rensning")
    
    return parser

def main() -> None:
    """Huvudfunktion som orchestrerar hela systemet."""
    print("🚀 Startar automatisk scraping...")
    
    # Tvångsmässig cleanup först (Render)
    force_cleanup_on_start()
    
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()
    
    start_date = args.date or STARTING_DATE
    
    if IS_RENDER:
        # Render: Scraping + webserver
        start_render_environment(
            start_date, args.url, args.db, args.sleep,
            args.skip_scripts, args.no_scripts, args.no_clean
        )
    else:
        # Lokal utveckling: Bara scraping
        run_scraping_loop(
            start_date, args.url, args.db, args.sleep,
            args.skip_scripts, args.no_scripts, args.no_clean,
            in_thread=False
        )

if __name__ == "__main__":
    main()
