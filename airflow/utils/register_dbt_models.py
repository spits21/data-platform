"""Auto-register dbt models as catalog assets.

Reads manifest.json and compares with existing catalog_assets,
then inserts new models automatically.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2 import sql

logger = logging.getLogger(__name__)


def get_dbt_models(dbt_project_path: str = "/opt/airflow/dbt/analytics_project") -> dict:
    """
    Parse dbt manifest.json and extract all models.
    
    Returns dict mapping model_name -> {
        'unique_id': str,
        'name': str,
        'schema': str,
        'description': str,
        'columns': dict,
        'tags': list,
        'fqn': list,
    }
    """
    manifest_path = Path(dbt_project_path) / "target" / "manifest.json"
    
    if not manifest_path.exists():
        logger.warning(f"Manifest not found at {manifest_path}")
        return {}
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    models = {}
    
    # Extract only model nodes (not tests, sources, etc)
    for node_id, node_data in manifest.get('nodes', {}).items():
        if node_id.startswith('model.analytics_project.'):
            model_name = node_data.get('name')
            models[model_name] = {
                'unique_id': node_id,
                'name': model_name,
                'schema': node_data.get('schema', 'analytics'),
                'description': node_data.get('description', ''),
                'columns': node_data.get('columns', {}),
                'tags': node_data.get('tags', []),
                'fqn': node_data.get('fqn', []),
            }
            logger.info(f"Found model: {model_name} in schema {node_data.get('schema', 'analytics')}")
    
    return models


def get_registered_assets(conn_string: str) -> set:
    """Get set of already-registered model names from catalog_assets."""
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM catalog_assets WHERE dbt_model_name IS NOT NULL")
        registered = {row[0] for row in cursor.fetchall()}
        cursor.close()
        conn.close()
        return registered
    except Exception as e:
        logger.error(f"Error fetching registered assets: {e}")
        return set()


def register_new_models(conn_string: str, dbt_project_path: str = "/opt/airflow/dbt/analytics_project") -> int:
    """
    Discover new dbt models and auto-register them as catalog assets.
    
    Returns: number of newly registered models
    """
    dbt_models = get_dbt_models(dbt_project_path)
    registered = get_registered_assets(conn_string)
    
    # Find new models
    new_models = {name: data for name, data in dbt_models.items() if name not in registered}
    
    if not new_models:
        logger.info("No new dbt models to register")
        return 0
    
    logger.info(f"Found {len(new_models)} new models to register: {list(new_models.keys())}")
    
    try:
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        for model_name, model_data in new_models.items():
            # Determine source system based on tags
            source_system = 'DBT' if 'dbt' in model_data['tags'] else 'DBT'
            
            # Build columns JSON
            columns = [
                {
                    'name': col_name,
                    'type': col_data.get('data_type', 'unknown'),
                    'description': col_data.get('description', ''),
                }
                for col_name, col_data in model_data['columns'].items()
            ]
            
            insert_query = sql.SQL("""
                INSERT INTO catalog_assets 
                (name, display_name, description, schema_name, table_name, database, 
                 source_system, columns, tags, owner, pipeline_status, dbt_model_name, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """)
            
            cursor.execute(insert_query, (
                model_name,                                    # name
                model_name.replace('_', ' ').title(),         # display_name
                model_data.get('description', ''),            # description
                model_data.get('schema', 'analytics'),        # schema_name
                model_name,                                    # table_name
                'airflow',                                     # database
                'DBT',                                         # source_system
                json.dumps(columns),                           # columns (JSON)
                model_data.get('tags', []),                   # tags
                'Operations Analytics',                        # owner
                'UNKNOWN',                                     # pipeline_status
                model_name,                                    # dbt_model_name
                datetime.utcnow(),                             # created_at
                datetime.utcnow(),                             # updated_at
            ))
            
            logger.info(f"Registered model: {model_name}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully registered {len(new_models)} new models")
        return len(new_models)
    
    except Exception as e:
        logger.error(f"Error registering models: {e}")
        raise


def auto_register_dbt_models() -> None:
    """
    Airflow task: Auto-register new dbt models.
    
    Reads from airflow database credentials (set via environment or .env).
    """
    import os
    
    # Build connection string for catalog_db
    host = os.getenv('CATALOG_DB_HOST', 'postgres')
    port = os.getenv('CATALOG_DB_PORT', '5432')
    dbname = os.getenv('CATALOG_DB_NAME', 'catalog_db')
    user = os.getenv('CATALOG_DB_USER', 'airflow')
    password = os.getenv('CATALOG_DB_PASS', 'airflow')
    
    conn_string = f"host={host} port={port} dbname={dbname} user={user} password={password}"
    
    count = register_new_models(conn_string)
    logger.info(f"Auto-registration complete: {count} models registered")
