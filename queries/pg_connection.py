import os
from functools import lru_cache
from typing import Any, Sequence, Mapping

import psycopg
from psycopg.rows import dict_row

DSN_ENV = "PG_DSN"

@lru_cache(maxsize=1)
def _dsn() -> str:
    dsn = os.getenv(DSN_ENV)
    if not dsn:
        raise RuntimeError(f"Miljövariabeln {DSN_ENV} saknas – kan inte ansluta till Postgres")
    return dsn

# En enkel connection-pool (1⇢4 anslutningar räcker för Uvicorn-worker).
_pool: psycopg.Connection | None = None

def get_conn() -> psycopg.Connection:
    global _pool  # noqa: PLW0603
    if _pool is None or _pool.closed:
        _pool = psycopg.connect(_dsn(), autocommit=True, row_factory=dict_row)  # type: ignore[arg-type]
    return _pool

def fetchall(sql: str, params: Sequence[Any] | Mapping[str, Any] | None = None):
    """Kör SELECT och returnerar lista med dict-rader."""
    with get_conn().cursor() as cur:
        cur.execute(sql, params or ())  # type: ignore[arg-type]
        return cur.fetchall()

__all__ = ["get_conn", "fetchall"] 