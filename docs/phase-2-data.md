# Phase 2: Data

## Completed

- Selected the official BPI Challenge 2017 public event log as the real operational-process source.
- Downloaded the gzip-compressed XES source archive into the Git-ignored raw-data directory.
- Recorded provenance, license, download location, published byte size, checksum, and retrieval date in `data/source_manifest.json`.
- Created dataset provenance documentation and a canonical data dictionary.
- Defined the required synthetic operational extension and its disclosure guardrails.
- Added a reproducible PowerShell downloader that refuses overwrites and validates the source checksum.

## Verification

- Local file MD5 matches the publisher's published value: `10b37a2f78e870d78406198403ff13d2`.
- Local file size matches the publisher's published value: `29,658,747` bytes.
- The raw source file is Git-ignored; the provenance manifest remains trackable.
- `data/source_manifest.json` parses successfully as JSON.
- `scripts/download_bpi_2017.ps1` parses with zero PowerShell syntax errors.

## Deferred by design

No raw records have been transformed, cleaned, excluded, or analysed. The application-case mapping and synthetic-field generation rules will be implemented and audited in Phase 3, alongside data-quality reporting.
