#!/usr/bin/env python3
"""Refresh Phase 5 materialized views.

This script refreshes all materialized views created in Phase 5 SQL Analytics.

Usage:
    python scripts/refresh_views.py

The script will:
1. Check if materialized views exist
2. Refresh each materialized view
3. Report refresh status for each view
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analytics.views import (
    get_all_materialized_views,
    materialized_view_exists,
    refresh_materialized_views,
)


def main():
    """Refresh all Phase 5 materialized views."""
    print("Phase 5 SQL Analytics - Materialized View Refresh")
    print("=" * 50)

    views = get_all_materialized_views()
    print(f"Found {len(views)} materialized views to check")

    # Check which views exist
    existing_views = []
    for view in views:
        if materialized_view_exists(view):
            existing_views.append(view)
            print(f"  [OK] {view}")
        else:
            print(f"  [MISSING] {view}")

    if not existing_views:
        print("\nNo materialized views found. Run the schema migration first:")
        print("  python scripts/init_database.py")
        return 1

    print(f"\nRefreshing {len(existing_views)} materialized views...")

    # Refresh views
    try:
        refreshed = refresh_materialized_views()
        print(f"\nRefreshed {len(refreshed)} materialized views:")
        for view in refreshed:
            print(f"  [OK] {view}")
        return 0
    except Exception as e:
        print(f"\nError during refresh: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())