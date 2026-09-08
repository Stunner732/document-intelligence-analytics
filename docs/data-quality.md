# Data-quality pipeline

## Scope

`src.cleaning.quality_pipeline` streams the gzip-compressed XES source so the full event log does not need to be loaded into memory. It writes three generated artifacts:

- `data_quality_report.json`: machine-readable rules, counts, and bounded examples;
- `data_quality_report.md`: concise operational report;
- `quarantine_manifest.json`: document IDs requiring review and the triggering rules.

Run it from the repository root with:

```powershell
python -m scripts.run_data_quality
```

## Checks and decisions

| Check | Decision |
| --- | --- |
| Missing IDs, duplicate documents, orphan events | Report and quarantine; do not delete |
| Duplicate/missing event IDs | Report for review; retain raw event |
| Missing/invalid timestamps, missing activities | Report and quarantine; do not delete |
| Non-monotonic event sequence | Report as warning; retain raw event |
| Impossible duration | Report and quarantine; do not delete |
| Negative page counts, invalid document types/status, SLA inconsistencies | Explicitly reported as not evaluable from the raw BPI source; they will be evaluated after the documented synthetic extension is created |

The pipeline does not yet produce a cleaned canonical dataset. This prevents assumptions about synthetic mapping rules from becoming invisible cleaning decisions.

## Limitations

The raw source does not contain direct document type, page count, branch, priority, SLA, or true error values. The two informational checks are therefore an intentional transparent result, not a quality pass. See [the synthetic extension specification](synthetic-extension.md).
