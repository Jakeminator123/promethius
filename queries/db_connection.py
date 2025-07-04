# queries/db_connection.py
import sqlite3
import os
from pathlib import Path
import logging
from functools import lru_cache
import threading
from contextlib import contextmanager
from typing import Any, cast
import atexit

log = logging.getLogger(__name__)

# Thread-local storage för connections
_thread_local = threading.local()

# Cache för db paths (loggar bara första gången)
_db_paths_logged: set[str] = set()

@lru_cache(maxsize=4)
def get_db_path(db_name: str) -> Path:
    """
    Returnerar sökvägen till databasen, antingen lokalt eller på Render
    
    Args:
        db_name: Namnet på databasen (t.ex. 'heavy_analysis.db' eller 'poker.db')
    
    Returns:
        Path: Sökväg till databasen
    """
    # Kolla om vi kör på Render (persistent disk mounted på /var/data)
    if os.path.exists('/var/data'):
        # På Render lagras databaserna i undermappen "database" på persistent disken
        db_path = Path('/var/data') / 'database' / db_name
        # Logga bara första gången för varje databas
        if db_name not in _db_paths_logged:
            log.info(f"Using Render persistent disk database: {db_path}")
            _db_paths_logged.add(db_name)
    else:
        # Lokalt: använd local_data/database
        db_path = Path(__file__).parent.parent / 'local_data' / 'database' / db_name
        if db_name not in _db_paths_logged:
            log.info(f"Using local database: {db_path}")
            _db_paths_logged.add(db_name)
    
    if not db_path.exists():
        log.warning(f"Database not found at {db_path}")
        
    return db_path

def is_heavy_analysis_ready() -> bool:
    """
    Kontrollerar om heavy_analysis.db är redo att användas
    
    Returns:
        bool: True om databasen finns och har nödvändiga tabeller
    """
    try:
        db_path = get_db_path('heavy_analysis.db')
        if not db_path.exists():
            return False
            
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Kontrollera att actions-tabellen finns och har data
        cursor.execute("SELECT COUNT(*) FROM actions LIMIT 1")
        row_tmp = cursor.fetchone()
        count_row = cast(tuple[int], row_tmp) if row_tmp else None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dashboard_summary'")
        dash_exists = cursor.fetchone() is not None
        
        conn.close()
        return dash_exists and bool(count_row and count_row[0])
        
    except Exception as e:
        log.debug(f"Heavy analysis DB not ready: {e}")
        return False

def get_thread_connection(db_name: str = 'heavy_analysis.db') -> sqlite3.Connection:
    """
    Returnerar en thread-local connection (återanvänds inom samma tråd)
    """
    # Skapa en unik nyckel för varje databas
    conn_key = f"conn_{db_name}"
    
    # Om vi inte har en connection för denna databas i denna tråd, skapa en
    if not hasattr(_thread_local, conn_key) or getattr(_thread_local, conn_key) is None:
        db_path = get_db_path(db_name)
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Optimeringar för SQLite
            _ = conn.execute("PRAGMA journal_mode=WAL")
            _ = conn.execute("PRAGMA journal_size_limit=50000000")  # 50 MB
            _ = conn.execute("PRAGMA synchronous=NORMAL")
            _ = conn.execute("PRAGMA cache_size=10000")
            _ = conn.execute("PRAGMA temp_store=MEMORY")
            setattr(_thread_local, conn_key, conn)
        except Exception as e:
            log.error(f"Failed to create connection to {db_name}: {e}")
            raise
    
    return getattr(_thread_local, conn_key)

@contextmanager
def get_connection(db_name: str = 'heavy_analysis.db'):
    """
    Context manager för databaskoppling
    """
    conn = get_thread_connection(db_name)
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    # Vi stänger INTE connection här - den återanvänds

def execute_query(query: str, params: tuple[object, ...] = (), db_name: str = 'heavy_analysis.db') -> list[dict[str, Any]]:
    """
    Kör en SELECT-query och returnerar resultatet
    
    Args:
        query: SQL-query att köra
        params: Parametrar till queryn
        db_name: Databas att köra mot
        
    Returns:
        list: Lista med resultat
    """
    # För heavy_analysis.db, kontrollera om den är redo
    if db_name == 'heavy_analysis.db' and not is_heavy_analysis_ready():
        log.warning("Heavy analysis database not ready - returning empty results")
        return []
    
    try:
        with get_connection(db_name) as conn:
            cursor = conn.cursor()
            
            # Utför query
            _ = cursor.execute(query, params) if params else cursor.execute(query)

            result_rows = cast(list[sqlite3.Row], cursor.fetchall())
            results: list[dict[str, Any]] = [cast(dict[str, Any], dict(r)) for r in result_rows]
            return results
            
    except Exception as e:
        log.error(f"Query failed: {e}")
        raise

# ---------------------------------------------------------------------------
# Stäng alla öppna connections vid process-exit (t.ex. vid Uvicorn reload)
# ---------------------------------------------------------------------------

@atexit.register
def _close_thread_connections() -> None:
    for attr, maybe_conn in _thread_local.__dict__.items():
        if isinstance(maybe_conn, sqlite3.Connection):
            try:
                maybe_conn.close()
            except Exception:
                pass 