# Database Schema Design — Phase 4

## Design Decisions

Based on the BPI Challenge 2017 event log (31,509 traces, 1,202,267 events) and the data dictionary (`docs/data-dictionary.md`), the database schema uses a star-like structure with:

- `applications` (trace-level, one per case)
- `events` (event-level, many per case)
- `offers` (optional, multiple per case — BPI supports this)
- `synthetic_extensions` (analytical extensions, clearly labeled synthetic)
- `data_loads` (lineage tracking)
- `schema_versions` (migration tracking)

All synthetic fields are clearly documented and separated into `synthetic_extensions`. The `synthetic_extensions` table includes a comment in SQL and a note in the code confirming these are fictional operational extensions, not historical facts from the institution.

## Schema Version: 001 (Initial)

Tables created:
1. `applications`
2. `events` (with foreign key to applications)
3. `offers` (with foreign key to applications)
4. `synthetic_extensions` (with foreign key to applications)
5. `data_loads`
6. `schema_versions`

## Migration Approach

- SQL files in `sql/` directory, named with version prefix (`001_`)
- Python module `src/database.py` handles connection, migrations, and verification
- Scripts `scripts/init_database.py` and `scripts/load_xes_to_db.py` for operations

## PostgreSQL Service

Docker Compose (`docker-compose.yml`) defines PostgreSQL 16-alpine service. It was configured in Phase 1. Service is not currently running (Docker not available in this environment) but is ready to start via:

```bash
docker compose up -d postgres
```

## Status

- Schema SQL migration file: ✅ Created (`sql/001_create_schema.sql`)
- Database Python module: ✅ Created (`src/database.py`)
- Scripts: ✅ Created (`scripts/init_database.py`, `scripts/load_xes_to_db.py`)
- Tests: ✅ All 17 database tests passing (`tests/test_database.py`)
- `.env` file: ✅ Created from `.env.example`
- Database connection: ⚠️ Not verified (PostgreSQL service not available — Docker unavailable)
- Schema execution: ⚠️ Not verified (requires running PostgreSQL)
- XES data loading: ⚠️ Not verified (requires running PostgreSQL)
