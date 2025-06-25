#!/usr/bin/env python3
import os
import shutil
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

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

if __name__ == "__main__":
    config = parse_config(ROOT / "config.txt")

    for pattern in config["TO_ERASE_FILES"]:
        for file in ROOT.rglob(pattern):
            file.unlink(missing_ok=True)

    for folder in config["TO_ERASE_FOLDERS"]:
        for dir in ROOT.rglob(folder):
            if dir.is_dir():
                shutil.rmtree(dir, ignore_errors=True)

    for pattern in config["TO_FLUSH"]:
        for file in ROOT.rglob(pattern):
            flush_file(file)

    print("Rensning klar.")