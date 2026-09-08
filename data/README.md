# Data directory

`raw/` is reserved for immutable source extracts. `processed/` is reserved for
reproducible derived datasets. Phase 2 selected BPI Challenge 2017 and stores the
locally downloaded source XES archive in `raw/`; it remains Git-ignored.

Data files are ignored by Git by default. Small, explicitly approved sample data
may be added later with a corresponding provenance note.

See [`source_manifest.json`](source_manifest.json),
[`../docs/dataset.md`](../docs/dataset.md), and
[`../docs/synthetic-extension.md`](../docs/synthetic-extension.md).
