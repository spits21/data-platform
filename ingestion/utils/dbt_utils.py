"""
Helper function to initialize dbt profiles for Airflow DAG tasks

Add this to your data_pipeline.py DAG file, or import it from a utilities module.
"""
import os
from pathlib import Path


def setup_dbt_profiles():
    """
    Initialize dbt profiles.yml in the Airflow home directory.
    This function should be called as a PythonOperator task before dbt_run.
    """
    airflow_home = os.path.expanduser("~")
    dbt_dir = Path(airflow_home) / ".dbt"
    profiles_file = dbt_dir / "profiles.yml"
    
    # Create directory if it doesn't exist
    dbt_dir.mkdir(parents=True, exist_ok=True)
    
    # Create profiles.yml content
    profiles_content = """analytics_project:
  target: dev
  outputs:
    dev:
      type: postgres
      host: postgres
      user: airflow
      pass: airflow
      port: 5432
      dbname: airflow
      schema: analytics
      threads: 4
      keepalives_idle: 0
    prod:
      type: postgres
      host: "{{ env_var('DBT_POSTGRES_HOST', 'postgres') }}"
      user: "{{ env_var('DBT_POSTGRES_USER', 'airflow') }}"
      pass: "{{ env_var('DBT_POSTGRES_PASS', 'airflow') }}"
      port: "{{ env_var('DBT_POSTGRES_PORT', '5432') }}"
      dbname: "{{ env_var('DBT_POSTGRES_DB', 'airflow') }}"
      schema: analytics
      threads: 4
      keepalives_idle: 0
"""
    
    # Write profiles.yml
    with open(profiles_file, 'w') as f:
        f.write(profiles_content)
    
    # Set proper permissions
    os.chmod(profiles_file, 0o600)
    
    profiles_path_str = str(profiles_file)
    print(f"✓ dbt profiles.yml created at {profiles_path_str}")
    return profiles_path_str


if __name__ == "__main__":
    # For standalone testing
    setup_dbt_profiles()
