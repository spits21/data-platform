**Data Platform**  
**Operations & Maintenance Guide**

Docker  •  Python Scripts  •  Airflow  •  dbt  •  PostgreSQL  •  Supabase  •  **AI Data Catalog**

*Design Reference  |  Daily Operations  |  Troubleshooting  |  Extending the Platform*

Version 1.1  —  March 12, 2026

# **Section 1 — Platform Overview**

This document is the authoritative operations reference for your local data platform. It covers the full architecture, daily startup and shutdown procedures, routine maintenance tasks, troubleshooting common failures, and step-by-step instructions for extending the platform with new data sources.

## **1.1  Purpose & Scope**

The platform serves as a central repository that ingests data from multiple source systems, transforms it into clean analytics-ready tables, and exposes that data to Power BI dashboards, AI agents, and an interactive AI-powered Data Catalog. It is designed to run on a local or on-premise machine with minimal operational overhead.

**Current data sources:**

* Supabase PostgreSQL database (incidents table — active)

* ServiceNow REST API (connector built, pending live credentials)

* MariaDB source databases (connector built, pending configuration)

**Current data outputs:**

* analytics.stg\_servicenow\_incidents — cleaned and deduplicated incidents view

* Power BI — ready to connect via local PostgreSQL

* AI Data Catalog — interactive UI with Claude Haiku 4.5 integration for intelligent data exploration

* AI agents — queryable via direct PostgreSQL connection or REST API

## **1.2  Architecture Diagram**

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
                                   │  writes to  
                    ┌──────────────▼──────────────┐  
                    │   PostgreSQL: raw schema     │  
                    │   raw.supabase\_incidents     │  
                    └──────────────┬──────────────┘  
                                   │  transformed by  
                    ┌──────────────▼──────────────┐  
                    │        dbt Core              │  
                    │   staging → analytics →      │  
                    │        reporting             │  
                    └──────────────┬──────────────┘  
                                   │  served to  
     ┌─────────────────────────────┼────────────────────┬──────────────┐  
     │                             │                    │              │  
 ┌───▼─────────┐      ┌───────────▼─────────┐  ┌──────▼──────┐  ┌───▼──────┐  
 │  Power BI   │      │  **AI Data Catalog** │  │  AI Agents  │  │   SQL    │  
 │ Dashboards  │      │ (NEW - Port 8002)    │  │  (REST API) │  │ Queries  │  
 └─────────────┘      │ Claude Haiku 4.5     │  └─────────────┘  └──────────┘  
                      │ UI + Chat + History  │  
                      └────────┬─────────────┘  
                               │  
                  ┌────────────▼────────────┐  
                  │   FastAPI Backend       │  
                  │   (Port 8001)           │  
                  │   Asset Registry        │  
                  │   SQL Executor          │  
                  └────────────┬────────────┘  
                               │  
                    ┌──────────▼──────────┐  
                    │  Apache Airflow      │  
                    │  Orchestrates all    │  
                    │  steps — every 6hrs  │  
                    └─────────────────────┘

## **1.3  Technology Stack**

| Component | Technology | Version | Role |
| :---- | :---- | :---- | :---- |
| Container Runtime | Docker Desktop | Latest | Hosts all services |
| Orchestration | Apache Airflow | 2.8.1 | Schedules and monitors pipelines |
| Metadata Database | PostgreSQL | 15 | Airflow metadata + data warehouse |
| Ingestion | Python Scripts | 3.13 | Pulls data from all sources |
| Transformation | dbt Core | 1.11.6 | SQL models and data quality tests |
| AI Catalog Backend | FastAPI | 0.109.0 | REST API, SQL execution, Claude integration |
| AI Catalog Frontend | Vanilla HTML/JS | ES6 | Interactive UI, asset browser, chat |
| AI Integration | Claude Haiku 4.5 | Latest | Intelligent data exploration via Anthropic SDK |
| BI Output | Power BI | Latest | Dashboards and reporting |
| Source DB | Supabase | Cloud | Primary data source (incidents) |

## **1.4  Database Schema Layout**

All data lives in a single PostgreSQL instance (the Airflow container). It is organized into four schemas representing the medallion data architecture:

| Schema | Purpose | Who Writes | Who Reads |
| :---- | :---- | :---- | :---- |
| raw.\* | Raw ingested data — exact copy from source, no changes | Python scripts | dbt staging models |
| staging.\* | Cleaned, typed, deduplicated data — one model per source | dbt | dbt analytics models |
| analytics.\* | Business logic, joins, aggregations | dbt | dbt reporting models, Power BI, AI Catalog |
| reporting.\* | Final materialized views — optimized for dashboards | dbt | Power BI, AI agents |

**Additional database for catalog metadata:**

| Database | Schema | Purpose | Who Writes | Who Reads |
| :---- | :---- | :---- | :---- | :---- |
| catalog_db | public | Catalog asset definitions, metadata, tags | Catalog API admin | Catalog API, Frontend UI |

## **1.5  File Structure Reference**

C:\\Users\\spits\\data-platform\\  
│  
├── airflow\\  
│   ├── dags\\  
│   │   └── data\_pipeline.py        ← Main Airflow DAG  
│   ├── logs\\                        ← Airflow runtime logs (auto-populated)  
│   ├── plugins\\                     ← Custom operators (currently empty)  
│   ├── .env                         ← Airflow + PostgreSQL credentials  
│   └── docker-compose.yml           ← All Docker service definitions  
│  
├── ingestion\\  
│   ├── sources\\  
│   │   ├── supabase.py              ← Supabase connector (ACTIVE)  
│   │   ├── servicenow.py            ← ServiceNow connector (built, inactive)  
│   │   └── mariadb.py               ← MariaDB connector (built, inactive)  
│   ├── utils\\  
│   │   └── db.py                    ← Shared DB connection helpers  
│   └── .env                         ← All source system credentials  
│  
├── dbt\\  
│   ├── .dbt\\  
│   │   └── profiles.yml             ← dbt database connection config  
│   └── analytics\_project\\  
│       ├── dbt\_project.yml          ← dbt project config  
│       └── models\\  
│           └── staging\\  
│               ├── stg\_servicenow\_incidents.sql  ← Staging model  
│               └── schema.yml                   ← Data quality tests  
│  
├── **catalog-api/** ← **NEW - AI Data Catalog Backend**  
│   ├── app\\  
│   │   ├── main.py                  ← FastAPI entry point  
│   │   ├── config.py                ← Settings and environment variables  
│   │   ├── database.py              ← SQLAlchemy async setup  
│   │   ├── itsm_reader.py           ← Read-only asyncpg for SQL execution  
│   │   ├── models\\  
│   │   │   └── asset.py             ← CatalogAsset ORM model  
│   │   ├── schemas\\  
│   │   │   └── asset.py             ← Pydantic request/response types  
│   │   ├── services\\  
│   │   │   ├── claude_service.py    ← Claude Haiku integration & agentic loop  
│   │   │   └── sql_executor.py      ← Safe read-only SQL validator & executor  
│   │   └── routers\\  
│   │       ├── assets.py            ← GET/POST /assets endpoints  
│   │       ├── ai_lab.py            ← POST /ai-lab/chat endpoint  
│   │       └── mcp.py               ← MCP manifest endpoints  
│   ├── Dockerfile                   ← Container build  
│   ├── requirements.txt             ← Python dependencies  
│   ├── ARCHITECTURE.md              ← System design documentation  
│   └── seed/  
│       └── seed_assets.py           ← Initialize catalog metadata  
│  
└── **catalog-ui/** ← **NEW - AI Data Catalog Frontend**  
    └── index.html                   ← Single-file HTML UI (600 lines)  
                                        • Asset search & filtering  
                                        • Responsive detail modals  
                                        • Claude AI chat interface  
                                        • SQL execution history tracking

# **Section 2 — Daily Operations**

## **2.1  Starting the Platform**

The platform consists of Docker containers that need to be started each time your machine reboots or Docker Desktop is restarted.

1. Open Docker Desktop from the Start menu and wait for it to show Running in the system tray.

2. Open PowerShell and navigate to the Airflow directory:

cd C:\\Users\\spits\\data-platform\\airflow

3. Start all Airflow containers in the background:

docker compose up \-d

4. Verify all containers are healthy:

docker compose ps

You should see four containers with status Up or healthy (including the new catalog-api):

NAME                          STATUS  
airflow-postgres-1            Up (healthy)  
airflow-airflow-webserver-1   Up (healthy)  
airflow-airflow-scheduler-1   Up  
airflow-catalog-api-1         Up

5. Open the Airflow UI in your browser:

http://localhost:8080

6. Log in with username: admin  /  password: admin and confirm the data\_platform\_pipeline DAG is active (toggle is blue/on).

7. **NEW — Open the AI Data Catalog UI in your browser:**

http://localhost:8002

The catalog should display all registered assets and be ready for queries.

*💡  The pipeline runs automatically every 6 hours once the DAG is unpaused, and the Catalog API runs as a background service. You do not need to trigger anything manually during normal operations.*

## **2.2  Stopping the Platform**

8. Open PowerShell and navigate to the Airflow directory:

cd C:\\Users\\spits\\data-platform\\airflow

9. Stop all containers gracefully:

docker compose down

10. Close Docker Desktop from the system tray to free all remaining memory.

*⚠️  Running docker compose down stops containers but preserves all data in the postgres\_data volume and catalog_db. Your data is safe.*

## **2.3  Checking Pipeline Health**

The fastest way to check if your pipeline is healthy is the Airflow UI:

11. Open http://localhost:8080 and log in.

12. Find data\_platform\_pipeline in the DAG list.

13. Check the Recent Tasks column — you want to see green circles only.

14. Click on the DAG name, then click Graph to see the last run visually. All three boxes should be dark green.

15. Click on any task box then click Logs to read detailed output for that task.

| Task Color | Meaning | Action Required |
| :---- | :---- | :---- |
| Dark Green | Success — completed without errors | None |
| Light Green | Running — currently executing | Wait and monitor |
| Yellow | Queued — waiting to start | Wait, check scheduler if stuck \> 5 min |
| Orange | Up for retry — failed, retrying | Check logs after all retries complete |
| Red | Failed — all retries exhausted | Check logs and fix immediately |
| Gray | Skipped — did not run | Check upstream task for failures |

## **2.4  Manually Triggering a Pipeline Run**

Use this when you need fresh data outside the normal 6-hour schedule — for example before an important meeting or after adding a new data source.

16. Open http://localhost:8080 and log in.

17. Find data\_platform\_pipeline in the DAG list.

18. Click the play button (▶) on the right side of the row.

19. Select Trigger DAG from the dropdown.

20. Click on the DAG name then click Graph to watch the run in real time.

*💡  You can also trigger a run from PowerShell without opening the browser: docker exec airflow-airflow-scheduler-1 airflow dags trigger data\_platform\_pipeline*

## **2.5  Querying Your Data**

Three ways to query your clean data depending on your preference:

### **Via Docker (no install required)**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
   
\-- Then run any SQL:  
SELECT count(\*) FROM analytics.stg\_servicenow\_incidents;  
SELECT state, count(\*) FROM analytics.stg\_servicenow\_incidents GROUP BY state;  
\\q  \-- to exit

### **Via DBeaver (recommended GUI tool)**

Connect DBeaver to: Host \= localhost, Port \= 5432, Database \= airflow, User \= airflow, Password \= airflow

### **Via AI Data Catalog (NEW — recommended for exploration)**

Open http://localhost:8002 and:
1. Browse assets in the left sidebar
2. Click on an asset to see its columns and metadata
3. Ask Claude a question in the chat box (e.g., "How many incidents are in the open state?")
4. Claude will generate and execute SQL, show results, and provide analysis
5. View all executed queries in the SQL History section

### **Useful Queries**

\-- Row counts across all schemas  
SELECT schemaname, tablename, n\_live\_tup as row\_count  
FROM pg\_stat\_user\_tables  
ORDER BY schemaname, tablename;  
   
\-- Check when raw data was last synced  
SELECT max(updated\_at) as last\_updated FROM raw.supabase\_incidents;  
   
\-- Incident breakdown by state  
SELECT state, count(\*) as total  
FROM analytics.stg\_servicenow\_incidents  
GROUP BY state ORDER BY total DESC;  
   
\-- Incident breakdown by priority  
SELECT priority, count(\*) as total  
FROM analytics.stg\_servicenow\_incidents  
GROUP BY priority ORDER BY total DESC;  
   
\-- Most recently updated incidents  
SELECT incident\_number, short\_description, state, updated\_at  
FROM analytics.stg\_servicenow\_incidents  
ORDER BY updated\_at DESC LIMIT 20;

---

# **Section 2.6 — Using the AI Data Catalog (NEW)**

## **2.6.1  Catalog UI Overview**

The AI Data Catalog at http://localhost:8002 provides an interactive interface to explore and query your data assets using natural language.

**Main Sections:**

* **Asset Browser (Left)** — Lists all registered catalog assets with search/filter
* **Asset Detail Modal (Center)** — View columns, types, descriptions, metadata tags
* **Claude Chat (Bottom)** — Ask questions about the asset and Claude will generate SQL
* **SQL History (Right)** — View all queries executed with timestamps and results

## **2.6.2  Searching Assets**

1. Open http://localhost:8002
2. Type in the search box to filter assets by name
3. Click on an asset card to open its detail modal

Available assets:
* stg\_servicenow\_incidents (from Supabase)
* stg\_servicenow\_configuration\_items (from Supabase)
* incidents\_with\_configuration\_items (dbt mart)

## **2.6.3  Asking Claude Questions**

Once you click an asset detail:

1. Scroll to the "Ask Claude" section at the bottom
2. Type a natural language question about the data, e.g.:
   * "How many incidents are open?"
   * "Show me the top 5 incident priorities"
   * "What's the most recent incident?"
3. Press Enter or click Send
4. Claude will:
   - Generate a SQL query based on your question
   - Execute it safely (read-only, limited to 500 rows)
   - Display results in a formatted table
   - Provide analysis and insights

## **2.6.4  Viewing Query History**

After asking Claude questions, all executed SQL appears in the "SQL History" section. You can:
* See the exact query Claude generated
* View timestamp of execution
* Copy queries for use in DBeaver or psql
* Expand/collapse query details

## **2.6.5  Multi-Turn Conversations**

The chat maintains conversation history within a session:
1. Ask a question
2. Claude responds with a query result
3. Ask a follow-up question referencing the previous context
4. Claude will understand and generate appropriate follow-up queries

*Tip: Refresh the page to start a new conversation.*

---

# **Section 3 — Pipeline Design Details**

## **3.1  Ingestion Layer — How Python Scripts Work**

Each ingestion script follows the same pattern: connect to source, pull records changed since the last run, write to raw schema using an upsert. This incremental approach means only new or changed records are processed on each run — not the entire dataset.

| Script | Source | Target Table | Incremental Column | Status |
| :---- | :---- | :---- | :---- | :---- |
| sources/supabase.py | Supabase PostgreSQL | raw.supabase\_incidents | updated\_at | Active |
| sources/servicenow.py | ServiceNow REST API | raw.servicenow\_incidents | sys\_updated\_on | Built — inactive |
| sources/mariadb.py | MariaDB database | raw.mariadb\_\<table\> | updated\_at | Built — inactive |

The incremental sync window is set to 7 hours (1 hour overlap beyond the 6-hour schedule) to ensure no records are missed if a run is delayed:

\# In data\_pipeline.py DAG  
since=datetime.now(timezone.utc) \- timedelta(hours=7)  \# 7hr window for safety

The shared upsert function in utils/db.py handles duplicate prevention. If a record already exists in the raw table, it updates it rather than inserting a duplicate:

INSERT INTO raw.supabase\_incidents (...) VALUES ...  
ON CONFLICT (id) DO UPDATE SET ..., synced\_at \= NOW()

## **3.2  Transformation Layer — How dbt Works**

dbt runs SQL transformations in dependency order. Each model reads from the previous layer and produces a new table or view. Models are stored as .sql files and executed by running dbt run.

| Model | Schema | Type | Source | Description |
| :---- | :---- | :---- | :---- | :---- |
| stg\_servicenow\_incidents | analytics | View | raw.supabase\_incidents | Deduplicated, cleaned incidents with proper types |

**The staging model does three important things:**

* Deduplication — uses ROW\_NUMBER() to keep only the most recent version of each incident when duplicates exist in the source

* Type casting — converts text columns to proper types (timestamps, integers)

* Null filtering — removes records with null primary keys that would break downstream models

**Data quality tests run automatically after every dbt run and will fail the pipeline if violations are found:**

Current tests (schema.yml):  
  incident\_id   → unique, not\_null  
  incident\_number → not\_null  
  state         → not\_null  
  created\_at    → not\_null

## **3.3  Orchestration Layer — How Airflow Works**

Airflow runs the data\_platform\_pipeline DAG on a cron schedule of 0 \*/6 \* \* \* meaning it triggers at midnight, 6am, noon, and 6pm every day.

**Task execution order:**

ingest\_supabase  ──►  dbt\_run  ──►  dbt\_test  
   
Each task must succeed before the next one starts.  
If ingest\_supabase fails, dbt\_run and dbt\_test are skipped.  
If dbt\_run fails, dbt\_test is skipped.  
Failed tasks retry up to 2 times with a 5-minute delay between attempts.

| DAG Setting | Value | Effect |
| :---- | :---- | :---- |
| schedule\_interval | 0 \*/6 \* \* \* | Runs at 12am, 6am, 12pm, 6pm daily |
| retries | 2 | Each task retries twice on failure |
| retry\_delay | 5 minutes | Waits 5 minutes between retries |
| catchup | False | Does not backfill missed runs |
| start\_date | 2025-01-01 | DAG activation reference date |

## **3.4  AI Data Catalog Layer — How the Catalog Works (NEW)**

The AI Data Catalog adds an intelligent query layer on top of the data warehouse.

**Architecture:**

* **Backend (Port 8001):** FastAPI service running in Docker
  - Manages CatalogAsset metadata (tables, columns, descriptions, tags)
  - Receives natural language queries from the frontend
  - Generates SQL using Claude Haiku 4.5
  - Executes queries safely (read-only, max 500 rows)
  - Returns results with metadata

* **Frontend (Port 8002):** Static HTML + JavaScript served via Python HTTP server
  - Asset browser with search and filtering
  - Detail modals showing columns and metadata
  - Chat interface for conversing with Claude
  - SQL history and execution logs

* **Claude Integration:** Anthropic SDK (Claude Haiku 4.5)
  - Receives context: asset definition, column names/types, user query
  - Generates SELECT queries (no DML/DDL)
  - Executes through safe SQL executor
  - Returns natural language analysis of results

**Data Flow:**

1. User opens http://localhost:8002
2. Frontend fetches asset list from `/assets` endpoint
3. User clicks an asset and searches for details via `/assets/{id}`
4. User asks a question in the chat box
5. Frontend POSTs to `/ai-lab/chat` with asset_id + message
6. Backend sends context to Claude Haiku 4.5
7. Claude generates a SQL query
8. Backend validates query (6 safety rules)
9. Backend executes via read-only asyncpg connection
10. Results returned to frontend
11. Claude provides natural language summary
12. Query logged in history

**Safety Controls:**

- Query must be SELECT (no INSERT/UPDATE/DELETE/DROP/ALTER)
- Query must reference the specified table
- Max 500 rows returned
- Read-only transaction enforced at database level
- All queries logged for audit trail

# **Section 4 — Routine Maintenance**

## **4.1  Weekly Tasks**

### **Review Airflow Run History**

23. Open http://localhost:8080 and click on data\_platform\_pipeline.

24. Click the Calendar view to see a heatmap of run success and failures over the past week.

25. Investigate any red cells by clicking on them and reviewing the logs.

### **Check Catalog API Health (NEW)**

docker exec airflow-catalog-api-1 curl \-s http://localhost:8001/health

Should return:

{"status":"healthy","service":"catalog-api"}

If the catalog-api container is not running:

docker compose restart catalog-api

### **Check Disk Usage**

Airflow logs accumulate over time. Check Docker disk usage weekly:

docker system df

If disk usage is high, clean up old logs and unused images:

\# Remove unused Docker images, containers, and networks  
docker system prune  
   
\# Remove Airflow logs older than 30 days  
\# Run from PowerShell:  
Get-ChildItem C:\\Users\\spits\\data-platform\\airflow\\logs \-Recurse |  
  Where-Object { $\_.LastWriteTime \-lt (Get-Date).AddDays(-30) } |  
  Remove-Item \-Force

### **Verify Data Freshness**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow \-c  
"SELECT max(updated\_at) as last\_record, max(synced\_at) as last\_sync  
 FROM raw.supabase\_incidents;"

### **Verify Catalog Metadata is Current (NEW)**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d catalog_db \-c  
"SELECT name, table_name, row_count, updated_at FROM catalog_assets ORDER BY updated_at DESC;"

## **4.2  Monthly Tasks**

### **Update Python Dependencies**

pip install \--upgrade dbt-core dbt-postgres psycopg2-binary  
pip install \--upgrade requests pandas python-dotenv pymysql anthropic  
   
\# Verify dbt still works after upgrade  
cd C:\\Users\\spits\\data-platform\\dbt\\analytics\_project  
dbt debug

### **Update Docker Images**

cd C:\\Users\\spits\\data-platform\\airflow  
   
\# Pull latest Airflow image (and catalog-api rebuilds automatically)  
docker compose pull  
   
\# Restart with new images  
docker compose down  
docker compose up \-d

*⚠️  Always test a manual DAG run and verify catalog-api health after updating Docker images to confirm nothing broke.*

### **Review and Vacuum PostgreSQL**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
   
\-- Check table sizes  
SELECT schemaname, tablename,  
       pg\_size\_pretty(pg\_total\_relation\_size(schemaname||'.'||tablename)) as size  
FROM pg\_tables  
WHERE schemaname IN ('raw','staging','analytics','reporting')  
ORDER BY pg\_total\_relation\_size(schemaname||'.'||tablename) DESC;  
   
\-- Run vacuum to reclaim space  
VACUUM ANALYZE raw.supabase\_incidents;  
\\q

### **Backup Catalog Metadata (NEW)**

Before making major changes to catalog assets, backup the metadata:

\# Backup catalog_db schema  
docker exec airflow-postgres-1 pg\_dump \-U airflow \-d catalog_db \-Fc \> C:\\Users\\spits\\data-platform\\backups\\catalog\_db\_$(Get-Date -f yyyyMMdd).dump

Then verify you can restore:

\# To restore (if needed):  
docker exec \-i airflow-postgres-1 pg\_restore \-U airflow \-d catalog_db C:\\Users\\spits\\data-platform\\backups\\catalog\_db\_YYYYMMDD.dump

## **4.3  Managing the profiles.yml After Container Restarts**

If you have not yet added profiles.yml as a permanent volume mount, it will be lost every time containers are recreated. To make it permanent, add this to your docker-compose.yml volumes section:

\# In airflow/docker-compose.yml under x-airflow-common volumes:  
    \- ../dbt/.dbt:/home/airflow/.dbt

Then restart:

docker compose down && docker compose up \-d

If you ever need to recreate it manually inside the container:

docker exec airflow-airflow-scheduler-1 mkdir \-p /home/airflow/.dbt  
docker exec airflow-airflow-scheduler-1 bash \-c "cat \> /home/airflow/.dbt/profiles.yml \<\< 'EOF'  
analytics\_project:  
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

---

# **Section 5 — Troubleshooting**

## **5.1  Docker & Container Issues**

### **Containers not starting or keep restarting**

\# Check container status  
docker compose ps  
   
\# View startup logs for a specific container  
docker compose logs airflow-webserver  
docker compose logs airflow-scheduler  
docker compose logs postgres  
docker compose logs catalog-api   \# NEW

Common causes and fixes:

* Not enough memory — increase Docker Desktop memory to at least 8 GB under Settings → Resources → Advanced

* Port conflict — another app is using port 8080, 5432, 8001, or 8002. Stop the conflicting app or change the port in docker-compose.yml

* Volume permissions — on Windows, ensure your data-platform folder is shared in Docker Desktop under Settings → Resources → File Sharing

### **Cannot connect to Docker daemon**

Docker Desktop is not running. Open Docker Desktop from the Start menu and wait for it to show Running before running docker compose commands.

## **5.2  Airflow Issues**

### **DAG not appearing in the UI**

\# Check if the DAG file has syntax errors  
docker exec airflow-airflow-scheduler-1 python /opt/airflow/dags/data\_pipeline.py  
   
\# Check scheduler logs for import errors  
docker compose logs airflow-scheduler | grep ERROR

### **Task stuck in queued state**

\# Restart the scheduler  
docker compose restart airflow-scheduler

### **All tasks failing after machine restart**

The profiles.yml was lost when the container was recreated. Recreate it:

docker exec airflow-airflow-scheduler-1 mkdir \-p /home/airflow/.dbt  
docker exec airflow-airflow-scheduler-1 bash \-c "cat \> /home/airflow/.dbt/profiles.yml \<\< 'EOF'  
analytics\_project:  
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

## **5.3  Ingestion Script Issues**

### **Connection refused to PostgreSQL**

Cause: The LOCAL\_PG\_HOST in ingestion/.env is set to localhost but the script is running inside Docker where the correct hostname is postgres.

\# Verify ingestion/.env  
type C:\\Users\\spits\\data-platform\\ingestion\\.env  
   
\# Should show:  
LOCAL\_PG\_HOST=postgres

### **Cannot connect to Supabase**

Run a connection test:

cd C:\\Users\\spits\\data-platform\\ingestion  
python \-c "from utils.db import get\_supabase; c \= get\_supabase(); print('Connected OK'); c.close()"

Common causes:

* Wrong host in .env — verify against Supabase dashboard Settings → Database

* Password with special characters — wrap the value in double quotes in .env

* Network issue — ping aws-0-us-west-2.pooler.supabase.com from PowerShell

### **No rows synced — script runs but raw table is empty**

The incremental window is too narrow — no records have been updated in the last 7 hours. To do a full reload:

\# Temporarily change the since date in sources/supabase.py  
\# Find the last line and change to:  
run\_all(since=datetime(2000, 1, 1, tzinfo=timezone.utc))  
   
\# Run the script  
python \-m sources.supabase  
   
\# Then change it back to:  
run\_all(since=datetime.now(timezone.utc) \- timedelta(hours=6))

### **ModuleNotFoundError: No module named 'utils'**

You are running the script from the wrong directory or without the \-m flag:

\# Always run from the ingestion directory with \-m flag  
cd C:\\Users\\spits\\data-platform\\ingestion  
python \-m sources.supabase

## **5.4  dbt Issues**

### **profiles.yml not found**

\# Verify profiles.yml exists on your Windows machine  
type C:\\Users\\spits\\data-platform\\dbt\\.dbt\\profiles.yml  
   
\# Verify dbt can connect  
cd C:\\Users\\spits\\data-platform\\dbt\\analytics\_project  
dbt debug

### **Relation does not exist error**

The raw table hasn't been created yet — the ingestion script needs to run first:

cd C:\\Users\\spits\\data-platform\\ingestion  
python \-m sources.supabase  
   
\# Then retry dbt  
cd C:\\Users\\spits\\data-platform\\dbt\\analytics\_project  
dbt run

### **dbt test failures**

Check what data is actually failing the test:

\# Run tests with verbose output  
dbt test \--store-failures  
   
\# Then query the failures table in PostgreSQL  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
\\dt dbt\_test.\*   \-- lists all failure tables  
SELECT \* FROM dbt\_test\_\_audit.unique\_stg\_servicenow\_incidents\_incident\_id;

## **5.5  AI Data Catalog Issues (NEW)**

### **Catalog UI shows "Error loading assets"**

The frontend cannot connect to the backend. Check:

\# 1. Backend is running  
docker ps | grep catalog-api

If not running:

docker compose restart catalog-api

\# 2. CORS is configured correctly (should allow localhost:8002)  
docker exec airflow-catalog-api-1 cat /app/app/main.py | grep -A 10 "allow_origins"

\# 3. Backend is responding  
curl http://localhost:8001/health

Should return:

{"status":"healthy","service":"catalog-api"}

### **Claude returns "table does not exist"**

The catalog metadata references a table that doesn't exist in the database. This can happen if:

* The asset was manually added but the source table hasn't been created yet
* The table name in the metadata is incorrect
* The ingestion script hasn't run yet

Verify the table exists:

docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
SELECT \* FROM staging.stg_servicenow_incidents LIMIT 1;

If empty, run the ingestion:

cd C:\\Users\\spits\\data-platform\\ingestion  
python \-m sources.supabase

### **Claude generates invalid SQL**

Claude generates queries based on column metadata in the catalog. If the metadata is incorrect:

\# Check the asset definition  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d catalog_db  
SELECT name, columns::text FROM catalog_assets WHERE table_name = 'stg_servicenow_incidents';  
\\q

\# Verify actual table columns  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
\\d staging.stg_servicenow_incidents

If they don't match, update the catalog metadata (see Section 6.3 below).

### **Frontend won't load at http://localhost:8002**

The Python HTTP server serving the HTML isn't running. Check:

\# Is the server running?  
netstat -ano | findstr :8002

If not, start it:

cd C:\\Users\\spits\\data-platform\\catalog-ui  
python -m http.server 8002 --bind 127.0.0.1

## **5.6  Quick Diagnostic Checklist**

Run through this checklist in order when the pipeline is failing:

| \# | Check | Command | Expected Result |
| :---- | :---- | :---- | :---- |
| 1 | Docker running | docker compose ps | 4 containers Up |
| 2 | Airflow UI accessible | Open http://localhost:8080 | Login page loads |
| 3 | Catalog UI accessible | Open http://localhost:8002 | Asset list displays |
| 4 | PostgreSQL reachable | docker exec airflow-postgres-1 pg\_isready \-U airflow | accepting connections |
| 5 | Raw table exists | \\dt raw.\* in psql | raw.supabase\_incidents listed |
| 6 | Catalog API healthy | curl http://localhost:8001/health | Returns healthy status |
| 7 | Ingestion script works | python \-m sources.supabase (from ingestion folder) | Loaded N rows... |
| 8 | dbt connects | dbt debug (from analytics\_project folder) | All checks passed |
| 9 | dbt models run | dbt run | PASS=1 ERROR=0 |
| 10 | dbt tests pass | dbt test | PASS=4 ERROR=0 |

---

# **Section 6 — Adding New Data Pipelines & Catalog Items**

## **6.1  Two Types of Additions**

There are two separate but related tasks:

1. **Adding a new DATA SOURCE** — create ingestion script, dbt model, add to Airflow DAG
2. **Adding a new CATALOG ASSET** — register an existing table in the AI Data Catalog so users can query it

This section covers both.

## **6.2  Adding a New Data Source — Overview of the Process**

Follow these steps every time you need to add a new data source to the platform. The process is the same regardless of the source type.

Step 1 — Add credentials to ingestion/.env  
Step 2 — Create the ingestion script in sources/  
Step 3 — Test the script manually  
Step 4 — Verify the raw table was created in PostgreSQL  
Step 5 — Create a dbt staging model  
Step 6 — Add data quality tests to schema.yml  
Step 7 — Run dbt run and dbt test  
Step 8 — Add the new task to the Airflow DAG  
Step 9 — Trigger a manual run and confirm green

## **6.3  Step 1 — Add Credentials**

Open ingestion/.env and add a new block for your source:

notepad C:\\Users\\spits\\data-platform\\ingestion\\.env

Add credentials following this pattern:

\# ── New Source Name ───────────────────────────────────────────────────  
NEWSOURCE\_HOST=your-host  
NEWSOURCE\_PORT=5432  
NEWSOURCE\_DB=your-database  
NEWSOURCE\_USER=your-username  
NEWSOURCE\_PASS="your password"

## **6.4  Step 2 — Create the Ingestion Script**

Create a new file in ingestion/sources/. Use this template as your starting point — replace all YOUR\_\* placeholders:

notepad C:\\Users\\spits\\data-platform\\ingestion\\sources\\your\_source.py

Paste and customize this template:

\# ingestion/sources/your\_source.py  
import os, logging  
import psycopg2  
from datetime import datetime, timedelta, timezone  
from psycopg2.extras import execute\_values  
from utils.db import get\_local\_pg, ensure\_schema  
from dotenv import load\_dotenv  
load\_dotenv()  
log \= logging.getLogger(\_\_name\_\_)  
   
\# ── Configure your source tables here ────────────────────────────────  
SYNC\_TABLES \= \[  
    {'table': 'your\_table\_name', 'updated\_col': 'updated\_at'},  
    \# Add more tables as needed  
\]  
   
def get\_source\_conn():  
    """Return a connection to your source database"""  
    return psycopg2.connect(   \# swap for pymysql if MariaDB/MySQL  
        host=os.getenv('NEWSOURCE\_HOST'),  
        port=int(os.getenv('NEWSOURCE\_PORT', 5432)),  
        dbname=os.getenv('NEWSOURCE\_DB'),  
        user=os.getenv('NEWSOURCE\_USER'),  
        password=os.getenv('NEWSOURCE\_PASS'),  
        \# sslmode='require'   \# uncomment for cloud databases  
    )  
   
def sync\_table(table: str, updated\_col: str, since: datetime):  
    src  \= get\_source\_conn()  
    dest \= get\_local\_pg()  
    ensure\_schema(dest, 'raw')  
   
    \# Pull changed records from source  
    with src.cursor() as cur:  
        cur.execute(f'SELECT \* FROM {table} WHERE {updated\_col} \>= %s', (since,))  
        cols \= \[d\[0\] for d in cur.description\]  
        rows \= \[dict(zip(cols, row)) for row in cur.fetchall()\]  
   
    if not rows:  
        log.info(f'No new rows in {table} since {since}')  
        src.close(); dest.close()  
        return 0  
   
    \# Create destination table if it doesn't exist  
    col\_defs \= ', '.join(\[f'{c} TEXT' for c in cols\])  
    dest.cursor().execute(  
        f'CREATE TABLE IF NOT EXISTS raw.newsource\_{table} ({col\_defs})'  
    )  
    dest.commit()  
   
    \# Load records  
    vals \= \[tuple(str(r\[c\]) if r\[c\] is not None else None for c in cols) for r in rows\]  
    with dest.cursor() as cur:  
        execute\_values(cur,  
            f'INSERT INTO raw.newsource\_{table} ({chr(44).join(cols)}) VALUES %s',  
            vals  
        )  
    dest.commit()  
    log.info(f'Loaded {len(rows)} rows into raw.newsource\_{table}')  
    src.close(); dest.close()  
    return len(rows)  
   
def run\_all(since: datetime):  
    for cfg in SYNC\_TABLES:  
        sync\_table(cfg\['table'\], cfg\['updated\_col'\], since)  
   
if \_\_name\_\_ \== '\_\_main\_\_':  
    \# Use old date for first full load, then switch to rolling window  
    run\_all(since=datetime(2000, 1, 1, tzinfo=timezone.utc))

## **6.5  Step 3 & 4 — Test the Script and Verify the Table**

\# Run the script manually first  
cd C:\\Users\\spits\\data-platform\\ingestion  
python \-m sources.your\_source  
   
\# Verify the raw table was created  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
\\dt raw.\*  
SELECT count(\*) FROM raw.newsource\_your\_table\_name;  
SELECT \* FROM raw.newsource\_your\_table\_name LIMIT 5;  
\\q

Once data is confirmed, update the since date in the script to use the rolling window:

\# Change the last line back to rolling window  
run\_all(since=datetime.now(timezone.utc) \- timedelta(hours=6))

## **6.6  Step 5 — Create the dbt Staging Model**

Create a new SQL file in the staging models folder. The filename should match the table name:

notepad C:\\Users\\spits\\data-platform\\dbt\\analytics\_project\\models\\staging\\stg\_newsource\_your\_table.sql

Use this template — replace column names with your actual columns from Step 4:

\-- models/staging/stg\_newsource\_your\_table.sql  
with source as (  
    select \* from raw.newsource\_your\_table\_name  
),  
deduplicated as (  
    select \*,  
        row\_number() over (  
            partition by id          \-- replace with your primary key column  
            order by updated\_at desc \-- replace with your timestamp column  
        ) as row\_num  
    from source  
    where id is not null             \-- replace with your primary key column  
),  
cleaned as (  
    select  
        id              as record\_id,       \-- rename to meaningful names  
        name            as record\_name,  
        status          as status,  
        created\_at::timestamp as created\_at,  
        updated\_at::timestamp as updated\_at  
    from deduplicated  
    where row\_num \= 1  
)  
select \* from cleaned

## **6.7  Step 6 — Add Data Quality Tests**

Open schema.yml and add a new model block for your new staging model:

notepad C:\\Users\\spits\\data-platform\\dbt\\analytics\_project\\models\\staging\\schema.yml

Add this block inside the models: list (keep existing models, just add below):

  \- name: stg\_newsource\_your\_table  
    description: Cleaned data from New Source your\_table\_name  
    columns:  
      \- name: record\_id  
        description: Unique record identifier  
        tests:  
          \- unique  
          \- not\_null  
      \- name: record\_name  
        tests:  
          \- not\_null  
      \- name: created\_at  
        tests:  
          \- not\_null

## **6.8  Step 7 — Run dbt**

cd C:\\Users\\spits\\data-platform\\dbt\\analytics\_project  
   
\# Run only the new model first to isolate any issues  
dbt run \--select stg\_newsource\_your\_table  
   
\# Run its tests  
dbt test \--select stg\_newsource\_your\_tabledbt  
   
\# Once clean, run everything together  
dbt run  
dbt test

## **6.9  Step 8 — Add to the Airflow DAG**

Open the DAG file and add a new ingest task plus wire it into the execution order:

notepad C:\\Users\\spits\\data-platform\\airflow\\dags\\data\_pipeline.py

Add a new task function and PythonOperator (after the existing ingest\_supabase block):

    def run\_newsource():  
        from sources.your\_source import run\_all  
        return run\_all(since=datetime.now(timezone.utc) \- timedelta(hours=7))  
   
    ingest\_newsource \= PythonOperator(  
        task\_id='ingest\_newsource',  
        python\_callable=run\_newsource,  
    )

Update the execution order line at the bottom to include the new task:

\# Before (single source):  
ingest\_supabase \>\> dbt\_run \>\> dbt\_test  
   
\# After (multiple sources running in parallel):  
\[ingest\_supabase, ingest\_newsource\] \>\> dbt\_run \>\> dbt\_test

*💡  The bracket syntax runs all ingest tasks simultaneously before dbt starts — saving time when you have multiple sources.*

## **6.10  Step 9 — Confirm in Airflow**

26. Open http://localhost:8080 — the DAG should update automatically within 30 seconds.

27. Click on data\_platform\_pipeline to confirm the new task appears in the Graph view.

28. Click the play button and select Trigger DAG to run manually.

29. Watch all tasks turn green — your new pipeline is live.

---

# **Section 6.11 — Adding New Catalog Items (NEW)**

Once you have a table in the data warehouse (whether freshly ingested or an existing table), you can register it in the AI Data Catalog so users can query it with Claude.

## **6.11.1  When to Add a Catalog Item**

Add a catalog item any time you have:
- A new dbt model that's ready for end-users
- An existing analytics table that wasn't previously documented
- A new mart or reporting view
- Any table users should be able to explore with Claude

## **6.11.2  Registering a New Asset**

### **Method 1: Via API (Recommended for automation)**

POST to the `/assets` endpoint:

curl \-X POST http://localhost:8001/assets \-H "Content-Type: application/json" \-d '{  
  "name": "stg_new_table",  
  "display_name": "New Source Table",  
  "description": "Description of what this table contains",  
  "schema_name": "analytics",  
  "table_name": "stg_new_table",  
  "database": "airflow",  
  "source_system": "CUSTOM",  
  "columns": \[  
    {  
      "name": "id",  
      "type": "uuid",  
      "description": "Primary key",  
      "ai_tags": \["join_key", "dedup"\]  
    },  
    {  
      "name": "name",  
      "type": "text",  
      "description": "Record name",  
      "ai_tags": \["NLP", "embedding"\]  
    }  
  \],  
  "tags": \["new-source", "analytics"\],  
  "owner": "data-team"  
}'

### **Method 2: Via Database Insert (Manual)**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d catalog_db

Then insert directly:

INSERT INTO catalog_assets (  
  name, display_name, description, schema_name, table_name, database,  
  source_system, columns, tags, owner, row_count, pipeline_status  
) VALUES (  
  'stg_new_table',  
  'New Source Table',  
  'Description of what this table contains',  
  'analytics',  
  'stg_new_table',  
  'airflow',  
  'CUSTOM',  
  '[{"name": "id", "type": "uuid", "description": "Primary key"},  
    {"name": "name", "type": "text", "description": "Record name"}]'::jsonb,  
  '{"new-source","analytics"}'::text\[\],  
  'data-team',  
  NULL,  
  'UNKNOWN'  
);

\\q

## **6.11.3  Verify the Asset Appears in the Catalog**

1. Open http://localhost:8002
2. Search for your new asset name in the search box
3. Click to open the detail modal
4. Verify all columns are showing correctly
5. Try asking Claude a question about the data

## **6.11.4  Updating Asset Metadata**

If you need to change descriptions, tags, or column info:

### **Via API (PUT endpoint):**

curl \-X PUT http://localhost:8001/assets/1 \-H "Content-Type: application/json" \-d '{  
  "display_name": "Updated Display Name",  
  "description": "Updated description",  
  "tags": \["tag1", "tag2"\]  
}'

### **Via Database (Direct SQL):**

docker exec \-it airflow-postgres-1 psql \-U airflow \-d catalog_db

UPDATE catalog_assets SET  
  display_name = 'Updated Display Name',  
  description = 'Updated description',  
  tags = ARRAY\['tag1', 'tag2'\]  
WHERE name = 'stg_new_table';

\\q

## **6.11.5  Column Metadata Best Practices**

For Claude to generate good queries, provide detailed column information:

* **name** — The actual database column name
* **type** — PostgreSQL data type (text, integer, timestamp, uuid, boolean, etc.)
* **description** — What the column represents
* **ai_tags** — Hints for Claude:
  - `join_key` — Primary or foreign key for joining
  - `dedup` — Used in deduplication logic
  - `NLP` — Contains natural language (customer names, descriptions)
  - `embedding` — Suitable for semantic search / embeddings
  - `time_series` — Timestamp column
  - `SLA` — Important for SLA calculations
  - `label` — Target variable for ML models

Example:

"columns": \[  
  {  
    "name": "incident_id",  
    "type": "uuid",  
    "description": "Unique incident identifier",  
    "ai_tags": \["join_key", "dedup"\]  
  },  
  {  
    "name": "description",  
    "type": "text",  
    "description": "Incident description from ServiceNow",  
    "ai_tags": \["NLP", "embedding"\]  
  },  
  {  
    "name": "created_at",  
    "type": "timestamp",  
    "description": "When the incident was created",  
    "ai_tags": \["time_series"\]  
  },  
  {  
    "name": "priority",  
    "type": "integer",  
    "description": "Priority level 1-5, 1 is highest",  
    "ai_tags": \["label"\]  
  }  
\]

---

# **Section 7 — Quick Reference Card**

## **7.1  Essential Commands**

\# ── START ────────────────────────────────────────────────────────────  
cd C:\\Users\\spits\\data-platform\\airflow  
docker compose up \-d  
   
\# ── STOP ─────────────────────────────────────────────────────────────  
docker compose down  
   
\# ── STATUS ───────────────────────────────────────────────────────────  
docker compose ps  
   
\# ── VIEW LOGS ────────────────────────────────────────────────────────  
docker compose logs airflow-scheduler  
docker compose logs airflow-webserver  
docker compose logs catalog-api   \# NEW  
   
\# ── RESTART A SERVICE ────────────────────────────────────────────────  
docker compose restart airflow-scheduler  
docker compose restart catalog-api   \# NEW  
   
\# ── CONNECT TO POSTGRESQL ────────────────────────────────────────────  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d airflow  
docker exec \-it airflow-postgres-1 psql \-U airflow \-d catalog_db   \# NEW  
   
\# ── RUN INGESTION MANUALLY ───────────────────────────────────────────  
cd C:\\Users\\spits\\data-platform\\ingestion  
python \-m sources.supabase  
   
\# ── RUN DBT MANUALLY ─────────────────────────────────────────────────  
cd C:\\Users\\spits\\data-platform\\dbt\\analytics\_project  
dbt run  
dbt test  
dbt run \--select stg\_servicenow\_incidents   \# run single model  
   
\# ── TRIGGER AIRFLOW DAG ──────────────────────────────────────────────  
docker exec airflow-airflow-scheduler-1 airflow dags trigger data\_platform\_pipeline  
   
\# ── RECREATE PROFILES.YML (after container recreate) ─────────────────  
docker exec airflow-airflow-scheduler-1 mkdir \-p /home/airflow/.dbt

## **7.2  Access Points**

| Interface | URL / Address | Credentials |
| :---- | :---- | :---- |
| Airflow UI | http://localhost:8080 | admin / admin |
| **AI Data Catalog** (NEW) | **http://localhost:8002** | None (open access) |
| PostgreSQL | localhost:5432 | airflow / airflow |
| DBeaver / pgAdmin | localhost:5432 | airflow / airflow |
| Supabase Dashboard | https://supabase.com | Your Supabase account |
| **Catalog API** (NEW) | http://localhost:8001 | None (no auth) |

## **7.3  Key File Locations**

| File | Location | What to Edit |
| :---- | :---- | :---- |
| Airflow DAG | airflow\\dags\\data\_pipeline.py | Add tasks, change schedule |
| Source credentials | ingestion\\.env | Passwords, hostnames |
| DB connections | ingestion\\utils\\db.py | Connection helper functions |
| Supabase script | ingestion\\sources\\supabase.py | Tables to sync, since window |
| Staging model | dbt\\analytics\_project\\models\\staging\\stg\_\*.sql | SQL transformations |
| Quality tests | dbt\\analytics\_project\\models\\staging\\schema.yml | Add/remove tests |
| dbt connection | dbt\\.dbt\\profiles.yml | Database connection |
| Docker services | airflow\\docker-compose.yml | Ports, volumes, images |
| **Catalog API backend** (NEW) | catalog-api\\app\\main.py | CORS, lifespan, routes |
| **Catalog Frontend** (NEW) | catalog-ui\\index.html | UI design, API endpoints |

## **7.4  Pipeline Schedule**

| Time (Local) | What Happens |
| :---- | :---- |
| 12:00 AM | Airflow triggers pipeline — ingest \+ dbt run \+ dbt test |
| 6:00 AM | Airflow triggers pipeline — ingest \+ dbt run \+ dbt test |
| 12:00 PM | Airflow triggers pipeline — ingest \+ dbt run \+ dbt test |
| 6:00 PM | Airflow triggers pipeline — ingest \+ dbt run \+ dbt test |

*⚠️  Times shown are UTC. Adjust for your local timezone — UTC-5 (EST) means runs at 7pm, 1am, 7am, 1pm local time.*

## **7.5  Catalog Service Ports & Endpoints**

| Service | Port | Endpoint | Purpose |
| :---- | :---- | :---- | :---- |
| Frontend | 8002 | http://localhost:8002 | UI for browsing assets and chatting with Claude |
| Backend API | 8001 | http://localhost:8001 | REST API for assets and AI chat |
| Health Check | 8001 | http://localhost:8001/health | Verify backend is healthy |
| List Assets | 8001 | GET http://localhost:8001/assets | Get all catalog assets |
| Asset Detail | 8001 | GET http://localhost:8001/assets/{id} | Get asset columns and metadata |
| Chat | 8001 | POST http://localhost:8001/ai-lab/chat | Send query, get Claude response |

## **7.6  Power BI Connection Details**

Based on your .env file, here are the Power BI connection details for your staging tables:

PostgreSQL Connection:

* Server: localhost  
* Port: 5432  
* Database: airflow  
* Username: airflow  
* Password: airflow  
* Schema: analytics (where your staging tables live)

In Power BI:

1. Go to Get Data → PostgreSQL database  
2. Enter:  
   * Server: localhost  
   * Database: airflow  
3. Click OK  
4. When prompted, select Database authentication and enter:  
   * Username: airflow  
   * Password: airflow  
5. Select the tables from the analytics schema (e.g., stg\_servicenow\_incidents, stg\_servicenow\_configuration\_items, incidents\_with\_configuration\_items)

## **7.7  Order of Operations**

Incident created (rtools form) 

\> Record created in transactional database (supabase)

	\> DAG Ingestion (Airflow)

		\> DAG dbt run (Airflow)

			\> DAG dbt test (Airflow)

				\> Dashboard refresh (Power BI)

				\> **AI Data Catalog UI updated** (NEW)

				\> n8n chat bot

---

**END OF DOCUMENT**

*Last Updated: March 12, 2026*  
*Version: 1.1 — Added AI Data Catalog sections*
