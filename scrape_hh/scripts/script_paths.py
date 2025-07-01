#!/usr/bin/env python3
"""
Gemensam path-hantering för alla processing-scripts.
Fungerar både lokalt och på Render.com.
"""
import sys
from pathlib import Path

# Lägg till utils i path
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Import från centraliserad path-hantering
from utils.paths import PROJECT_ROOT, POKER_DB, HEAVY_DB, IS_RENDER

# För bakåtkompatibilitet - scripts förväntar sig dessa variabler
ROOT = PROJECT_ROOT
SRC_DB = POKER_DB
DST_DB = HEAVY_DB
OUT_DB = HEAVY_DB  # Alias som vissa scripts använder

# Läs config.txt
CFG = {}
config_file = ROOT / "config.txt"
if config_file.exists():
    for line in config_file.read_text().splitlines():
        if "=" in line:
            k, v = line.strip().split("=", 1)
            CFG[k.strip().upper()] = v.strip()

# Ranges databas
RANGES_DB = ROOT / CFG.get("RANGES_PATH", "utils/trees_db/cash/poker_ranges.db")

# För scripts som använder SQLITE dict
SQLITE = {
    "HANDS": SRC_DB,
    "RANGES": RANGES_DB,
    "OUT": OUT_DB,
}

# Debug info
if __name__ == "__main__":
    print(f"ROOT: {ROOT}")
    print(f"SRC_DB: {SRC_DB}")
    print(f"DST_DB: {DST_DB}")
    print(f"RANGES_DB: {RANGES_DB}")
    print(f"IS_RENDER: {IS_RENDER}") 