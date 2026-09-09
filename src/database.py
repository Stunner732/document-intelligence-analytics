"""Database connection and schema management utilities."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Any

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from src.config import settings


def get_connection_kwargs() -> dict[str, Any]:
    """Build connection kwargs from settings."""
    return {
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "dbname": settings.postgres_db,
        "user": settings.postgres_user,
        "password": settings.postgres_password,
    }


@contextmanager
def get_connection() -> Generator[Connection, None, None]:
    """Context manager for database connections."""
    conn = psycopg.connect(**get_connection_kwargs())
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def get_cursor() -> Generator[psycopg.Cursor, None, None]:
    """Context manager for database cursors."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            yield cur


def check_database_connection() -> bool:
    """Verify database connectivity."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT version();")
            _ = cur.fetchone()
        return True
    except Exception:
        return False


def get_schema_version() -> str | None:
    """Get the current applied schema version."""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT version FROM schema_versions ORDER BY applied_at DESC LIMIT 1")
            result = cur.fetchone()
            return result[0] if result else None
    except Exception:
        return None


def run_migrations(migrations_dir: Path) -> list[str]:
    """Run all pending SQL migrations in order."""
    if not migrations_dir.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    # Find and sort migration files
    migrations = sorted(migrations_dir.glob("*.sql"))
    applied_version = get_schema_version()

    applied_migrations: list[str] = []
    for migration in migrations:
        # Extract version from filename (e.g., "001_create_schema.sql" -> "001")
        version = migration.stem.split("_")[0]

        if applied_version and version <= applied_version:
            continue

        # Execute migration
        with get_cursor() as cur:
            cur.execute(migration.read_text(encoding="utf-8"))
            cur.connection.commit()

        applied_migrations.append(migration.name)

    return applied_migrations


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            );
            """,
            (table_name,),
        )
        return cur.fetchone()[0]


def get_table_row_count(table_name: str) -> int:
    """Get row count for a table."""
    with get_cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        return cur.fetchone()[0]


def list_tables() -> list[dict[str, Any]]:
    """List all tables in the database with row counts."""
    with get_cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            SELECT
                t.table_name,
                obj_description(t.table_name::regclass) as comment,
                (SELECT COUNT(*) FROM information_schema.columns c
                 WHERE c.table_name = t.table_name AND c.table_schema = 'public') as column_count
            FROM information_schema.tables t
            WHERE t.table_schema = 'public'
            AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name;
            """
        )
        return [dict(row) for row in cur.fetchall()]