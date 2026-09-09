#!/usr/bin/env python3
"""Load BPI Challenge 2017 XES data into PostgreSQL.

This script reads the XES file and populates the database tables.
"""

import gzip
import sys
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_cursor, check_database_connection


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _get_attribute_value(element: ET.Element, key: str) -> str:
    """Get a named attribute from an XES element."""
    for child in element:
        if _local_name(child.tag) in {"string", "date", "int", "float", "boolean", "id"}:
            if child.attrib.get("key") == key:
                return child.attrib.get("value", "")
    return ""


def load_application_attributes() -> list[str]:
    """Return the trace-level attributes to extract."""
    return [
        "concept:name",
        "ApplicationType",
        "LoanGoal",
        "RequestedAmount",
    ]


def load_event_attributes() -> list[str]:
    """Return the event-level attributes to extract."""
    return [
        "EventID",
        "concept:name",
        "time:timestamp",
        "org:resource",
        "EventOrigin",
        "lifecycle:transition",
        "Action",
        "case:concept:name",
    ]


def load_offers_attributes() -> list[str]:
    """Return offer-related attributes to extract from traces."""
    return [
        "OfferID",
        "OfferAmount",
        "OfferCost",
        "CreditScore",
        "InterestRate",
    ]


def main():
    """Load XES data into PostgreSQL."""
    source_path = project_root / "data" / "raw" / "BPI_Challenge_2017.xes.gz"

    if not source_path.exists():
        print(f"Error: Source file not found: {source_path}")
        return 1

    print(f"Checking database connection...")
    if not check_database_connection():
        print("Error: Cannot connect to database. Ensure PostgreSQL is running.")
        return 1

    print(f"Loading data from: {source_path}")

    application_attrs = load_application_attributes()
    event_attrs = load_event_attributes()
    offers_attrs = load_offers_attributes()

    application_count = 0
    event_count = 0

    with get_cursor() as cur:
        with gzip.open(source_path, "rb") as source:
            for _, element in ET.iterparse(source, events=("end",)):
                if _local_name(element.tag) != "trace":
                    continue

                # Extract trace-level attributes
                trace_attrs = {}
                for attr in application_attrs:
                    trace_attrs[attr] = _get_attribute_value(element, attr)

                application_id = trace_attrs["concept:name"].strip()
                if not application_id:
                    continue

                # Insert application
                cur.execute(
                    """
                    INSERT INTO applications (application_id, application_type, loan_goal, requested_amount)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (application_id) DO NOTHING;
                    """,
                    (
                        application_id,
                        _get_attribute_value(element, "ApplicationType"),
                        _get_attribute_value(element, "LoanGoal"),
                        float(_get_attribute_value(element, "RequestedAmount") or 0),
                    ),
                )
                application_count += 1

                # Process events
                timestamps = []
                for event in element:
                    if _local_name(event.tag) == "event":
                        event_id = _get_attribute_value(event, "EventID")
                        activity = _get_attribute_value(event, "concept:name")
                        timestamp_str = _get_attribute_value(event, "time:timestamp")
                        resource = _get_attribute_value(event, "org:resource")
                        event_origin = _get_attribute_value(event, "EventOrigin")
                        lifecycle = _get_attribute_value(event, "lifecycle:transition")
                        action = _get_attribute_value(event, "Action")

                        if not event_id:
                            continue

                        ts = _parse_timestamp(timestamp_str)
                        if ts:
                            timestamps.append(ts)

                        cur.execute(
                            """
                            INSERT INTO events (event_id, application_id, activity, event_timestamp,
                                              resource, lifecycle_transition, action, event_origin)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (event_id) DO NOTHING;
                            """,
                            (
                                event_id,
                                application_id,
                                activity,
                                ts,
                                resource,
                                lifecycle,
                                action,
                                event_origin,
                            ),
                        )
                        event_count += 1

                # Update application timestamps
                if timestamps:
                    cur.execute(
                        """
                        UPDATE applications
                        SET first_event_time = %s,
                            last_event_time = %s,
                            event_count = %s
                        WHERE application_id = %s;
                        """,
                        (
                            min(timestamps),
                            max(timestamps),
                            len(timestamps),
                            application_id,
                        ),
                    )

                element.clear()

            # Commit all changes
            cur.connection.commit()

    print(f"\nLoading complete:")
    print(f"  Applications: {application_count:,}")
    print(f"  Events: {event_count:,}")

    return 0


if __name__ == "__main__":
    sys.exit(main())