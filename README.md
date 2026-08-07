# Data Platform

A local/on-premise data platform that ingests operational data (ServiceNow via Supabase, with MariaDB/ServiceNow API connectors built for future use), transforms it through a medallion architecture with dbt, and exposes it to Power BI, an n8n chat bot, and an AI-powered Data Catalog with a Claude-driven natural-language query interface.

## Architecture

```
Supabase (source DB)
       │  ingestion/sources/supabase.py
       ▼
 raw.*                (PostgreSQL — exact copy from source)
       │  dbt
       ▼
 staging.* → analytics.* → reporting.*   (cleaned, joined, aggregated)
       │
       ├──────────────┬──────────────────┬───────────────┐
       ▼               ▼                  ▼               ▼
   Power BI     AI Data Catalog UI     n8n chat bot   Direct SQL / BI tools
                (Catalog API + Claude)
```

Apache Airflow orchestrates the whole pipeline on a 6-hour schedule:

```
ingest_supabase → setup_dbt_profiles → dbt_run → dbt_test → register_dbt_models
```

## Components

| Directory | Purpose |
|---|---|
| [`airflow/`](airflow) | Airflow DAGs, Docker Compose stack for Airflow + PostgreSQL, RBAC/dbt-registration utilities |
| [`ingestion/`](ingestion) | Python scripts that pull data from source systems (Supabase active; ServiceNow/MariaDB connectors built) into the `raw` schema |
| [`dbt/`](dbt) | dbt Core project transforming `raw` → `staging`/`analytics`/`reporting` models, with schema tests |
| [`catalog-api/`](catalog-api) | FastAPI backend: asset registry, JWT auth + role-based access control, Claude-powered SQL chat agent, MCP server for Claude Desktop |
| [`catalog-ui/`](catalog-ui) | Static HTML/JS frontend for browsing assets, viewing lineage, and chatting with Claude about the data |
| [`n8n/`](n8n) | n8n workflow automation / chat bot, Docker Compose stack |
| [`PowerBI/`](PowerBI) | Power BI dashboard connecting to the `analytics` schema |

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | Apache Airflow 2.8.1 |
| Ingestion | Python 3.13 (psycopg2, pymysql) |
| Transformation | dbt Core 1.11.x |
| Warehouse | PostgreSQL 15 |
| Catalog API | FastAPI, SQLAlchemy (async) + asyncpg, JWT auth |
| Catalog UI | Vanilla HTML/JS, no build step |
| AI | Anthropic Claude (Haiku 4.5) via `anthropic` SDK, exposed to Claude Desktop over MCP |
| Automation | n8n |
| BI | Power BI |

## Getting Started

### Prerequisites
- Docker Desktop
- Python 3.11+ (for running ingestion/dbt outside Docker)
- Supabase credentials for the source database

### 1. Configure environment variables
Copy the required variables into `airflow/.env` and `ingestion/.env` (both are git-ignored):
```
SUPABASE_HOST=
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=postgres.[project-ref]
SUPABASE_PASS=
ANTHROPIC_API_KEY=sk-ant-...
POSTGRES_USER=airflow
POSTGRES_PASSWORD=airflow
POSTGRES_DB=airflow
```

### 2. Start the platform
```bash
cd airflow
docker compose up -d
```

This brings up PostgreSQL, Airflow (webserver + scheduler), the Catalog API, and the Catalog UI.

### 3. Unpause the DAG
Open the Airflow UI, log in, and toggle `data_platform_pipeline` on. It runs automatically every 6 hours, or trigger it manually:
```bash
docker exec <airflow-scheduler-container> airflow dags trigger data_platform_pipeline
```

### 4. Explore the data
Open the AI Data Catalog and browse assets, or ask Claude a question about the data directly.

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| Airflow UI | http://localhost:8080 | admin / admin |
| Catalog UI | http://localhost:8002 | JWT login (see below) |
| Catalog API | http://localhost:8001 | — |
| PostgreSQL | localhost:5432 | airflow / airflow |
| n8n | http://localhost:5678 | — |

## Authentication & Access Control

The Catalog UI/API and the MCP integration share the same role-based access model:
- Users log in via `POST /auth/login` and receive a JWT (`Authorization: Bearer <token>`).
- Access to an asset is checked against `analytics.application_roles_with_users`: a role like `incidents_role` grants access to any asset whose table name contains `incidents`.
- Per-user PostgreSQL accounts mirror the same roles for direct SQL access.
- `admin` / `admin` bypasses role checks (Catalog) and holds full access (PostgreSQL).

## Adding a New Data Source

1. Add credentials to `ingestion/.env`.
2. Add the table to `SYNC_TABLES` in `ingestion/sources/supabase.py` (or write a new connector under `ingestion/sources/`).
3. Add a staging model in `dbt/analytics_project/models/staging/`.
4. Add tests to `schema.yml`.
5. Run `dbt run && dbt test`, then trigger the DAG — `register_dbt_models` auto-registers new models in the catalog.

See [`Data_Platform_Operations_Guide_UPDATED.md`](Data_Platform_Operations_Guide_UPDATED.md) for the full walkthrough.

## Further Documentation

- [`Data_Platform_Operations_Guide_UPDATED.md`](Data_Platform_Operations_Guide_UPDATED.md) — full operations reference: startup/shutdown, maintenance, troubleshooting, extending the platform
- [`DEVELOPER_QUICK_REF.md`](DEVELOPER_QUICK_REF.md) — quick command/query reference for local development
- [`catalog-api/ARCHITECTURE.md`](catalog-api/ARCHITECTURE.md) — Catalog API/UI design details
- [`MCP_SERVER_SUMMARY.md`](MCP_SERVER_SUMMARY.md) — connecting Claude Desktop to the catalog via MCP
- [`airflow/CLAUDE.md`](airflow/CLAUDE.md) — architecture notes for AI coding agents working in this repo
