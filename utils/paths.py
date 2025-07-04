#!/usr/bin/env python3
"""
Centraliserad path-hantering för både lokal utveckling och Render.com
"""
import os
from pathlib import Path

# Detektera om vi kör på Render
IS_RENDER = os.getenv("RENDER") == "true"

# Projektrot
if IS_RENDER:
    # På Render använder vi persistent disk
    DATA_ROOT = Path("/var/data")
    PROJECT_ROOT = Path("/opt/render/project/src")
else:
    # Lokalt använder vi projektmappen
    PROJECT_ROOT = Path(__file__).resolve().parents[1]  # prom/
    DATA_ROOT = PROJECT_ROOT / "local_data"

# Databas-paths
DB_DIR = DATA_ROOT / "database"
POKER_DB = DB_DIR / "poker.db"
HEAVY_DB = DB_DIR / "heavy_analysis.db"

# Logg-paths
LOG_DIR = DATA_ROOT / "logs"

# Arkiv-paths
ARCHIVE_DIR = DATA_ROOT / "archive"

# Skapa alla nödvändiga mappar
for directory in [DB_DIR, LOG_DIR, ARCHIVE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Skriv ut info vid import
if IS_RENDER:
    print(f"🚀 Kör på Render.com")
    print(f"   Data: {DATA_ROOT}")
else:
    print(f"💻 Kör lokalt")
    print(f"   Projekt: {PROJECT_ROOT}")
    print(f"   Data: {DATA_ROOT}") 