FROM apache/airflow:3.2.2-python3.14

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    "apache-airflow-providers-fab==3.6.5"

COPY --chown=airflow:root --chmod=0755 airflow/start-airflow.sh /usr/local/bin/start-airflow
