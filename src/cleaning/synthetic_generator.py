"""Deterministic synthetic operational metadata generator for BPI Challenge applications.

Generates reproducible, seed-controlled synthetic extension records for loan application
cases while enforcing schema constraints and preserving isolation from database logic.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass
from typing import Any, Iterable, Sequence

SLA_TARGET_HOURS: dict[str, int] = {
    "urgent": 12,
    "high": 24,
    "normal": 48,
    "low": 72,
}

PRIORITY_LEVELS: tuple[str, ...] = ("low", "normal", "high", "urgent")

DOCUMENT_TYPES: tuple[str, ...] = (
    "Mortgage Application",
    "Personal Loan Request",
    "Proof of Income",
    "Identity Verification",
    "Tax Return",
)

BRANCHES: tuple[str, ...] = (
    "Branch North",
    "Branch South",
    "Branch East",
    "Branch West",
    "Branch Central",
    "Branch Metro",
    "Branch Regional",
    "Branch Harbour",
    "Branch Valley",
    "Branch Highland",
)

OPERATOR_TEAMS: tuple[str, ...] = (
    "Team Alpha",
    "Team Beta",
    "Team Gamma",
    "Team Delta",
    "FastTrack Ops",
)

REGIONS: tuple[str, ...] = ("North", "South", "East", "West", "Central")

CHANNELS: tuple[str, ...] = (
    "Online Portal",
    "Mobile App",
    "In-Person Branch",
    "Partner Referral",
    "Mail/Post",
)


@dataclass(frozen=True)
class SyntheticExtensionRecord:
    """Represents synthetic operational metadata for a single application case."""

    application_id: str
    document_type: str
    page_count: int
    branch: str
    operator_team: str
    priority: str
    sla_target_hours: int
    region: str
    channel: str
    quality_score: float
    error_flag: bool
    rejection_flag: bool
    lineage_tag: str = "synthetic"

    def to_dict(self, include_lineage: bool = False) -> dict[str, Any]:
        """Convert record to dictionary for database insertion or serialization."""
        data = asdict(self)
        if not include_lineage:
            data.pop("lineage_tag", None)
        return data


class SyntheticExtensionGenerator:
    """Deterministic generator for synthetic operational metadata."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed

    def _get_app_rng(self, application_id: str) -> random.Random:
        """Derive isolated Random instance from SHA-256(seed + application_id)."""
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError(f"Invalid application_id: {application_id!r}. Must be a non-empty string.")

        key = f"{self.seed}:{application_id.strip()}".encode("utf-8")
        digest = hashlib.sha256(key).digest()
        seed_int = int.from_bytes(digest[:8], byteorder="big")
        return random.Random(seed_int)

    def generate_record(self, application_id: str) -> SyntheticExtensionRecord:
        """Generate a single deterministic synthetic extension record."""
        if not isinstance(application_id, str) or not application_id.strip():
            raise ValueError(f"Invalid application_id: {application_id!r}. Must be a non-empty string.")

        clean_app_id = application_id.strip()
        rng = self._get_app_rng(clean_app_id)

        priority = rng.choices(
            PRIORITY_LEVELS,
            weights=[0.25, 0.50, 0.20, 0.05],
            k=1,
        )[0]

        sla_target_hours = SLA_TARGET_HOURS[priority]
        document_type = rng.choice(DOCUMENT_TYPES)
        page_count = rng.randint(1, 25)
        branch = rng.choice(BRANCHES)
        operator_team = rng.choice(OPERATOR_TEAMS)
        region = rng.choice(REGIONS)
        channel = rng.choice(CHANNELS)

        raw_score = rng.uniform(65.0, 100.0)
        quality_score = round(raw_score, 2)

        error_flag = rng.random() < 0.08
        rejection_flag = rng.random() < 0.05

        record = SyntheticExtensionRecord(
            application_id=clean_app_id,
            document_type=document_type,
            page_count=page_count,
            branch=branch,
            operator_team=operator_team,
            priority=priority,
            sla_target_hours=sla_target_hours,
            region=region,
            channel=channel,
            quality_score=quality_score,
            error_flag=error_flag,
            rejection_flag=rejection_flag,
            lineage_tag="synthetic",
        )

        self.validate_record(record)
        return record

    def generate_batch(self, application_ids: Iterable[str]) -> list[SyntheticExtensionRecord]:
        """Generate synthetic extension records for a batch of application IDs."""
        if application_ids is None:
            raise ValueError("application_ids cannot be None")
        return [self.generate_record(app_id) for app_id in application_ids]

    @staticmethod
    def validate_record(record: SyntheticExtensionRecord) -> bool:
        """Validate that a record satisfies all schema constraints."""
        if not record.application_id or not record.application_id.strip():
            raise ValueError("Record application_id cannot be empty")

        if record.priority not in PRIORITY_LEVELS:
            raise ValueError(f"Invalid priority {record.priority!r}. Must be one of {PRIORITY_LEVELS}")

        if record.sla_target_hours != SLA_TARGET_HOURS[record.priority]:
            raise ValueError(
                f"SLA target mismatch for priority {record.priority}: "
                f"expected {SLA_TARGET_HOURS[record.priority]}, got {record.sla_target_hours}"
            )

        if not (65.00 <= record.quality_score <= 100.00):
            raise ValueError(f"Quality score {record.quality_score} out of bounds [65.00, 100.00]")

        if record.page_count < 1:
            raise ValueError(f"Page count must be >= 1, got {record.page_count}")

        return True
