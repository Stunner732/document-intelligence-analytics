#!/usr/bin/env python3
"""Populate synthetic operational metadata into PostgreSQL database.

Reads all application IDs from the database, generates deterministic synthetic extensions,
executes transactional batch UPSERT into synthetic_extensions, and logs lineage in data_loads.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.cleaning.synthetic_generator import SyntheticExtensionGenerator, SyntheticExtensionRecord
from src.database import check_database_connection, get_connection


def populate_synthetic_extensions(seed: int = 42, batch_size: int = 1000, dry_run: bool = False) -> int:
    """Generate and load synthetic operational extension records into PostgreSQL.

    Args:
        seed: Random seed for deterministic generation.
        batch_size: Batch size for database UPSERT operations.
        dry_run: If True, validate generation without modifying database records.

    Returns:
        0 on success, 1 on failure.
    """
    if not check_database_connection():
        print("Error: Could not connect to PostgreSQL database.", file=sys.stderr)
        return 1

    print(f"Connecting to database to fetch application IDs (seed={seed}, batch_size={batch_size}, dry_run={dry_run})...")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT application_id FROM applications ORDER BY application_id;")
            rows = cur.fetchall()
            app_ids = [row[0] for row in rows]

    total_apps = len(app_ids)
    if total_apps == 0:
        print("Warning: No applications found in database.", file=sys.stderr)
        return 1

    print(f"Found {total_apps:,} applications in database.")

    generator = SyntheticExtensionGenerator(seed=seed)
    print("Generating synthetic extension records...")
    records = generator.generate_batch(app_ids)
    print(f"Successfully generated {len(records):,} synthetic extension records.")

    if dry_run:
        print("\n[DRY RUN SUMMARY]")
        print(f"  Records generated: {len(records):,}")
        print(f"  Seed: {seed}")
        print("  Sample Record:")
        if records:
            import json
            print(json.dumps(records[0].to_dict(include_lineage=True), indent=4))
        print("\nDry run completed cleanly. No database records were modified.")
        return 0

    started_at = datetime.now(timezone.utc)
    upsert_query = """
    INSERT INTO synthetic_extensions (
        application_id, document_type, page_count, branch, operator_team,
        priority, sla_target_hours, region, channel, quality_score,
        error_flag, rejection_flag, updated_at
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
    )
    ON CONFLICT (application_id) DO UPDATE SET
        document_type = EXCLUDED.document_type,
        page_count = EXCLUDED.page_count,
        branch = EXCLUDED.branch,
        operator_team = EXCLUDED.operator_team,
        priority = EXCLUDED.priority,
        sla_target_hours = EXCLUDED.sla_target_hours,
        region = EXCLUDED.region,
        channel = EXCLUDED.channel,
        quality_score = EXCLUDED.quality_score,
        error_flag = EXCLUDED.error_flag,
        rejection_flag = EXCLUDED.rejection_flag,
        updated_at = NOW();
    """

    print(f"Executing batch UPSERT into synthetic_extensions (batch_size={batch_size})...")
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Process in batches
            for i in range(0, total_apps, batch_size):
                batch_records = records[i : i + batch_size]
                batch_params = [
                    (
                        r.application_id,
                        r.document_type,
                        r.page_count,
                        r.branch,
                        r.operator_team,
                        r.priority,
                        r.sla_target_hours,
                        r.region,
                        r.channel,
                        r.quality_score,
                        r.error_flag,
                        r.rejection_flag,
                    )
                    for r in batch_records
                ]
                cur.executemany(upsert_query, batch_params)

            # Record audit lineage in data_loads
            audit_query = """
            INSERT INTO data_loads (
                source_file, load_type, records_loaded, load_status, started_at, completed_at
            ) VALUES (
                %s, %s, %s, %s, %s, NOW()
            );
            """
            cur.execute(
                audit_query,
                (
                    f"synthetic_generator_seed_{seed}",
                    "synthetic_extension",
                    total_apps,
                    "SUCCESS",
                    started_at,
                ),
            )

            conn.commit()

    print(f"\nPopulation Complete:")
    print(f"  Synthetic Extensions Populated: {total_apps:,}")
    print(f"  Seed Used: {seed}")
    print(f"  Audit Record Logged to data_loads: SUCCESS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate synthetic operational metadata into PostgreSQL.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic generator (default: 42).")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for UPSERT queries (default: 1000).")
    parser.add_argument("--dry-run", action="store_true", help="Validate generation without inserting database rows.")

    args = parser.parse_args()
    return populate_synthetic_extensions(seed=args.seed, batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
