#!/usr/bin/env python3
"""
Backup databaser innan deploy (valfritt)
"""
import shutil
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent))
from utils.paths import POKER_DB, HEAVY_DB, IS_RENDER, ARCHIVE_DIR

def backup_databases():
    """Säkerhetskopierar databaser innan rensning"""
    if not IS_RENDER:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for db in [POKER_DB, HEAVY_DB]:
        if db.exists():
            backup_name = f"{db.stem}_{timestamp}{db.suffix}"
            backup_path = ARCHIVE_DIR / backup_name
            try:
                shutil.copy2(db, backup_path)
                print(f"   ✓ Backup: {backup_name}")
                
                # Behåll bara de 3 senaste backuperna
                backups = sorted(ARCHIVE_DIR.glob(f"{db.stem}_*{db.suffix}"))
                if len(backups) > 3:
                    for old_backup in backups[:-3]:
                        old_backup.unlink()
                        
            except Exception as e:
                print(f"   ⚠️  Backup misslyckades: {e}")

if __name__ == "__main__":
    backup_databases() 