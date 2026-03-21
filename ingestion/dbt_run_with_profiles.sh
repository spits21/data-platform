#!/bin/bash
# Quick fix for dbt profiles in Airflow DAG
# Replace the bash_command in your dbt_run BashOperator with this one-liner

mkdir -p ~/.dbt && cat > ~/.dbt/profiles.yml << 'EOF'
analytics_project:
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
EOF
cd /opt/airflow/dbt/analytics_project && dbt run --target dev
