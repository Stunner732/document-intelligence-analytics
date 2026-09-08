from __future__ import annotations

import gzip
import json
from pathlib import Path

from src.cleaning.quality_pipeline import run_quality_checks


def _write_xes(path: Path) -> None:
    xes = """<?xml version=\"1.0\"?><log>
    <trace><string key=\"concept:name\" value=\"Application_1\"/>
    <event><string key=\"EventID\" value=\"Event_1\"/><string key=\"concept:name\" value=\"A_Create Application\"/><date key=\"time:timestamp\" value=\"2016-01-01T10:00:00.000Z\"/></event>
    <event><string key=\"EventID\" value=\"Event_2\"/><string key=\"concept:name\" value=\"A_Complete\"/><date key=\"time:timestamp\" value=\"2016-01-01T11:00:00.000Z\"/></event></trace>
    <trace><event><string key=\"EventID\" value=\"Event_1\"/><string key=\"concept:name\" value=\"A_Create Application\"/><date key=\"time:timestamp\" value=\"not-a-date\"/></event></trace>
    </log>"""
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(xes)


def test_quality_pipeline_writes_report_and_quarantine(tmp_path: Path) -> None:
    source = tmp_path / "source.xes.gz"
    output_dir = tmp_path / "reports"
    _write_xes(source)

    report = run_quality_checks(source, output_dir)

    assert report["records"] == {"traces": 2, "events": 3}
    counts = {item["rule"]: item["issue_count"] for item in report["rules"]}
    assert counts["missing_document_id"] == 1
    assert counts["orphan_event"] == 1
    assert counts["invalid_timestamp"] == 1
    assert counts["duplicate_event_id"] == 1
    assert (output_dir / "data_quality_report.md").is_file()
    assert json.loads((output_dir / "quarantine_manifest.json").read_text())
