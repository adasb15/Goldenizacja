#!/usr/bin/env bash
set -euo pipefail

airflow db migrate
airflow fab-db migrate

if ! airflow users create \
    --username "${AIRFLOW_USERNAME:-admin}" \
    --password "${AIRFLOW_PASSWORD:-admin}" \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com; then
    airflow users reset-password \
        --username "${AIRFLOW_USERNAME:-admin}" \
        --password "${AIRFLOW_PASSWORD:-admin}"
fi

airflow api-server --host 0.0.0.0 --port 8080 &
api_server_pid=$!

airflow scheduler &
scheduler_pid=$!

airflow dag-processor &
dag_processor_pid=$!

airflow triggerer &
triggerer_pid=$!

shutdown() {
    kill -TERM \
        "$api_server_pid" \
        "$scheduler_pid" \
        "$dag_processor_pid" \
        "$triggerer_pid" \
        2>/dev/null || true
    wait || true
}

trap shutdown EXIT INT TERM
wait -n "$api_server_pid" "$scheduler_pid" "$dag_processor_pid" "$triggerer_pid"
