# ingestion/utils/db.py
import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
load_dotenv()
 
def get_local_pg():
    return psycopg2.connect(
        host=os.getenv('LOCAL_PG_HOST', 'postgres'),
        port=int(os.getenv('LOCAL_PG_PORT', 5432)),
        dbname=os.getenv('LOCAL_PG_DB', 'airflow'),
        user=os.getenv('LOCAL_PG_USER', 'airflow'),
        password=os.getenv('LOCAL_PG_PASS', 'airflow')
    )
 
def get_supabase():
    return psycopg2.connect(
        host=os.getenv('SUPABASE_HOST'),
        port=int(os.getenv('SUPABASE_PORT', 5432)),
        dbname=os.getenv('SUPABASE_DB', 'postgres'),
        user=os.getenv('SUPABASE_USER'),
        password=os.getenv('SUPABASE_PASS'),
        sslmode='require'
    )
 
def ensure_schema(conn, schema):
    with conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS {schema}')
    conn.commit()
 
def upsert(conn, table, records, conflict_col):
    if not records: return 0
    cols = list(records[0].keys())
    vals = [tuple(r[c] for c in cols) for r in records]
    updates = ', '.join([f'{c}=EXCLUDED.{c}' for c in cols if c != conflict_col])
    sql = f'''
        INSERT INTO {table} ({','.join(cols)}) VALUES %s
        ON CONFLICT ({conflict_col}) DO UPDATE SET {updates}, synced_at=NOW()
    '''
    with conn.cursor() as cur:
        execute_values(cur, sql, vals)
    conn.commit()
    return len(vals)