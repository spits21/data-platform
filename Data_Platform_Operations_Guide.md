# **Data Platform**  
# **Operations & Maintenance Guide**

Docker • Python Scripts • Airflow • dbt • PostgreSQL • Supabase • Data Catalog

*Design Reference | Daily Operations | Troubleshooting | Extending the Platform*

**Version 2.0 — March 14, 2026**

---

# **Section 1 — Platform Overview**

## **1.1  Purpose & Scope**

The data platform serves as a central repository that:
- **Ingests** data from multiple source systems (Supabase, ServiceNow, MariaDB)
- **Transforms** it into clean analytics-ready tables via dbt
- **Exposes** data through a queryable catalog UI with lineage visualization
- **Orchestrates** all processes via Apache Airflow on a 6-hour schedule
- **Powers** Power BI dashboards, AI agents, and direct SQL access

This guide covers the full architecture, daily operations, maintenance tasks, troubleshooting, and extending the platform.

## **1.2  Architecture Diagram**

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SOURCE SYSTEMS                               │
│   Supabase DB    ServiceNow API    MariaDB DBs    Server Stats      │
└────────┬─────────────────┬──────────────┬──────────────┬───────────┘
         │                 │              │              │
         └─────────────────┴──────────────┴──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    Python Ingestion Scripts  │
                    │  sources/supabase.py         │
                    │  sources/servicenow.py       │
                    │  sources/mariadb.py          │
                    └──────────────┬──────────────┘
                                   │ writes to
                    ┌──────────────▼──────────────┐
                    │   PostgreSQL: raw schema     │
                    │   raw.supabase_incidents     │
                    └──────────────┬──────────────┘
                                   │ transformed by
                    ┌──────────────▼──────────────┐
                    │        dbt Core              │
                    │   staging → analytics →      │
                    │        reporting             │
                    └──────────────┬──────────────┘
                                   │ served to
              ┌────────────────────┼────────────────────┐
              │                    │                    │
   ┌──────────▼──────┐  ┌─────────▼──────┐  ┌────────▼────────┐
   │    Power BI      │  │   Catalog UI    │  │  SQL Queries    │
   │   Dashboards     │  │  (port 8002)    │  │  DBeaver/psql   │
   └─────────────────┘  └────────┬────────┘  └────────────────┘
                                   │ displays
                         ┌─────────▼──────────┐
                         │  Asset Schemas      │
                         │  Lineage Flows      │
                         │  AI Chat Interface  │
                         │  Connection Info    │
                         └────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │    Apache Airflow            │
                    │  Orchestrates & monitors     │
                    │  every step — every 6 hours  │
                    └─────────────────────────────┘
```

## **1.3  Technology Stack**

| Component | Technology | Version | Role |
|:---|:---|:---|:---|
| Container Runtime | Docker Desktop | Latest | Hosts all services |
| Orchestration | Apache Airflow | 2.8.1 | Schedules and monitors pipelines |
| Metadata Database | PostgreSQL | 15 | Airflow metadata + data warehouse |
| Ingestion | Python Scripts | 3.13 | Pulls data from all sources |
| Transformation | dbt Core | 1.11.6 | SQL models and data quality tests |
| Catalog Frontend | Static HTML | - | Asset browser with lineage visualization |
| Catalog Server | Python HTTP | 3.8+ | Serves static HTML on port 8002 |
| Catalog API | FastAPI | - | Backend for asset metadata and chat |
| BI Output | Power BI | Latest | Dashboards and reporting |
| Source DB | Supabase | Cloud | Primary data source (incidents) |

## **1.4  Database Schema Layout**

All data lives in a single PostgreSQL instance. It is organized into schemas representing the medallion data architecture:

| Schema | Purpose | Who Writes | Who Reads |
|:---|:---|:---|:---|
| raw.* | Raw ingested data — exact copy from source, no changes | Python scripts | dbt staging models |
| staging.* | Cleaned, typed, deduplicated data — one model per source | dbt | dbt analytics models |
| analytics.* | Business logic, joins, aggregations | dbt | dbt reporting models, Power BI, Catalog UI |
| reporting.* | Final materialized views — optimized for dashboards | dbt | Power BI, AI agents |
| catalog.* | Catalog metadata and asset definitions | Backend API | Catalog UI, AI agents |

## **1.5  File Structure Reference**

```
C:\Users\spits\data-platform\
│
├── airflow\
│   ├── dags\
│   │   └── data_pipeline.py        ← Main Airflow DAG
│   ├── logs\                        ← Airflow runtime logs (auto-populated)
│   ├── plugins\                     ← Custom operators (currently empty)
│   ├── .env                         ← Airflow + PostgreSQL credentials
│   ├── docker-compose.yml           ← All Docker service definitions
│   └── docker-compose.override.yml  ← Local dev overrides
│
├── catalog-ui\                      ← NEW: Data Catalog Frontend
│   ├── index.html                  ← Main UI (HTML + vanilla JS)
│   ├── serve.py                    ← Python HTTP server
│   ├── README.md                   ← Frontend documentation
│   ├── .env.local                  ← Frontend config
│   └── .gitignore
│
├── catalog-api\                     ← Catalog Backend
│   ├── app\
│   │   ├── models\                 ← SQLAlchemy ORM models
│   │   ├── routers\                ← API endpoints
│   │   ├── schemas\                ← Pydantic validation
│   │   └── services\               ← Business logic
│   ├── seed\
│   │   └── seed_assets.py          ← Initialize catalog with 5 assets
│   ├── Dockerfile
│   └── requirements.txt
│
├── ingestion\
│   ├── sources\
│   │   ├── supabase.py              ← Supabase connector (ACTIVE)
│   │   ├── servicenow.py            ← ServiceNow connector (built, inactive)
│   │   └── mariadb.py               ← MariaDB connector (built, inactive)
│   ├── utils\
│   │   └── db.py                    ← Shared DB connection helpers
│   └── .env                         ← All source system credentials
│
└── dbt\
    ├── .dbt\
    │   └── profiles.yml             ← dbt database connection config
    └── analytics_project\
        ├── dbt_project.yml          ← dbt project config
        └── models\
            ├── staging\
            │   ├── stg_servicenow_incidents.sql
            │   ├── stg_servicenow_change_requests.sql
            │   ├── stg_servicenow_configuration_items.sql
            │   └── schema.yml        ← Data quality tests
            └── analytics\
                ├── incidents_with_configuration_items.sql
                └── incidents_with_change_requests.sql
```

---

# **Section 2 — Daily Operations**

## **2.1  Starting the Platform**

The platform consists of Docker containers (Airflow + PostgreSQL) and a Python HTTP server (Catalog UI) that need to be started each time your machine reboots.

**Step 1: Start Docker Services**

```powershell
# Open PowerShell and navigate to Airflow directory
cd C:\Users\spits\data-platform\airflow

# Start all Airflow containers in the background
docker compose up -d

# Verify all containers are healthy
docker compose ps
```

You should see status `Up (healthy)` or `Up` for:
- airflow-postgres-1
- airflow-airflow-webserver-1
- airflow-airflow-scheduler-1

**Step 2: Start the Catalog UI Server**

```powershell
# In a new PowerShell window, navigate to catalog-ui
cd C:\Users\spits\data-platform\catalog-ui

# Start the Python HTTP server (runs in foreground)
python serve.py
```

You should see:
```
Serving catalog UI on all interfaces, port 8002
Navigate to http://localhost:8002 or http://192.168.1.156:8002
```

**Step 3: Verify All Services**

```powershell
# Open Airflow UI
# Navigate to http://localhost:8080

# Log in: username=admin, password=admin

# Confirm data_pipeline DAG is active (blue toggle)

# Open Catalog UI
# Navigate to http://localhost:8002

# Confirm assets load and you can click through tabs
```

💡 **Environment Startup Script (Optional)**

Create a `.bat` file to automate startup:

```batch
@echo off
REM Start Docker services (background)
cd C:\Users\spits\data-platform\airflow
docker compose up -d
timeout /t 10

REM Start Catalog UI (foreground in new window)
start cmd /k "cd C:\Users\spits\data-platform\catalog-ui && python serve.py"

REM Open browser windows
timeout /t 5
start http://localhost:8080
start http://localhost:8002

echo Services started. Airflow: http://localhost:8080  Catalog: http://localhost:8002
```

## **2.2  Stopping the Platform**

```powershell
# Stop Docker containers (preserves data)
cd C:\Users\spits\data-platform\airflow
docker compose down

# Stop Catalog UI server (Ctrl+C in the terminal)
# or kill the process:
Get-Process -Name python | Where-Object {$_.CommandLine -match "serve.py"} | Stop-Process -Force

# Close Docker Desktop from system tray
```

⚠️ All data is preserved. Container shutdown is safe.

## **2.3  Checking Pipeline Health**

**Via Airflow UI (Recommended)**

1. Open http://localhost:8080 and log in
2. Find `data_platform_pipeline` in the DAG list
3. Check the **Recent Tasks** column — you want green circles only
4. Click on the DAG name, then **Graph** to see the last run visually
5. All three task boxes should be dark green (success)

**Task Status Colors:**

| Color | Meaning | Action |
|:---|:---|:---|
| Dark Green | Success — completed without errors | None |
| Light Green | Running — currently executing | Wait and monitor |
| Yellow | Queued — waiting to start | Wait; check scheduler if stuck > 5 min |
| Orange | Up for retry — failed, retrying | Check logs after retries complete |
| Red | Failed — all retries exhausted | Check logs and fix immediately |
| Gray | Skipped — did not run | Check upstream task for failures |

**Via Command Line**

```powershell
# View Airflow scheduler logs
docker compose logs airflow-scheduler

# View last 100 lines of scheduler logs
docker compose logs airflow-scheduler | Select-Object -Last 100

# Trigger a manual DAG run from CLI
docker exec airflow-airflow-scheduler-1 airflow dags trigger data_platform_pipeline
```

## **2.4  Checking Catalog UI Health**

```powershell
# Test frontend is responding
try { 
  $r = Invoke-WebRequest -Uri "http://localhost:8002/" -UseBasicParsing
  Write-Host "✅ Catalog UI: $($r.StatusCode)"
} catch { 
  Write-Host "❌ Catalog UI: FAILED" 
}

# Test backend API is responding
try { 
  $r = Invoke-WebRequest -Uri "http://localhost:8001/assets" -UseBasicParsing
  Write-Host "✅ Catalog API: $($r.StatusCode)" 
} catch { 
  Write-Host "❌ Catalog API: FAILED" 
}
```

## **2.5  Manually Triggering a Pipeline Run**

Use this when you need fresh data outside the normal 6-hour schedule.

**Via Airflow UI**

1. Open http://localhost:8080 and log in
2. Find `data_platform_pipeline` in the DAG list
3. Click the **Play button** (▶) on the right side
4. Select **Trigger DAG**
5. Click on the DAG name, then **Graph** to watch the run in real time

**Via Command Line**

```powershell
docker exec airflow-airflow-scheduler-1 airflow dags trigger data_platform_pipeline

# View run details
docker exec airflow-airflow-scheduler-1 airflow dags list-runs --dag-id data_platform_pipeline
```

## **2.6  Querying Your Data**

### **Via Docker (no install required)**

```powershell
docker exec -it airflow-postgres-1 psql -U airflow -d airflow

-- Then run any SQL:
SELECT count(*) FROM analytics.stg_servicenow_incidents;
SELECT state, count(*) FROM analytics.stg_servicenow_incidents GROUP BY state;
\q  -- to exit
```

### **Via DBeaver (recommended GUI tool)**

Connect with:
- Host = localhost
- Port = 5432
- Database = airflow
- User = airflow
- Password = airflow

### **Useful Queries**

```sql
-- Row counts across all schemas
SELECT schemaname, tablename, n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY schemaname, tablename;

-- Check when raw data was last synced
SELECT max(updated_at) as last_updated FROM raw.supabase_incidents;

-- Incident breakdown by state
SELECT state, count(*) as total
FROM analytics.stg_servicenow_incidents
GROUP BY state ORDER BY total DESC;

-- Incident breakdown by priority
SELECT priority_code, count(*) as total
FROM analytics.stg_servicenow_incidents
GROUP BY priority_code ORDER BY total DESC;

-- Most recently updated incidents
SELECT incident_number, state, priority_code, updated_at
FROM analytics.stg_servicenow_incidents
ORDER BY updated_at DESC LIMIT 20;

-- Catalog assets count
SELECT count(*) FROM catalog.catalog_asset;

-- Catalog assets with metadata
SELECT id, name, display_name, schema_name, table_name, source_system
FROM catalog.catalog_asset
ORDER BY id;
```

---

# **Section 3 — Catalog UI Operations**

## **3.1  What is the Catalog UI?**

The Data Catalog provides a web interface to:
- **Browse** all ingested and transformed data assets
- **View** detailed schemas with column names, types, and descriptions
- **Explore** data lineage showing how data flows through the platform
- **Query** assets directly via API or SQL connection
- **Chat** with Claude AI about your data

The frontend is a **static HTML application** (no build step) served by a simple Python HTTP server on port 8002.

## **3.2  Starting the Catalog UI Server**

```powershell
# Navigate to catalog-ui directory
cd C:\Users\spits\data-platform\catalog-ui

# Start the server
python serve.py

# Expected output:
# Serving catalog UI on all interfaces, port 8002
# Navigate to http://localhost:8002 or http://192.168.1.156:8002
```

The server runs in the foreground and logs all requests.

## **3.3  Accessing the Catalog**

**Local Access:**
- http://localhost:8002

**Network Access (from other machines):**
- http://192.168.1.156:8002 (or your machine's IP address)

## **3.4  Catalog UI Features**

### **Browse Page**
- Search assets by name, table name, or description
- Filter by domain (ITSM, Analytics, etc.)
- View asset status and tags
- Click "View Details" to open asset detail page

### **Asset Detail Page**
- **Schema Tab** - Column names, types, and descriptions from PostgreSQL
- **Lineage Tab** - Visual representation of data flow stages
- **Quality Tab** - Data quality metrics and test results
- **Connection Info** - Copy connection strings, MCP configs, or launch Claude

### **Lineage Visualization**
Shows data journey through 4 stages:

1. **SOURCE** - Where data originates (ServiceNow API, Supabase, etc.)
2. **ORCHESTRATION** - How data is scheduled (Airflow DAG)
3. **STORAGE** - Raw data location (PostgreSQL raw schema)
4. **TRANSFORMATION** - Analytics models (dbt models)

For joined models, shows:
- **UPSTREAM** - Source models that feed into the join
- **DOWNSTREAM** - Resulting joined model

### **AI Chat**
- Ask questions about selected assets
- Requires backend API running on http://localhost:8001
- Uses Claude AI via the `/ai-lab/chat` endpoint

## **3.5  Current Catalog Assets (5 Total)**

| ID | Asset | Schema | Table | Source | Type |
|:---|:---|:---|:---|:---|:---|
| 6 | ServiceNow Incidents (Staging) | staging | stg_servicenow_incidents | Supabase | Staging |
| 7 | Configuration Items (Staging) | staging | stg_servicenow_configuration_items | Supabase | Staging |
| 8 | Incidents + CI (Mart) | analytics | incidents_with_configuration_items | dbt | Analytics |
| 9 | Change Requests (Staging) | staging | stg_servicenow_change_requests | Supabase | Staging |
| 10 | Incidents + Changes (Mart) | analytics | incidents_with_change_requests | dbt | Analytics |

## **3.6  Updating Catalog Metadata**

Asset metadata is stored in PostgreSQL and served by the catalog-api backend.

**Add a New Asset:**

1. Insert into `catalog.catalog_asset` table via the backend seed script
2. Restart the backend API container
3. Refresh the catalog UI (Ctrl+Shift+R)

**Update Asset Columns:**

The column information is derived from the actual PostgreSQL table structures and fetched dynamically.

To add detailed descriptions:
1. Query `catalog.catalog_asset.columns` (JSON field)
2. Update via the backend API or directly in the database

---

# **Section 4 — Pipeline Design Details**

## **4.1  Ingestion Layer — How Python Scripts Work**

Each ingestion script connects to a source, pulls records changed since the last run, and writes to the raw schema using an upsert pattern.

| Script | Source | Target Table | Incremental Column | Status |
|:---|:---|:---|:---|:---|
| sources/supabase.py | Supabase PostgreSQL | raw.supabase_incidents | updated_at | ✅ Active |
| sources/servicenow.py | ServiceNow REST API | raw.servicenow_incidents | sys_updated_on | Built — inactive |
| sources/mariadb.py | MariaDB database | raw.mariadb_<table> | updated_at | Built — inactive |

**Incremental Sync Window:** 7 hours (1 hour overlap beyond the 6-hour schedule)

This ensures no records are missed if a run is delayed.

**Upsert Logic:** If a record already exists in the raw table, it updates it rather than inserting a duplicate.

```sql
INSERT INTO raw.supabase_incidents (...) VALUES ...
ON CONFLICT (id) DO UPDATE SET ..., synced_at = NOW()
```

## **4.2  Transformation Layer — How dbt Works**

dbt runs SQL transformations in dependency order. Each model reads from the previous layer and produces a new table or view.

| Model | Schema | Type | Source | Description |
|:---|:---|:---|:---|:---|
| stg_servicenow_incidents | analytics | View | raw.supabase_incidents | Deduplicated, cleaned incidents |
| stg_servicenow_change_requests | analytics | View | raw.supabase_change_requests | Deduplicated, cleaned changes |
| stg_servicenow_configuration_items | analytics | View | raw.supabase_configuration_items | Deduplicated, cleaned CIs |
| incidents_with_configuration_items | analytics | View | stg_servicenow_incidents + stg_servicenow_configuration_items | Joined mart |
| incidents_with_change_requests | analytics | View | stg_servicenow_incidents + stg_servicenow_change_requests | Joined mart |

**Staging models perform:**
- **Deduplication** - ROW_NUMBER() keeps only the most recent version
- **Type casting** - Converts text to proper types (timestamps, integers)
- **Null filtering** - Removes records with null primary keys

**Data quality tests run automatically after dbt run:**
- `incident_id` → unique, not_null
- `incident_number` → not_null
- `state` → not_null
- `created_at` → not_null

## **4.3  Orchestration Layer — How Airflow Works**

Airflow runs `data_platform_pipeline` DAG on a cron schedule of `0 */6 * * *` (every 6 hours).

**Task Execution Order:**

```
ingest_supabase ──► dbt_run ──► dbt_test ──► (catalog sync)
```

Each task must succeed before the next starts.
- If `ingest_supabase` fails → `dbt_run` and `dbt_test` are skipped
- If `dbt_run` fails → `dbt_test` is skipped
- Failed tasks retry up to 2 times with a 5-minute delay

| DAG Setting | Value | Effect |
|:---|:---|:---|
| schedule_interval | 0 */6 * * * | Runs at 12am, 6am, 12pm, 6pm daily |
| retries | 2 | Each task retries twice on failure |
| retry_delay | 5 minutes | Waits 5 minutes between retries |
| catchup | False | Does not backfill missed runs |
| start_date | 2025-01-01 | DAG activation reference date |

---

# **Section 5 — Routine Maintenance**

## **5.1  Weekly Tasks**

### **Review Airflow Run History**

1. Open http://localhost:8080 and click on `data_platform_pipeline`
2. Click the **Calendar** view to see a heatmap of run success/failures over the week
3. Investigate any red cells by clicking and reviewing logs

### **Check Disk Usage**

```powershell
docker system df

# If high, clean up old logs and unused images:
docker system prune

# Remove Airflow logs older than 30 days:
Get-ChildItem C:\Users\spits\data-platform\airflow\logs -Recurse |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
  Remove-Item -Force
```

### **Verify Data Freshness**

```powershell
docker exec -it airflow-postgres-1 psql -U airflow -d airflow -c \
"SELECT max(updated_at) as last_record, max(synced_at) as last_sync
 FROM raw.supabase_incidents;"
```

### **Verify Catalog Assets**

```powershell
# Check catalog dashboard heartbeat
curl http://localhost:8001/assets | ConvertFrom-Json | Measure-Object

# Should return 5 assets
```

## **5.2  Monthly Tasks**

### **Update Python Dependencies**

```powershell
pip install --upgrade dbt-core dbt-postgres psycopg2-binary
pip install --upgrade requests pandas python-dotenv pymysql

# Verify dbt still works
cd C:\Users\spits\data-platform\dbt\analytics_project
dbt debug
```

### **Update Docker Images**

```powershell
cd C:\Users\spits\data-platform\airflow

# Pull latest images
docker compose pull

# Restart with new versions
docker compose down
docker compose up -d

# Test a manual DAG run
docker exec airflow-airflow-scheduler-1 airflow dags trigger data_platform_pipeline
```

### **Optimize PostgreSQL**

```powershell
docker exec -it airflow-postgres-1 psql -U airflow -d airflow

-- Check table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname IN ('raw','staging','analytics','reporting')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Run vacuum to reclaim space
VACUUM ANALYZE raw.supabase_incidents;
\q
```

## **5.3  Quarterly Tasks**

### **Archive Historical Logs**

```powershell
# Compress and backup Airflow logs older than 60 days
$logs = Get-ChildItem C:\Users\spits\data-platform\airflow\logs -Recurse |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-60) }

# Create backup
$backupPath = "C:\Users\spits\data-platform\airflow\logs_archive"
if (-not (Test-Path $backupPath)) { New-Item -ItemType Directory $backupPath }

$logs | Move-Item -Destination $backupPath

Write-Host "Archived $($logs.Count) old log files"
```

### **Audit Data Quality**

```sql
-- Check for unexpected nulls in critical fields
SELECT 'stg_servicenow_incidents' as table_name,
       count(case when incident_id is null then 1 end) as null_incident_id,
       count(case when incident_number is null then 1 end) as null_incident_number,
       count(case when state is null then 1 end) as null_state
FROM analytics.stg_servicenow_incidents;

-- Check for duplicates that slipped through
SELECT incident_id, count(*) as duplicate_count
FROM analytics.stg_servicenow_incidents
GROUP BY incident_id
HAVING count(*) > 1;
```

---

# **Section 6 — Troubleshooting**

## **6.1  Docker & Container Issues**

### **Containers not starting or keep restarting**

```powershell
# Check container status
docker compose ps

# View startup logs
docker compose logs airflow-webserver
docker compose logs airflow-scheduler
docker compose logs postgres
```

**Common causes and fixes:**

- **Not enough memory** → Increase Docker Desktop memory to at least 8 GB
  (Settings → Resources → Advanced)

- **Port conflict** → Another app using 8080 or 5432
  (Stop conflicting app or change port in docker-compose.yml)

- **Volume permissions** → On Windows, ensure data-platform folder is shared in Docker Desktop
  (Settings → Resources → File Sharing)

### **Cannot connect to Docker daemon**

Docker Desktop is not running. Open Docker Desktop and wait for "Running" in system tray.

## **6.2  Airflow Issues**

### **DAG not appearing in the UI**

```powershell
# Check DAG file syntax
docker exec airflow-airflow-scheduler-1 python /opt/airflow/dags/data_pipeline.py

# Check scheduler logs for import errors
docker compose logs airflow-scheduler | grep ERROR
```

### **Task stuck in queued state**

```powershell
# Restart the scheduler
docker compose restart airflow-scheduler
```

### **All tasks failing after machine restart**

The profiles.yml was lost. Recreate it:

```powershell
docker exec airflow-airflow-scheduler-1 mkdir -p /home/airflow/.dbt
docker exec airflow-airflow-scheduler-1 bash -c "cat > /home/airflow/.dbt/profiles.yml << 'EOF'
analytics_project:
  target: dev
  outputs:
    dev:
      type: postgres
      host: postgres
      user: airflow
      password: airflow
      port: 5432
      dbname: airflow
      schema: analytics
      threads: 4
EOF"
```

## **6.3  Ingestion Script Issues**

### **Connection refused to PostgreSQL**

**Cause:** LOCAL_PG_HOST in ingestion/.env is set to localhost but script runs inside Docker where it should be `postgres`.

```powershell
# Verify ingestion/.env
type C:\Users\spits\data-platform\ingestion\.env

# Should show:
# LOCAL_PG_HOST=postgres
```

### **Cannot connect to Supabase**

```powershell
cd C:\Users\spits\data-platform\ingestion
python -c "from utils.db import get_supabase; c = get_supabase(); print('Connected OK'); c.close()"
```

**Common causes:**
- Wrong host in .env — verify against Supabase dashboard
- Password with special characters — wrap in double quotes in .env
- Network issue — test connectivity

### **No rows synced — script runs but raw table is empty**

The incremental window is too narrow (no records updated in last 7 hours). Do a full reload:

```python
# Temporarily change in sources/supabase.py:
run_all(since=datetime(2000, 1, 1, tzinfo=timezone.utc))

# Then change back to:
run_all(since=datetime.now(timezone.utc) - timedelta(hours=6))
```

### **ModuleNotFoundError**

Always run from the ingestion directory with -m flag:

```powershell
cd C:\Users\spits\data-platform\ingestion
python -m sources.supabase
```

## **6.4  dbt Issues**

### **profiles.yml not found**

```powershell
type C:\Users\spits\data-platform\dbt\.dbt\profiles.yml

# Verify dbt can connect
cd C:\Users\spits\data-platform\dbt\analytics_project
dbt debug
```

### **Relation does not exist error**

The raw table hasn't been created. Run ingestion first:

```powershell
cd C:\Users\spits\data-platform\ingestion
python -m sources.supabase

# Then retry dbt
cd C:\Users\spits\data-platform\dbt\analytics_project
dbt run
```

### **dbt test failures**

```powershell
# Run tests with verbose output
dbt test --store-failures

# Check failure tables
docker exec -it airflow-postgres-1 psql -U airflow -d airflow
\dt dbt_test.*
SELECT * FROM dbt_test__audit.unique_stg_servicenow_incidents_incident_id;
```

## **6.5  Catalog UI Issues**

### **Frontend server won't start**

```powershell
# Check if port 8002 is already in use
netstat -ano | Select-String ":8002"

# Kill existing process if needed
Get-Process -Name python | Where-Object {$_.CommandLine -match "serve.py"} | Stop-Process -Force

# Try starting again
cd C:\Users\spits\data-platform\catalog-ui
python serve.py
```

### **Frontend loads but no assets display**

```powershell
# Check if backend API is running
try { 
  $r = Invoke-WebRequest -Uri "http://localhost:8001/assets" -UseBasicParsing
  $r.Content | ConvertFrom-Json | Measure-Object
} catch { 
  Write-Host "Backend API not responding - start catalog-api container"
}
```

### **Lineage tab shows no data**

**Cause:** Asset table_name doesn't match entry in `lineageFlows` object in index.html

**Fix:** Edit `index.html` around line 1340 and add entry to `lineageFlows` object:

```javascript
const lineageFlows = {
  'your_table_name': {
    stages: [
      { title: 'SOURCE', type: 'API', items: ['source/table'], icon: '📋', color: '#fef3c7' },
      { title: 'ORCHESTRATION', type: 'Airflow DAG', items: ['your_dag'], icon: '⚙️', color: '#bfdbfe' },
      { title: 'STORAGE', type: 'PostgreSQL', items: ['raw.schema.table'], icon: '🗄️', color: '#a5f3fc' },
      { title: 'TRANSFORMATION', type: 'dbt Model', items: ['your_model'], icon: '✨', color: '#fed7aa' }
    ]
  },
  // ... existing entries
};
```

### **Schema tab shows no columns**

**Cause:** Columns not included in API response or asset doesn't have column metadata

**Fix:** Verify backend seed_assets.py includes complete column definitions:

```python
# In catalog-api/seed/seed_assets.py
columns=[
    {"name": "column_1", "type": "uuid", "description": "Description..."},
    {"name": "column_2", "type": "text", "description": "Description..."},
    # ... etc
]
```

Then re-seed:

```powershell
docker exec catalog-api python seed/seed_assets.py
```

## **6.6  Quick Diagnostic Checklist**

Run through in order when pipeline is failing:

| # | Check | Command | Expected Result |
|:---|:---|:---|:---|
| 1 | Docker running | docker compose ps | 3 containers Up |
| 2 | Airflow UI accessible | Open http://localhost:8080 | Login page loads |
| 3 | PostgreSQL reachable | docker exec airflow-postgres-1 pg_isready -U airflow | accepting connections |
| 4 | Raw table exists | \dt raw.* in psql | raw.supabase_incidents listed |
| 5 | Ingestion script works | python -m sources.supabase (from ingestion folder) | Loaded N rows... |
| 6 | dbt connects | dbt debug (from analytics_project folder) | All checks passed |
| 7 | dbt models run | dbt run | PASS=5 ERROR=0 |
| 8 | dbt tests pass | dbt test | PASS>=15 ERROR=0 |
| 9 | Catalog UI responds | Open http://localhost:8002 | Assets list loads |
| 10 | Catalog API responds | curl http://localhost:8001/assets | Returns 5 assets |

---

# **Section 7 — Adding New Data Pipelines**

Follow these steps every time you need to add a new data source.

## **7.1  Overview of the Process**

1. Add credentials to ingestion/.env
2. Create the ingestion script in sources/
3. Test the script manually
4. Verify raw table in PostgreSQL
5. Create dbt staging model
6. Add data quality tests to schema.yml
7. Run `dbt run` and `dbt test`
8. Add task to Airflow DAG
9. Trigger manual run and confirm green
10. Add asset to catalog (optional)

## **7.2  Step 1 — Add Credentials**

```powershell
notepad C:\Users\spits\data-platform\ingestion\.env
```

Add a credential block:

```
# ── New Source Name ───────────────────────────────────────────────────
NEWSOURCE_HOST=your-host
NEWSOURCE_PORT=5432
NEWSOURCE_DB=your-database
NEWSOURCE_USER=your-username
NEWSOURCE_PASS="your password"
```

## **7.3  Step 2 — Create the Ingestion Script**

Use the template from catalog-api/seed/ or existing sources/ as a starting point.

Key pattern:
```python
def get_source_conn():
    """Return connection to source database"""
    return psycopg2.connect(
        host=os.getenv('NEWSOURCE_HOST'),
        port=int(os.getenv('NEWSOURCE_PORT', 5432)),
        dbname=os.getenv('NEWSOURCE_DB'),
        user=os.getenv('NEWSOURCE_USER'),
        password=os.getenv('NEWSOURCE_PASS'),
    )

def sync_table(table: str, updated_col: str, since: datetime):
    src = get_source_conn()
    dest = get_local_pg()
    
    # Pull changed records
    with src.cursor() as cur:
        cur.execute(f'SELECT * FROM {table} WHERE {updated_col} >= %s', (since,))
        # ... load and upsert logic
```

## **7.4  Steps 3-9 — Test & Deploy**

See Section 6.2 of the old operations guide for detailed step-by-step instructions on testing ingestion scripts, creating dbt models, adding tests, and integrating with Airflow.

---

# **Section 8 — Quick Reference Card**

## **8.1  Essential Commands**

```powershell
# ── START DATABASE & AIRFLOW ──────────────────────────────────────────
cd C:\Users\spits\data-platform\airflow
docker compose up -d

# ── START CATALOG UI ───────────────────────────────────────────────────
cd C:\Users\spits\data-platform\catalog-ui
python serve.py

# ── STOP EVERYTHING ───────────────────────────────────────────────────
docker compose down
# (and Ctrl+C the catalog-ui server)

# ── STATUS ────────────────────────────────────────────────────────────
docker compose ps

# ── VIEW LOGS ─────────────────────────────────────────────────────────
docker compose logs airflow-scheduler
docker compose logs airflow-webserver

# ── RESTART A SERVICE ────────────────────────────────────────────────
docker compose restart airflow-scheduler

# ── CONNECT TO POSTGRESQL ────────────────────────────────────────────
docker exec -it airflow-postgres-1 psql -U airflow -d airflow

# ── RUN INGESTION MANUALLY ───────────────────────────────────────────
cd C:\Users\spits\data-platform\ingestion
python -m sources.supabase

# ── RUN DBT MANUALLY ─────────────────────────────────────────────────
cd C:\Users\spits\data-platform\dbt\analytics_project
dbt run
dbt test
dbt run --select stg_servicenow_incidents

# ── TRIGGER AIRFLOW DAG ──────────────────────────────────────────────
docker exec airflow-airflow-scheduler-1 airflow dags trigger data_platform_pipeline
```

## **8.2  Access Points**

| Interface | URL / Address | Credentials |
|:---|:---|:---|
| Airflow UI | http://localhost:8080 | admin / admin |
| Catalog UI | http://localhost:8002 | (no auth) |
| Catalog API | http://localhost:8001 | (no auth) |
| PostgreSQL | localhost:5432 | airflow / airflow |
| DBeaver / pgAdmin | localhost:5432 | airflow / airflow |

## **8.3  Key File Locations**

| File | Location | What to Edit |
|:---|:---|:---|
| Airflow DAG | airflow\dags\data_pipeline.py | Add tasks, change schedule |
| Source credentials | ingestion\.env | Passwords, hostnames |
| DB connections | ingestion\utils\db.py | Connection helpers |
| Supabase script | ingestion\sources\supabase.py | Tables to sync |
| Staging models | dbt\analytics_project\models\staging\stg_*.sql | SQL transformations |
| Quality tests | dbt\analytics_project\models\staging\schema.yml | Add/remove tests |
| dbt connection | dbt\.dbt\profiles.yml | Database connection |
| Docker services | airflow\docker-compose.yml | Ports, volumes, images |
| Catalog UI | catalog-ui\index.html | Lineage flows, schema defaults |
| Catalog backend | catalog-api\seed\seed_assets.py | Add assets, columns |

## **8.4  Pipeline Schedule**

| Time (UTC) | Local (EST) | What Happens |
|:---|:---|:---|
| 12:00 AM | 7:00 PM | Pipeline runs: ingest + dbt run + dbt test |
| 6:00 AM | 1:00 AM | Pipeline runs: ingest + dbt run + dbt test |
| 12:00 PM | 7:00 AM | Pipeline runs: ingest + dbt run + dbt test |
| 6:00 PM | 1:00 PM | Pipeline runs: ingest + dbt run + dbt test |

*Adjust times for your timezone. Schedule in cron format: `0 */6 * * *`*

## **8.5  Power BI Connection Details**

PostgreSQL Connection:
- Server: localhost
- Port: 5432
- Database: airflow
- Username: airflow
- Password: airflow
- Schema: analytics (where staging tables live)

In Power BI:
1. Get Data → PostgreSQL database
2. Server: localhost, Database: airflow
3. Database authentication: airflow / airflow
4. Select tables from `analytics` schema

## **8.6  Data Flow Order**

```
Incident created (ServiceNow)
  ↓
Record created in Supabase database
  ↓
DAG Ingestion Task (Airflow) — every 6 hours
  ↓
Raw table populated (PostgreSQL raw schema)
  ↓
DAG dbt_run Task (Airflow)
  ↓
Staging & analytics tables created
  ↓
DAG dbt_test Task (Airflow)
  ↓
Data quality tests pass/fail
  ↓
Catalog UI displays asset (with lineage, schema, chat)
  ↓
Power BI dashboards refresh
  ↓
n8n chatbot queries data
```

---

**Document Version:** 2.0  
**Last Updated:** March 14, 2026  
**Next Review:** April 14, 2026
