#!/usr/bin/env python3
# main.py – central startpunkt som först rensar och sedan startar scraping

from __future__ import annotations
import argparse, sys, os, time, datetime, subprocess, multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import signal

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import PROJECT_ROOT, POKER_DB, IS_RENDER

# ── 1. Hitta projektroten och förbered import ──────────────────────────
ROOT = PROJECT_ROOT
DB_PATH = POKER_DB.relative_to(ROOT) if not IS_RENDER else POKER_DB

print(f"🏠 Projektrot: {ROOT}")
print(f"💾 Database: {POKER_DB}")

os.chdir(ROOT)
sys.path.append(str(ROOT / "scrape_hh"))

import scrape

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

def run_clean_start() -> bool:
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
                      skip_scripts: list = None, no_scripts: bool = False) -> None:
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
                     skip_scripts: list = None, no_scripts: bool = False) -> None:
    if not run_clean_start():
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return

    run_fetch_process(date_str, url, db, skip_scripts, no_scripts)

def run_loop(start_date: str, url: str | None, db: str | None,
             sleep_s: int = 300, max_workers: int = 1,
             skip_scripts: list = None, no_scripts: bool = False) -> None:
    if not run_clean_start():
        print("❌ Kan inte fortsätta utan lyckad rensning")
        return

    day = datetime.date.fromisoformat(start_date)

    def signal_handler(signum, frame):
        print(f"\n🛑 Fick signal {signum} - stänger av gracefully...")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    batch_size = CFG.get("BATCH_SIZE", "500")
    print(f"🔄 Startar loop från {start_date} med {max_workers} worker(s)")
    print(f"   Batch-storlek: {batch_size} händer per dag")

    while True:
        try:
            current_date = day.isoformat()

            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                future = executor.submit(run_fetch_process, current_date, url, db,
                                         skip_scripts, no_scripts)
                future.result()

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
ap.add_argument("--date", help="Startdatum (default = STARTING_DATE från config.txt)")
ap.add_argument("--url", help="Överskriv BASE_URL")
ap.add_argument("--db", help="Överskriv DB-sökväg")
ap.add_argument("--workers", type=int, default=1,
                help="Antal worker-processer (default: 1)")
ap.add_argument("--sleep", type=int, default=300,
                help="Sovtid i sekunder mellan körningar (default: 300)")
ap.add_argument("--skip-scripts", nargs="*", default=[],
                help="Script att hoppa över")
ap.add_argument("--no-scripts", action="store_true",
                help="Hoppa över alla processing-scripts")

args = ap.parse_args()

# ── 4. Kör vald handling ───────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 Startar automatisk scraping...")
    start = args.date or STARTING_DATE
    run_loop(start, args.url, args.db, args.sleep, args.workers,
             args.skip_scripts, args.no_scripts)
