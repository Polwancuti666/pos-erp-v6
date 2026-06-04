"""Database connection pool for PostgreSQL."""
from __future__ import annotations
import os
import psycopg
from psycopg.rows import dict_row
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

# Build URL from individual env vars
_pg_user = os.getenv("POSTGRES_USER", "sa")
_pg_pw = os.getenv("POSTGRES_PASSWORD", "")
_pg_host = os.getenv("POSTGRES_HOST", "localhost")
_pg_port = os.getenv("POSTGRES_PORT", "5432")
_pg_db = os.getenv("POSTGRES_DB", "pos_erp")

DATABASE_URL = os.getenv(
    "POS_ERP_DATABASE_URL",
    f"postgresql://{_pg_user}:{_pg_pw}@{_pg_host}:{_pg_port}/{_pg_db}"
)

_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg.conninfo.make_conninfo(DATABASE_URL)
    return _pool

@contextmanager
def get_conn():
    """Get a database connection."""
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, options='-c timezone=Asia/Jakarta')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def fetch_all(query: str, params: tuple = ()) -> list[dict]:
    """Execute query and return all rows."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def fetch_one(query: str, params: tuple = ()) -> dict | None:
    """Execute query and return one row."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

def execute(query: str, params: tuple = ()) -> int:
    """Execute query and return rowcount."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.rowcount

def execute_returning(query: str, params: tuple = ()) -> dict | None:
    """Execute query and return the inserted/updated row."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()
