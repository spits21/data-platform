# ⚡ QUICK DEVELOPER REFERENCE

## 🔗 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:8002 | Data catalog UI |
| API | http://localhost:8001 | Backend API |
| Airflow | http://localhost:8080 | DAG orchestration |
| PostgreSQL | localhost:5432 | Data warehouse |

---

## 📁 Key Files

| File | Purpose | Active |
|------|---------|--------|
| `catalog-ui/index.html` | Frontend SPA | ✅ |
| `catalog-api/` | FastAPI backend | ✅ |
| `airflow/dags/data_pipeline.py` | DAG definition | ✅ |
| `dbt/analytics_project/models/` | dbt models | ✅ |
| `ingestion/sources/supabase.py` | Data sync | ✅ |
| `ingestion/utils/dbt_utils.py` | Setup helpers | ✅ |

---

## 🔍 Common Queries

### Check incident count
```sql
SELECT COUNT(*) FROM analytics.stg_servicenow_incidents;
```

### See all incidents
```sql
SELECT 
  incident_id, 
  incident_number, 
  priority, 
  state 
FROM analytics.stg_servicenow_incidents 
ORDER BY created_at DESC;
```

### Check catalog assets
```sql
SELECT id, display_name, schema_name, table_name 
FROM catalog_db.catalog_assets;
```

### Check DAG execution
```
Visit: http://localhost:8080 → data_platform_pipeline
```

---

## 🚀 Common Tasks

### Add a new incident to test
1. Query Supabase incidents table
2. Add new record
3. Trigger DAG: `http://localhost:8080`
4. Wait 5 minutes for sync + dbt
5. Frontend will show new incident

### Test Claude AI response
1. Go to http://localhost:8002
2. Browse → View Details → Chat with Claude
3. Ask: "How many incidents have priority 1?"
4. Should show real count from database

### Check if DAG ran successfully
```bash
# Via Airflow UI
http://localhost:8080 → data_platform_pipeline → graph

# Via database
SELECT state, COUNT(*) 
FROM public.dag_run 
WHERE dag_id = 'data_platform_pipeline' 
GROUP BY state;
```

### Reset everything (dangerous!)
```bash
docker-compose down -v  # Removes all containers AND volumes
docker-compose up -d    # Restart
```

---

## 🐛 Debugging

### Frontend not loading data?
```javascript
// Check browser console (F12)
// Look for fetch errors to /assets or /ai-lab/chat
// Verify http://localhost:8001 is reachable
```

### Claude returning old data?
```sql
-- Check which schema/table is in catalog
SELECT schema_name, table_name FROM catalog_db.catalog_assets;

-- Verify new data in analytics schema
SELECT COUNT(*) FROM analytics.stg_servicenow_incidents;
```

### DAG failing?
```
1. Go to http://localhost:8080
2. Click on failed task
3. Read log for error details
4. Common issues:
   - Missing dbt profiles (fixed by setup_dbt_profiles task)
   - Database connection (check postgres running)
   - Duplicate key (UPSERT should handle now)
```

### API returning 500 error?
```bash
# Check API logs
docker logs <catalog-api-container>

# Verify database connection
curl http://localhost:8001/health
```

---

## 📊 Data Lineage

```
Supabase
  ↓ (ingestion/sources/supabase.py)
raw.supabase_incidents (7 rows)
raw.supabase_configuration_items_snapshots (5 rows)
  ↓ (dbt/analytics_project/models/)
analytics.stg_servicenow_incidents (7 rows)
analytics.stg_servicenow_configuration_items (5 rows)
analytics.incidents_with_configuration_items (7 rows)
  ↓ (catalog-api)
catalog_db.catalog_assets (3 assets)
  ↓ (catalog-ui)
Frontend display + Claude context
```

---

## 🔐 Credentials

| Service | User | Password | Location |
|---------|------|----------|----------|
| PostgreSQL | airflow | airflow | ingestion/.env |
| Supabase | (configured) | (configured) | ingestion/.env |
| Anthropic API | (key) | (ANTHROPIC_API_KEY) | ingestion/.env |

---

## 📝 Environment Variables

Located in: `ingestion/.env`

Key variables:
```
LOCAL_PG_HOST=postgres           # For Airflow container
LOCAL_PG_USER=airflow
LOCAL_PG_PASS=airflow
LOCAL_PG_DB=airflow

SUPABASE_HOST=...
SUPABASE_USER=...

ANTHROPIC_API_KEY=sk-ant-...     # Claude API
CATALOG_DB_NAME=catalog_db
```

---

## ✅ Health Check Checklist

Run this to verify system is healthy:

```bash
# 1. Containers running?
docker ps | grep -E "airflow|postgres|postgres.*catalog"

# 2. API healthy?
curl http://localhost:8001/health

# 3. Frontend loads?
curl http://localhost:8002 | head -20

# 4. Airflow accessible?
curl -s http://localhost:8080/health

# 5. Database accessible?
psql -h localhost -U airflow -d airflow -c "SELECT COUNT(*) FROM analytics.stg_servicenow_incidents;"
```

---

## 📚 Documentation

- **Architecture:** `ARCHITECTURE_FINAL.md` (this system overview)
- **Setup:** See docker-compose files and .env
- **Cleanup:** `CLEANUP_COMMANDS.md` (remove old files)
- **Fixes Applied:** `ARCHITECTURE_CLEANUP.md` (what was cleaned up)

---

## 💡 Pro Tips

1. **Quick test:** Frontend at http://localhost:8002 - everything works locally
2. **Monitor DAGs:** Airflow UI shows logs for all runs
3. **Query real data:** Use `analytics` schema (dbt-created), not `raw`
4. **Add incidents:** Just add to Supabase; DAG will sync automatically
5. **Scale features:** Add dbt models → register in catalog → Claude sees it

---

## 🆘 Support

### If something breaks:
1. Check logs: Airflow UI or `docker logs container-name`
2. Verify DB: `psql -h localhost -U airflow -d airflow`
3. Restart: `docker-compose restart`
4. Full reset: `docker-compose down -v && docker-compose up -d`

### Common fixes:
- Database connection timeout → restart postgres
- dbt profiles missing → DAG will auto-create (setup_dbt_profiles task)
- Old data showing → run DAG manually to refresh
- Claude wrong schema → check `catalog_assets` table (should be `analytics`)
