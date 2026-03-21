# ingestion/sources/supabase.py
import logging
from datetime import datetime, timedelta, timezone
from psycopg2.extras import execute_values
from utils.db import get_supabase, get_local_pg, ensure_schema
log = logging.getLogger(__name__)

# Add every table you want to sync here.
# Set 'updated_col' to None for tables without a timestamp column (full sync each run).
SYNC_TABLES = [
    {'table': 'incidents', 'updated_col': 'updated_at'},
    {'table': 'change_requests', 'updated_col': 'updated_at'},
    {'table': 'application_roles', 'updated_col': None},
    {'table': 'users', 'updated_col': 'updated_at'},
]

def sync_table(table: str, updated_col, since: datetime):
    src  = get_supabase()
    dest = get_local_pg()
    ensure_schema(dest, 'raw')

    with src.cursor() as cur:
        if updated_col:
            cur.execute(f'SELECT * FROM {table} WHERE {updated_col} >= %s', (since,))
        else:
            cur.execute(f'SELECT * FROM {table}')
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    # Assume 'id' is the primary key - adjust if different
    primary_key = 'id'
    table_name = f'raw.supabase_{table}'

    # Always create the table so downstream dbt models don't fail on empty syncs
    if primary_key in cols:
        col_defs_with_pk = ', '.join([
            f'{c} TEXT PRIMARY KEY' if c == primary_key else f'{c} TEXT'
            for c in cols
        ])
        dest.cursor().execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({col_defs_with_pk})')
        dest.commit()
    else:
        col_defs = ', '.join([f'{c} TEXT' for c in cols])
        dest.cursor().execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({col_defs})')
        dest.commit()

    if not rows:
        log.info(f'No new rows in {table}')
        src.close(); dest.close()
        return 0

    vals = [tuple(str(r[c]) if r[c] is not None else None for c in cols) for r in rows]

    # Use UPSERT (INSERT ... ON CONFLICT DO UPDATE) to handle duplicates
    if primary_key in cols:
        # Build the conflict update clause (all columns except PK)
        update_cols = [c for c in cols if c != primary_key]
        update_clause = ', '.join([f'{c} = EXCLUDED.{c}' for c in update_cols])
        insert_sql = f'''
            INSERT INTO {table_name} ({chr(44).join(cols)})
            VALUES %s
            ON CONFLICT ({primary_key}) DO UPDATE SET {update_clause}
        '''
    else:
        # Fallback to simple insert if no primary key
        insert_sql = f'INSERT INTO {table_name} ({chr(44).join(cols)}) VALUES %s'

    with dest.cursor() as cur:
        execute_values(cur, insert_sql, vals)
    dest.commit()
    log.info(f'Synced {len(rows)} rows into {table_name} (inserted or updated)')
    src.close(); dest.close()
    return len(rows)

def run_all(since: datetime):
    for cfg in SYNC_TABLES:
        sync_table(cfg['table'], cfg['updated_col'], since)

if __name__ == '__main__':
   # Use this version as the default for monitoring / adding new items
   run_all(since=datetime.now(timezone.utc) - timedelta(hours=6))

   # Use below version to load historical data. Like a one-time backfill
   # run_all(since=datetime(2000, 1, 1, tzinfo=timezone.utc))
