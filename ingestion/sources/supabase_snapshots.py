import os, logging
from datetime import datetime, timezone
from psycopg2.extras import execute_values
from utils.db import get_supabase, get_local_pg, ensure_schema

log = logging.getLogger(__name__)

# Add every table you want to snapshot here
SNAPSHOT_TABLES = [
    'configuration_items',
    # 'another_table',
]

def snapshot_table(table: str):
    """
    Create a daily snapshot of a table with a timestamp column.
    Stores all rows with a snapshot_timestamp indicating when the snapshot was taken.
    """
    src = get_supabase()
    dest = get_local_pg()
    ensure_schema(dest, 'raw')
    
    snapshot_timestamp = datetime.now(timezone.utc)
    
    # Fetch all rows from source table
    with src.cursor() as cur:
        # First, get count of records
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        count = cur.fetchone()[0]
        log.info(f'Record count in {table}: {count}')
        
        cur.execute(f'SELECT * FROM {table}')
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    
    log.info(f'Found columns in {table}: {cols}')
    log.info(f'Fetched {len(rows)} rows from {table}')
    
    if not rows:
        log.info(f'No rows found in {table}')
        src.close()
        dest.close()
        return 0
    
    # Drop existing table and recreate with current schema
    # This ensures the table structure matches the source table
    col_defs = ', '.join([f'{c} TEXT' for c in cols])
    snapshot_table_name = f'raw.supabase_{table}_snapshots'
    
    with dest.cursor() as cur:
        # Create table if it doesn't exist
        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS {snapshot_table_name} (
                {col_defs},
                snapshot_timestamp TIMESTAMP WITH TIME ZONE
            )
        ''')
        # Clear existing data for fresh snapshot
        cur.execute(f'TRUNCATE TABLE {snapshot_table_name}')
    dest.commit()
    
    # Add snapshot_timestamp to each row
    vals = [
        tuple(str(r[c]) if r[c] is not None else None for c in cols) + (snapshot_timestamp,)
        for r in rows
    ]
    
    # Insert rows with timestamp
    cols_with_timestamp = cols + ['snapshot_timestamp']
    with dest.cursor() as cur:
        execute_values(
            cur,
            f'INSERT INTO {snapshot_table_name} ({chr(44).join(cols_with_timestamp)}) VALUES %s',
            vals
        )
    dest.commit()
    
    log.info(f'Loaded {len(rows)} rows into {snapshot_table_name} with snapshot_timestamp: {snapshot_timestamp}')
    src.close()
    dest.close()
    return len(rows)

def run_snapshots():
    """
    Execute snapshots for all configured tables.
    """
    for table in SNAPSHOT_TABLES:
        snapshot_table(table)

if __name__ == '__main__':
    run_snapshots()
