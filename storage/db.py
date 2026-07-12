"""
Thin connection helper around psycopg3. Deliberately not an ORM —
the project has ~4 tables and the queries are simple enough that
SQLAlchemy would be more ceremony than value here.
"""
import os
import json
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dev@localhost:5432/postgres")


@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Run storage/schema.sql against the configured database. Safe to re-run (IF NOT EXISTS)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r") as f:
        ddl = f.read()
    with get_conn() as conn:
        conn.execute(ddl)


def dumps(obj) -> str:
    """Helper for writing JSONB columns."""
    return json.dumps(obj)
