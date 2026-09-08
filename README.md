# AI-Powered Document Intelligence & Operations Analytics

An end-to-end portfolio project for analyzing document-processing operations. The
planned system will combine a governed PostgreSQL analytical layer, Python and SQL
analytics, machine learning, FastAPI, Power BI, and a locally hosted LLM that obtains
quantitative answers only through controlled tools.

## Current status

**Phase 3 — Data Quality is complete and verified.** The repository has a
non-destructive XES quality pipeline, report and quarantine outputs, and pytest
coverage. The pipeline has been executed against the real BPI Challenge 2017 dataset
with zero quarantine candidates and all structural checks passing.

## Business questions (planned)

- How much document volume is processed, and how quickly?
- Where are bottlenecks, errors, and SLA breaches concentrated?
- Which branches or teams perform best?
- Which documents are at risk of an SLA breach?
- Can users ask questions through an AI assistant grounded in database results?

## Planned architecture

See [the architecture overview](docs/architecture.md). The local LLM integration is
deliberately deferred until the underlying analytics system exists and the user's
Hermes Desktop exposure method can be inspected.

## Repository layout

| Path | Intended responsibility |
| --- | --- |
| `data/` | Raw source extracts and reproducible processed data |
| `src/data/`, `src/cleaning/` | Ingestion and quality pipeline (future phases) |
| `src/analytics/`, `sql/` | Analytical transformations and SQL analysis |
| `src/ml/` | Document classification and SLA-risk modelling |
| `src/ai/`, `api/` | Governed AI tools and API (future phases) |
| `notebooks/`, `dashboard/`, `reports/` | Analysis, Power BI specification, and outputs |
| `docs/`, `tests/`, `scripts/` | Documentation, automated tests, and utilities |

## Local setup

1. Create a virtual environment using Python 3.11 or newer.
2. Install dependencies: `python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and replace the placeholder database password.
4. Optionally run the local database: `docker compose up -d postgres`.

The source dataset is acquired separately into `data/raw/` and is excluded from Git.
Follow [the dataset acquisition guide](docs/dataset.md) to reproduce it. No processed
dataset, model, or AI service is configured yet.

## Security baseline

- Secrets belong in `.env`, never source control.
- Virtual environments, generated datasets, model artifacts, and Power BI binaries are
  ignored by default.
- Database credentials will not be exposed to an LLM. SQL validation and tool
  governance are planned before any AI integration.

## Roadmap

The project proceeds one reviewed phase at a time: data, data quality, database,
SQL analytics, Python analytics, ML, local LLM integration, AI copilot, Power BI,
testing, security hardening, and final documentation.
