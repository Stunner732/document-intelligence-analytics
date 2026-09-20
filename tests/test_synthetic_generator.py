"""Unit tests for deterministic synthetic operational metadata generator."""

from __future__ import annotations

import pytest

from src.cleaning.synthetic_generator import (
    PRIORITY_LEVELS,
    SLA_TARGET_HOURS,
    SyntheticExtensionGenerator,
    SyntheticExtensionRecord,
)


class TestSyntheticExtensionGeneratorDeterminism:
    """Test seed-controlled determinism and order independence."""

    def test_same_seed_same_app_id_identical_output(self) -> None:
        gen1 = SyntheticExtensionGenerator(seed=42)
        gen2 = SyntheticExtensionGenerator(seed=42)

        rec1 = gen1.generate_record("Application_1001")
        rec2 = gen2.generate_record("Application_1001")

        assert rec1 == rec2
        assert rec1.to_dict() == rec2.to_dict()

    def test_different_seeds_produce_different_output(self) -> None:
        gen1 = SyntheticExtensionGenerator(seed=42)
        gen2 = SyntheticExtensionGenerator(seed=99)

        rec1 = gen1.generate_record("Application_1001")
        rec2 = gen2.generate_record("Application_1001")

        # Due to seed difference, at least some fields should differ
        assert rec1 != rec2

    def test_different_app_ids_produce_independent_records(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)

        rec1 = gen.generate_record("Application_1001")
        rec2 = gen.generate_record("Application_1002")

        assert rec1.application_id == "Application_1001"
        assert rec2.application_id == "Application_1002"
        assert rec1 != rec2

    def test_output_stable_when_input_order_changes(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)

        ids_order_a = ["App_A", "App_B", "App_C", "App_D"]
        ids_order_b = ["App_D", "App_B", "App_A", "App_C"]

        batch_a = {r.application_id: r for r in gen.generate_batch(ids_order_a)}
        batch_b = {r.application_id: r for r in gen.generate_batch(ids_order_b)}

        for app_id in ids_order_a:
            assert batch_a[app_id] == batch_b[app_id]


class TestSyntheticExtensionSchemaConstraints:
    """Test database schema constraint satisfaction."""

    def test_priority_and_sla_mapping(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        app_ids = [f"Application_{i}" for i in range(1, 100)]
        records = gen.generate_batch(app_ids)

        for rec in records:
            assert rec.priority in PRIORITY_LEVELS
            assert rec.priority.islower(), "Priority must be strictly lowercase"
            assert rec.sla_target_hours == SLA_TARGET_HOURS[rec.priority]
            assert rec.priority in ("low", "normal", "high", "urgent")

            if rec.priority == "urgent":
                assert rec.sla_target_hours == 12
            elif rec.priority == "high":
                assert rec.sla_target_hours == 24
            elif rec.priority == "normal":
                assert rec.sla_target_hours == 48
            elif rec.priority == "low":
                assert rec.sla_target_hours == 72

    def test_quality_score_bounds_and_precision(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        app_ids = [f"Application_{i}" for i in range(1, 200)]
        records = gen.generate_batch(app_ids)

        for rec in records:
            assert 65.00 <= rec.quality_score <= 100.00
            # Ensure max 2 decimal places precision
            assert round(rec.quality_score, 2) == rec.quality_score

    def test_to_dict_structure_and_lineage(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        rec = gen.generate_record("Application_500")

        d_no_lineage = rec.to_dict(include_lineage=False)
        assert "lineage_tag" not in d_no_lineage
        assert "application_id" in d_no_lineage
        assert "priority" in d_no_lineage

        d_with_lineage = rec.to_dict(include_lineage=True)
        assert d_with_lineage["lineage_tag"] == "synthetic"

    def test_schema_keys_match_database_columns(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        rec = gen.generate_record("Application_1")
        d = rec.to_dict()

        expected_cols = {
            "application_id",
            "document_type",
            "page_count",
            "branch",
            "operator_team",
            "priority",
            "sla_target_hours",
            "region",
            "channel",
            "quality_score",
            "error_flag",
            "rejection_flag",
        }
        assert set(d.keys()) == expected_cols


class TestSyntheticExtensionInputValidation:
    """Test error handling for invalid or edge case inputs."""

    @pytest.mark.parametrize("invalid_id", ["", "   ", None, 123, []])
    def test_invalid_application_id_raises_value_error(self, invalid_id: any) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        with pytest.raises(ValueError):
            gen.generate_record(invalid_id)

    def test_generate_batch_none_raises_value_error(self) -> None:
        gen = SyntheticExtensionGenerator(seed=42)
        with pytest.raises(ValueError):
            gen.generate_batch(None)

    def test_validate_record_rejects_corrupted_record(self) -> None:
        corrupted_record = SyntheticExtensionRecord(
            application_id="App_1",
            document_type="Mortgage",
            page_count=5,
            branch="Branch 1",
            operator_team="Team A",
            priority="INVALID_PRIORITY",
            sla_target_hours=24,
            region="North",
            channel="Online",
            quality_score=90.0,
            error_flag=False,
            rejection_flag=False,
        )

        with pytest.raises(ValueError, match="Invalid priority"):
            SyntheticExtensionGenerator.validate_record(corrupted_record)
