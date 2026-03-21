# Data Catalog UI

Static HTML frontend for the data catalog with lineage visualization, asset browsing, and AI chat integration.

## Architecture

- **Frontend:** Static HTML + vanilla JavaScript (no build process required)
- **Server:** Python HTTP server (`serve.py`)
- **API:** Backend FastAPI catalog-api on port 8001
- **Port:** 8002

## Getting Started

### Prerequisites
- Python 3.8+
- Backend API running on http://localhost:8001

### Running the Server

```bash
cd c:\Users\spits\data-platform\catalog-ui
python serve.py
```

The catalog will be available at:
- http://localhost:8002 (local machine)
- http://192.168.1.156:8002 (network)

## Features

- **Browse Assets** - Search and explore data assets from the catalog
- **View Schemas** - Column names, types, and descriptions from database metadata
- **Lineage Visualization** - See data flow: SOURCE → ORCHESTRATION → STORAGE → TRANSFORMATION
- **AI Chat** - Ask Claude questions about assets and data
- **Connection Options** - Copy connection strings and MCP configurations for integration

## File Structure

```
catalog-ui/
├── index.html          # Main UI with embedded CSS and JavaScript
├── serve.py            # Python HTTP server
├── .env.local          # Environment variables
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Current Assets

1. **stg_servicenow_incidents** - Cleaned incidents from ServiceNow
2. **stg_servicenow_configuration_items** - CMDB configuration items from ServiceNow
3. **stg_servicenow_change_requests** - Change request data from ServiceNow
4. **incidents_with_configuration_items** - Joined mart combining incidents and CIs
5. **incidents_with_change_requests** - Joined mart combining incidents and changes

## API Integration

The frontend communicates with the backend at `http://localhost:8001`:
- `GET /assets` - Get all catalog assets with metadata and columns
- `POST /ai-lab/chat` - Send chat queries to Claude

## Customization

### Lineage Flows

To modify the lineage visualization, edit the `lineageFlows` object in `index.html` (around line 1340). Each asset key maps to a stages array showing the data flow.

### Asset Descriptions

Asset descriptions and metadata are fetched from the backend API and rendered dynamically. To update them, modify the catalog database or seed scripts in the backend.
