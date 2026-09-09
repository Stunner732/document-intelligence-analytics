#!/usr/bin/env python3
"""Initialize database schema from SQL migrations."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import check_database_connection, run_migrations


def main():
    """Initialize database schema."""
    print("Checking database connection...")
    if not check_database_connection():
        print("Error: Cannot connect to database. Ensure PostgreSQL is running.")
        sys.exit(1)

    print("Connection successful.")

    migrations_dir = project_root / "sql"
    print(f"Running migrations from: {migrations_dir}")

    try:
        applied = run_migrations(migrations_dir)
        if applied:
            print("Applied migrations:")
            for migration in applied:
                print(f"  [OK] {migration}")
        else:
            print("No pending migrations.")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())