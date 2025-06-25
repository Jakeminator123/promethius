# queries/db_connection.py
import sqlite3
import os
from pathlib import Path
import logging

log = logging.getLogger(__name__)

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
        db_path = Path('/var/data') / db_name
        log.info(f"Using Render persistent disk database: {db_path}")
    else:
        # Lokalt: använd local_data/database
        db_path = Path(__file__).parent.parent / 'local_data' / 'database' / db_name
        log.info(f"Using local database: {db_path}")
    
    if not db_path.exists():
        log.warning(f"Database not found at {db_path}")
        
    return db_path

def get_connection(db_name: str = 'heavy_analysis.db') -> sqlite3.Connection:
    """
    Skapar och returnerar en databasanslutning
    
    Args:
        db_name: Namnet på databasen
        
    Returns:
        sqlite3.Connection: Databasanslutning
        
    Raises:
        Exception: Om databasen inte kan öppnas
    """
    db_path = get_db_path(db_name)
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Gör att vi kan accessa kolumner med namn
        return conn
    except Exception as e:
        log.error(f"Failed to connect to database {db_name}: {e}")
        raise

def execute_query(query: str, params: tuple = None, db_name: str = 'heavy_analysis.db') -> list:
    """
    Kör en SELECT-query och returnerar resultatet
    
    Args:
        query: SQL-query att köra
        params: Parametrar till queryn
        db_name: Databas att köra mot
        
    Returns:
        list: Lista med resultat
    """
    conn = None
    try:
        conn = get_connection(db_name)
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
            
        results = cursor.fetchall()
        return [dict(row) for row in results]
        
    except Exception as e:
        log.error(f"Query failed: {e}")
        raise
    finally:
        if conn:
            conn.close() 