#!/usr/bin/env python3
import os
import shutil
import sqlite3
from pathlib import Path
import sys

# Import centraliserad path-hantering
sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import PROJECT_ROOT, DATA_ROOT, POKER_DB, HEAVY_DB, IS_RENDER, DB_DIR

ROOT = PROJECT_ROOT

# Läs config.txt från projektroten
def parse_config(cfg_path: Path):
    keys = {"TO_ERASE_FILES": [], "TO_ERASE_FOLDERS": [], "TO_FLUSH": []}
    if cfg_path.exists():
        for line in cfg_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip().upper()
            if key in keys:
                keys[key] = [x.strip() for x in val.split(",") if x.strip()]
    return keys

# Flush-fil (töm)
def flush_file(path: Path):
    if path.suffix == ".db":
        try:
            with sqlite3.connect(path) as conn:
                tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                for (tbl,) in tables:
                    conn.execute(f"DELETE FROM {tbl}")
                conn.commit()
        except:
            pass
    else:
        path.write_bytes(b"")

def clean_specific_directory(directory: Path, patterns: list):
    """Rensar specifik mapp istället för hela projektträdet"""
    if not directory.exists():
        return
    
    for pattern in patterns:
        # Använd glob istället för rglob för att bara söka i denna mapp
        for file in directory.glob(pattern):
            if file.is_file():
                try:
                    file.unlink()
                    print(f"   ✓ Raderade {file.name}")
                except Exception as e:
                    print(f"   ⚠️  Kunde inte radera {file.name}: {e}")

if __name__ == "__main__":
    # På Render gör vi ingenting
    if IS_RENDER:
        print("🚀 Kör på Render - ingen rensning behövs")
        sys.exit(0)
    
    print("🧹 Startar lokal rensning...")
    
    config = parse_config(ROOT / "config.txt")
    
    # Fokusera på databas-mappen istället för hela projektet
    if config["TO_ERASE_FILES"]:
        # Databaser finns bara i DB_DIR
        db_patterns = [f for f in config["TO_ERASE_FILES"] if f.endswith(('.db', '.db-wal', '.db-shm'))]
        if db_patterns:
            print("📁 Rensar databasfiler...")
            clean_specific_directory(DB_DIR, db_patterns)
        
        # Andra filer (om några)
        other_patterns = [f for f in config["TO_ERASE_FILES"] if not f.endswith(('.db', '.db-wal', '.db-shm'))]
        if other_patterns:
            print("📁 Rensar andra filer...")
            for pattern in other_patterns:
                # Bara sök i root, inte rekursivt
                for file in ROOT.glob(pattern):
                    if file.is_file():
                        file.unlink(missing_ok=True)
    
    # Hantera mappar om de finns i config
    if config["TO_ERASE_FOLDERS"]:
        print("📁 Rensar mappar...")
        for folder in config["TO_ERASE_FOLDERS"]:
            folder_path = ROOT / folder
            if folder_path.exists() and folder_path.is_dir():
                shutil.rmtree(folder_path, ignore_errors=True)
                print(f"   ✓ Raderade {folder}")
    
    # Flush-filer (töm istället för radera)
    if config.get("TO_FLUSH"):
        print("📝 Tömmer filer...")
        for pattern in config["TO_FLUSH"]:
            for file in ROOT.glob(pattern):
                flush_file(file)
                print(f"   ✓ Tömde {file.name}")
    
    print("✅ Rensning klar!")