"""
Example Airflow DAG with dbt_run fix - Use this as reference for updating data_pipeline.py

This shows how to add a setup task before dbt_run to initialize dbt profiles.
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Import the setup utility
import sys
sys.path.insert(0, '/opt/airflow')
from ingestion.utils.dbt_utils import setup_dbt_profiles

# Default DAG arguments
default_args = {
    'owner': 'data-team',
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 1, 1),
}

# Define the DAG
dag = DAG(
    'data_platform_pipeline',
    default_args=default_args,
    description='Data platform pipeline with dbt transformations',
    schedule_interval='@daily',
    catchup=False,
)

# ========== TASK 1: Setup dbt profiles (ADD THIS FIRST) ==========
setup_dbt = PythonOperator(
    task_id='setup_dbt_profiles',
    python_callable=setup_dbt_profiles,
    dag=dag,
    doc='Initialize dbt profiles.yml in the airflow home directory'
)

# ========== TASK 2: Run dbt (Existing task, no changes needed) ==========
dbt_run = BashOperator(
    task_id='dbt_run',
    bash_command='cd /opt/airflow/data-platform/dbt/analytics_project && dbt run --target dev',
    dag=dag,
    doc='Run dbt models to build analytics views and tables'
)

# ========== TASK 3: Run dbt tests (Optional) ==========
dbt_test = BashOperator(
    task_id='dbt_test',
    bash_command='cd /opt/airflow/data-platform/dbt/analytics_project && dbt test --target dev',
    dag=dag,
    doc='Run dbt tests to validate data quality'
)

# ========== TASK DEPENDENCIES ==========
# Make sure setup_dbt runs before dbt_run
setup_dbt >> dbt_run >> dbt_test

if __name__ == '__main__':
    dag.cli()
