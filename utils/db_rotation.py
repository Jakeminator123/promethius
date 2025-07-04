"""db_rotation.py – verktyg för att arkivera dagliga databaser.
"""
from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Tuple

from utils.paths import POKER_DB, HEAVY_DB, ARCHIVE_DIR

__all__ = [
    "archive_subdir",
    "rotate_databases",
    "get_db_paths_for_date",
]


def archive_subdir(date_str: str) -> Path:
    """Returnerar (och skapar) undermapp i ARCHIVE_DIR för givet datum."""
    d = ARCHIVE_DIR / date_str
    d.mkdir(parents=True, exist_ok=True)
    return d


def rotate_databases(date_str: str) -> None:
    """Flytta dagens *.db till arkivmapp och initiera nya tomma filer.

    Parametrar
    ----------
    date_str : str
        ISO-datumet (YYYY-MM-DD) som precis färdigbehandlats.
    """
    dst_dir = archive_subdir(date_str)

    for db_path in (POKER_DB, HEAVY_DB):
        try:
            if db_path.exists():
                target = dst_dir / db_path.name
                # Om det redan finns en fil för detta datum – skippa för att inte skriva över.
                if not target.exists():
                    shutil.move(str(db_path), str(target))
                # Skapa ny tom databas för kommande dag
                sqlite3.connect(str(db_path)).close()
        except Exception as e:
            # Logga bara; vi vill inte krascha scraping-loopen
            print(f"⚠️  rotate_databases: kunde inte rotera {db_path}: {e}")


def get_db_paths_for_date(date_str: str) -> Tuple[Path, Path]:
    """Returnerar (poker_db_path, heavy_db_path) för givet datum.
    Om arkivfiler saknas faller vi tillbaka till live-databasen.
    """
    sub = ARCHIVE_DIR / date_str
    p_db = sub / POKER_DB.name
    h_db = sub / HEAVY_DB.name

    poker_path = p_db if p_db.exists() else POKER_DB
    heavy_path = h_db if h_db.exists() else HEAVY_DB
    return poker_path, heavy_path 