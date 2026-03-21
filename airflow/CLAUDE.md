# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Starting the Platform

All services are started from the `airflow/` directory:

```bash
cd airflow
docker compose up -d
```

Services:
- Airflow UI: http://localhost:8080 (admin/admin)
- Catalog API: http://localhost:8001
- Catalog UI: http://localhost:8002
- PostgreSQL: localhost:5432 (airflow/airflow)

To run the catalog UI outside Docker (development mode):
```bash
cd ../catalog-ui && python serve.py
```

## Common Commands

```bash
# Trigger the pipeline DAG manually
curl -X POST http://localhost:8080/api/v1/dags/data_platform_pipeline/dagRuns \
  -H "Content-Type: application/json" -u admin:admin -d '{}'

# Check API health
curl http://localhost:8001/health

# Run dbt manually inside the airflow-scheduler container
docker exec <container-id> dbt run --target dev --project-dir /opt/airflow/dbt/analytics_project
docker exec <container-id> dbt test --target dev --project-dir /opt/airflow/dbt/analytics_project

# Query the analytics schema
docker exec -it <postgres-container> psql -U airflow -d airflow -c "SELECT * FROM analytics.stg_servicenow_incidents LIMIT 10;"

# Login to the catalog API and get a token
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin","password":"admin"}'
```

## Architecture Overview

This is a **medallion architecture** data platform with an AI-powered data catalog.

### Data Flow

```
Supabase (source DB) → Python ingestion scripts → raw.* schema (PostgreSQL)
                                                         ↓
                                              dbt transforms
                                                         ↓
                                           analytics.stg_* / mart tables
                                                         ↓
                              Catalog API (FastAPI) registers & exposes assets
                                                         ↓
                                     Catalog UI + Claude AI chat interface
```

The single Airflow DAG (`data_platform_pipeline`, runs every 6 hours) chains:
1. `ingest_supabase` — pulls from Supabase into `raw.*`
2. `setup_dbt_profiles` — writes `~/.dbt/profiles.yml` inside the container
3. `dbt_run` — transforms raw into `analytics.*` staging and mart models
4. `dbt_test` — runs schema tests defined in `schema.yml`
5. `register_dbt_models` — upserts new dbt models into the catalog metadata DB

### Two PostgreSQL Databases

- **`airflow`** — all pipeline data: `raw.*` (ingested), `analytics.*` (transformed)
- **`catalog_db`** — catalog metadata: `catalog_assets` + `user_credentials` tables

### Key Components

**Ingestion** (`../ingestion/` relative to airflow, mounted at `/opt/airflow/ingestion`):
- `sources/supabase.py` — incremental sync via `updated_at` window (default: last 7 hours). Set `updated_col: None` in `SYNC_TABLES` for tables without a timestamp (triggers full sync).
- `sources/supabase_snapshots.py` — daily full snapshots for slowly-changing tables
- `utils/db.py` — `get_supabase()` and `get_local_pg()` connection helpers; requires `SUPABASE_*` env vars

**dbt** (`../dbt/analytics_project/`, mounted at `/opt/airflow/dbt`):
- All models are in `models/staging/`
- Staging models deduplicate using `ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC)`
- Mart models join staging tables (e.g., `application_roles_with_users` joins `stg_application_roles` + `stg_users`)
- Profile is written at runtime by `setup_dbt_profiles` task; not stored in the repo

**Catalog API** (`../catalog-api/`):
- FastAPI with two async DB connections: SQLAlchemy (catalog_db) + asyncpg pool (airflow, read-only)
- `app/services/claude_service.py` — agentic loop using `claude-haiku-4-5-20251001` with `run_sql` tool (max 10 turns)
- `app/services/sql_executor.py` — validates queries against 6 rules before execution; auto-appends `LIMIT 500`
- `app/routers/mcp.py` — MCP manifest endpoint for Claude Desktop integration
- `app/services/auth_service.py` — JWT auth (HS256, 8h expiry) + asset access control

**Catalog UI** (`../catalog-ui/`):
- Single static `index.html` (vanilla JS, no build step)
- Served by `serve.py` (Python stdlib HTTP server) on port 8002

### Authentication & Access Control

All three access channels enforce the same role-based access:

**Catalog UI / API** — JWT token via `POST /auth/login {email, password}`. Token sent as `Authorization: Bearer <token>` on all requests. Access to an asset is validated by checking `analytics.application_roles_with_users`:
```sql
WHERE full_name = :username
  AND :table_name ILIKE '%' || REPLACE(role_name, '_role', '') || '%'
```
So `incidents_role` grants access to any asset whose `table_name` contains `incidents`.

**MCP** (`/mcp/asset/{id}`) — same JWT + access check applied before returning the manifest.

**Direct SQL** — per-user PostgreSQL accounts exist with username = `lower(full_name).replace(' ', '_')` and password = `full_name`. These accounts are granted the corresponding PostgreSQL roles (`incidents_role`, `change_requests_role`, `configuration_items_role`) which have `SELECT` on matching analytics views.

**Admin** — username `admin`, password `admin` in both the catalog (bypasses all role checks) and PostgreSQL (has `platform_admin` role with full access to `raw.*` and `analytics.*`).

**`catalog_db.user_credentials`** — stores login credentials. Seeded with admin on startup. To bulk-add users from Supabase:
```python
# Run inside catalog-api container
docker exec airflow-catalog-api-1 python3 -c "
import bcrypt, psycopg2
airflow = psycopg2.connect(host='postgres', dbname='airflow', user='airflow', password='airflow')
catalog = psycopg2.connect(host='postgres', dbname='catalog_db', user='airflow', password='airflow')
# ... insert with full_name as username and password
"
```

**PostgreSQL RBAC** is set up at API startup (`setup_postgres_rbac` in `main.py`). To create per-user PostgreSQL accounts for users with application roles, run the setup script in the catalog-api container (see session history).

### Environment Variables

All configured in `airflow/.env`. The required Supabase vars that must be set:
```
SUPABASE_HOST=
SUPABASE_PORT=5432
SUPABASE_DB=postgres
SUPABASE_USER=postgres.[project-ref]   # pooler format requires project-ref suffix
SUPABASE_PASS=
```

The `x-airflow-common` block in `docker-compose.yml` passes this `.env` to all Airflow containers via `env_file`.

### Adding a New Data Source

1. Add the table to `SYNC_TABLES` in `ingestion/sources/supabase.py` (set `updated_col: None` if no timestamp column)
2. Add a staging dbt model in `dbt/analytics_project/models/staging/`
3. Add tests to `schema.yml`
4. The `register_dbt_models` task will auto-register it in the catalog on next run
5. No DAG changes needed — `ingest_supabase` and `dbt_run` pick up all configured tables/models automatically
