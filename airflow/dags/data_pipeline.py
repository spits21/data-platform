from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta, timezone
import sys

sys.path.insert(0, '/opt/airflow/ingestion')
sys.path.insert(0, '/opt/airflow/utils')

from utils.dbt_utils import setup_dbt_profiles

default_args = {
    'owner': 'data-team',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email_on_failure': False,
}

with DAG(
    'data_platform_pipeline',
    default_args=default_args,
    description='Python ingest -> dbt transform -> reporting views',
    schedule_interval='0 */6 * * *',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['data-platform'],
) as dag:

    def run_supabase():
        from sources.supabase import run_all
        return run_all(since=datetime.now(timezone.utc) - timedelta(hours=7))

    ingest_supabase = PythonOperator(
        task_id='ingest_supabase',
        python_callable=run_supabase,
    )

    setup_dbt = PythonOperator(
        task_id='setup_dbt_profiles',
        python_callable=setup_dbt_profiles,
    )

    dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/dbt/analytics_project && dbt run --target dev',
    )

    dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt/analytics_project && dbt test --target dev',
    )

    def register_new_models_task():
        """Wrapper to import and call the registration function at runtime."""
        from register_dbt_models import auto_register_dbt_models
        auto_register_dbt_models()

    register_assets = PythonOperator(
        task_id='register_dbt_models',
        python_callable=register_new_models_task,
    )

    ingest_supabase >> setup_dbt >> dbt_run >> dbt_test >> register_assets