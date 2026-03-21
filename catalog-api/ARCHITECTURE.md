# Data Catalog Architecture

## Overview
The AI-ready Data Catalog is a multi-tier system for browsing and analyzing data assets with Claude Haiku 4.5 integration.

## Services

### Backend (8001)
- **FastAPI Application** running in Docker container `catalog-api`
- **Language**: Python 3.11
- **ORM**: SQLAlchemy 2.0 (async)
- **API Endpoints**:
  - `GET /assets` - List all catalog assets
  - `GET /assets/{id}` - Asset details with columns and metadata
  - `POST /assets` - Create new asset (admin)
  - `PUT /assets/{id}` - Update asset (admin)
  - `POST /ai-lab/chat` - Multi-turn Claude conversation with SQL execution

### Frontend (8002)
- **Static HTML** served via Python HTTP server
- **File**: `catalog-ui/index.html` (~600 lines)
- **Features**:
  - Asset search and filtering
  - Detail modals with column information
  - Claude AI chat interface with real-time responses
  - SQL history tracking
  - No build step required

### Databases

#### PostgreSQL "airflow" (Port 5432)
Contains actual data tables:
- `staging.stg_servicenow_incidents` (5 incidents)
- `staging.stg_servicenow_configuration_items` (5 config items)
- `marts.incidents_with_configuration_items` (8 joined records)

#### PostgreSQL "catalog_db" 
Contains metadata:
- `catalog_assets` - Asset registry with columns, tags, owner, lineage

## Data Flow

1. **Frontend loads** → Makes CORS fetch request to backend `/assets`
2. **User clicks asset** → Fetches `GET /assets/{id}` with full details
3. **User asks Claude** → POSTs to `/ai-lab/chat` with query + asset context
4. **Claude responds**:
   - Generates SQL query for the referenced table
   - Backend validates query (6-rule safety check)
   - Executes via asyncpg read-only connection
   - Returns results to Claude
   - Claude synthesizes response for user
5. **User sees history** → SQL executions logged in UI

## CORS Configuration
Cleaned up to only production-needed origins:
- `http://localhost:8001` (self for any internal calls)
- `http://localhost:8002` (frontend)

## Hot Reload
Both services support file-watching:
- **Backend**: Uvicorn with `--reload` flag in Docker
- **Frontend**: Just refresh browser to load updated `index.html`

## Database Connections
- **Catalog API** uses SQLAlchemy + asyncpg for async operations
- **SQL Executor** uses separate asyncpg pool with read-only enforcement
- **No passwords stored in code** - all from .env file

## Security
- SQL queries validated against 6 rules before execution
- Read-only enforcement at asyncpg transaction level
- CORS restricted to known origins
- No API keys stored in code
