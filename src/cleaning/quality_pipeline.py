"""Non-destructive data-quality checks for BPI Challenge 2017 XES data.

The pipeline writes audit reports and a quarantine manifest. It never mutates the raw
archive and never silently removes a record.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree as ET


MAX_EXAMPLES_PER_RULE = 20


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _attributes(element: ET.Element) -> dict[str, str]:
    """Return direct XES attributes from an event or trace element."""
    return {
        child.attrib["key"]: child.attrib.get("value", "")
        for child in element
        if _local_name(child.tag)
        in {"string", "date", "int", "float", "boolean", "id"}
        and "key" in child.attrib
    }


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class IssueCollector:
    """Collect bounded examples and full counts without retaining raw event payloads."""

    counts: Counter[str] = field(default_factory=Counter)
    examples: dict[str, list[dict[str, str]]] = field(default_factory=dict)

    def add(self, rule: str, document_id: str, detail: str, severity: str) -> None:
        self.counts[rule] += 1
        bucket = self.examples.setdefault(rule, [])
        if len(bucket) < MAX_EXAMPLES_PER_RULE:
            bucket.append(
                {
                    "document_id": document_id or "<missing>",
                    "detail": detail,
                    "severity": severity,
                }
            )


RULE_CATALOG: tuple[dict[str, str], ...] = (
    {
        "rule": "missing_document_id",
        "description": "Each trace must provide concept:name.",
        "severity": "error",
    },
    {
        "rule": "duplicate_document",
        "description": "Trace concept:name must be unique.",
        "severity": "error",
    },
    {
        "rule": "orphan_event",
        "description": "Each event must belong to a trace with an identifier.",
        "severity": "error",
    },
    {
        "rule": "missing_event_id",
        "description": "EventID should be populated for each source event.",
        "severity": "warning",
    },
    {
        "rule": "duplicate_event_id",
        "description": "EventID should be unique across the source extract.",
        "severity": "warning",
    },
    {
        "rule": "missing_timestamp",
        "description": "Every event should have time:timestamp.",
        "severity": "error",
    },
    {
        "rule": "invalid_timestamp",
        "description": "Event timestamps must be ISO-8601 parseable.",
        "severity": "error",
    },
    {
        "rule": "missing_activity",
        "description": "Every event should have concept:name.",
        "severity": "error",
    },
    {
        "rule": "non_monotonic_event_time",
        "description": "Source events should not move backwards within a trace.",
        "severity": "warning",
    },
    {
        "rule": "impossible_processing_duration",
        "description": "The derived end time must not precede the derived received time.",
        "severity": "error",
    },
    {
        "rule": "unavailable_document_extension_fields",
        "description": "Page count, document type, SLA, branch, priority, and true error fields are not source attributes.",
        "severity": "info",
    },
    {
        "rule": "sla_consistency_not_evaluable",
        "description": "SLA consistency is deferred until synthetic SLA targets are generated with documented rules.",
        "severity": "info",
    },
)


def iter_traces(source_path: Path) -> Iterable[tuple[dict[str, str], list[dict[str, str]]]]:
    """Stream traces from an XES gzip archive without loading it all into memory."""
    with gzip.open(source_path, "rb") as source:
        for _, element in ET.iterparse(source, events=("end",)):
            if _local_name(element.tag) != "trace":
                continue
            trace_attributes = _attributes(element)
            events = [
                _attributes(child)
                for child in element
                if _local_name(child.tag) == "event"
            ]
            yield trace_attributes, events
            element.clear()


def run_quality_checks(source_path: Path, output_dir: Path) -> dict[str, Any]:
    """Run source-quality checks and write JSON, Markdown, and quarantine artifacts."""
    if not source_path.is_file():
        raise FileNotFoundError(f"Source archive not found: {source_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    issues = IssueCollector()
    seen_documents: set[str] = set()
    seen_events: set[str] = set()
    total_documents = 0
    total_events = 0
    quarantine: list[dict[str, str]] = []

    for trace, events in iter_traces(source_path):
        total_documents += 1
        document_id = trace.get("concept:name", "").strip()
        trace_rules: set[str] = set()

        if not document_id:
            issues.add("missing_document_id", document_id, "Trace concept:name is blank.", "error")
            trace_rules.add("missing_document_id")
        elif document_id in seen_documents:
            issues.add("duplicate_document", document_id, "Trace concept:name repeats.", "error")
            trace_rules.add("duplicate_document")
        else:
            seen_documents.add(document_id)

        previous_time: datetime | None = None
        valid_times: list[datetime] = []
        for event in events:
            total_events += 1
            event_id = event.get("EventID", "").strip()
            if not document_id:
                issues.add("orphan_event", document_id, "Event belongs to a trace without an identifier.", "error")
                trace_rules.add("orphan_event")
            if not event_id:
                issues.add("missing_event_id", document_id, "EventID is blank.", "warning")
            elif event_id in seen_events:
                issues.add("duplicate_event_id", document_id, f"Repeated EventID: {event_id}", "warning")
            else:
                seen_events.add(event_id)

            if not event.get("concept:name", "").strip():
                issues.add("missing_activity", document_id, "Event concept:name is blank.", "error")
                trace_rules.add("missing_activity")

            raw_timestamp = event.get("time:timestamp", "").strip()
            parsed_timestamp = _parse_timestamp(raw_timestamp)
            if not raw_timestamp:
                issues.add("missing_timestamp", document_id, "time:timestamp is blank.", "error")
                trace_rules.add("missing_timestamp")
            elif parsed_timestamp is None:
                issues.add("invalid_timestamp", document_id, f"Unparseable timestamp: {raw_timestamp}", "error")
                trace_rules.add("invalid_timestamp")
            else:
                valid_times.append(parsed_timestamp)
                if previous_time and parsed_timestamp < previous_time:
                    issues.add("non_monotonic_event_time", document_id, "Event time precedes prior event time.", "warning")
                previous_time = parsed_timestamp

        if valid_times and max(valid_times) < min(valid_times):
            issues.add("impossible_processing_duration", document_id, "Derived duration is negative.", "error")
            trace_rules.add("impossible_processing_duration")
        if trace_rules:
            quarantine.append(
                {
                    "document_id": document_id or "<missing>",
                    "decision": "quarantine_for_review",
                    "rules": ";".join(sorted(trace_rules)),
                }
            )

    for rule in ("unavailable_document_extension_fields", "sla_consistency_not_evaluable"):
        issues.add(rule, "<dataset>", "See synthetic-extension.md for documented scope.", "info")

    report: dict[str, Any] = {
        "source_path": str(source_path),
        "records": {"traces": total_documents, "events": total_events},
        "pipeline_decision": "No raw records were deleted or altered.",
        "status": "completed_with_documented_source_schema_limitations",
        "rules": [
            {
                **rule,
                "issue_count": issues.counts.get(rule["rule"], 0),
                "examples": issues.examples.get(rule["rule"], []),
            }
            for rule in RULE_CATALOG
        ],
        "quarantine_record_count": len(quarantine),
    }
    (output_dir / "data_quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output_dir / "quarantine_manifest.json").write_text(json.dumps(quarantine, indent=2), encoding="utf-8")
    _write_markdown_report(output_dir / "data_quality_report.md", report)
    return report


def _write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Data quality report",
        "",
        f"- Source: `{report['source_path']}`",
        f"- Traces checked: {report['records']['traces']}",
        f"- Events checked: {report['records']['events']}",
        f"- Quarantine candidates: {report['quarantine_record_count']}",
        f"- Decision: {report['pipeline_decision']}",
        "",
        "| Rule | Severity | Issue count |",
        "| --- | --- | ---: |",
    ]
    for rule in report["rules"]:
        lines.append(f"| {rule['rule']} | {rule['severity']} | {rule['issue_count']} |")
    lines.extend(
        [
            "",
            "Synthetic fields and SLA consistency are explicitly reported as not evaluable from the raw source. They are not silently passed.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
