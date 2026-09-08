# Dataset selection and provenance

## Selected source

This project uses **BPI Challenge 2017**, a public, real-life event log for the loan-application process of a Dutch financial institution. It contains applications filed through an online system during 2016 and their subsequent events through 1 February 2017. The official publication records that the system can track multiple offers per application.

- Landing page: <https://data.4tu.nl/articles/dataset/BPI_Challenge_2017/12696884>
- DOI: <https://doi.org/10.4121/uuid:5f3067df-f10b-45da-b98b-86ae4c7a310b>
- Citation: van Dongen, B. (2017). *BPI Challenge 2017*. 4TU.ResearchData.
- License: [4TU General Terms of Use](https://doi.org/10.4121/resource:terms_of_use)

The repository does not redistribute the source file. Its URL, byte size, MD5 checksum, and retrieval date are recorded in [`data/source_manifest.json`](../data/source_manifest.json). The raw file is excluded from Git.

## Why this source fits

The source is a genuine operations workflow rather than a fabricated business dataset. It provides application case identifiers, event timestamps, named process activities, anonymous staff/system resources, lifecycle transitions, and application/offer-related attributes. These support defensible throughput, cycle-time, bottleneck, workload, and outcome analyses.

It is not a document-processing dataset in the narrow sense. It does **not** contain page counts, physical branches, operational priority, SLAs, or a true error flag. The project will construct a clearly labelled synthetic operational extension at the application-case grain. This extension is for demonstrating analytics-system design; it must never be presented as historical facts from the financial institution.

## Source attributes observed in the XES schema

| XES attribute | Meaning in this project | Availability |
| --- | --- | --- |
| `concept:name` (trace) | Application/case identifier | Source |
| `concept:name` (event) | Processing activity | Source |
| `time:timestamp` | Event time | Source |
| `org:resource` | Anonymized actor or system resource | Source |
| `EventOrigin`, `EventID`, `lifecycle:transition`, `Action` | Event metadata | Source |
| `ApplicationType`, `LoanGoal`, `RequestedAmount` | Application-level attributes | Source |
| Offer amount/cost/terms/score fields | Offer-specific attributes when present | Source |

No interpretation of observed values is made at this stage. Extraction, validation, and aggregation occur in later phases.

## Reproducible acquisition

Run `./scripts/download_bpi_2017.ps1` in PowerShell. It refuses to overwrite an existing file and verifies the published MD5 after download. It requires network access and acceptance of the source license.
