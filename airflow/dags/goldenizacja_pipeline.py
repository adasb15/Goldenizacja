from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from airflow import DAG
from airflow.models.param import Param
from airflow.operators.python import PythonOperator


API_BASE_URL = "http://api:8000"
LAYERS_API_PREFIX = "/layers"
DEFAULT_FILE_PATH = "/opt/airflow/data/csv/pesel.csv"
TERYT_SIMC_PATH = "/opt/airflow/data/teryt/SIMC.csv"
TERYT_ULIC_PATH = "/opt/airflow/data/teryt/ULIC.csv"
DEFAULT_SOURCE_SYSTEM_CODE_PARAM = "AUTO"
DEFAULT_ENTITY_TYPE_PARAM = "AUTO"
SOURCE_SYSTEM_BY_FILE_STEM = {
    "ceidg": "CEIDG",
    "gleif": "GLEIF",
    "knf_rejestr_dostawcow_i_wydawcow_pieniadza_elektronicznego": "KNF_PIENIADZ_ELEKTRONICZNY",
    "knf_rejestr_firm_inwestycyjnych": "KNF_FIRMY_INWESTYCYJNE",
    "knf_rejestr_posrednikow_ubezpieczeniowych_agent": "KNF_AGENT",
    "knf_rejestr_posrednikow_ubezpieczeniowych_pracownik_agenta": "KNF_PRACOWNIK_AGENTA",
    "krs": "KRS",
    "pesel": "PESEL",
    "regon": "REGON",
    "vat": "VAT",
}
DEFAULT_ENTITY_TYPE_BY_SOURCE_SYSTEM = {
    "GLEIF": "PARTY",
    "KNF_PIENIADZ_ELEKTRONICZNY": "PARTY",
    "PESEL": "PERSON",
    "REGON": "PARTY",
    "VAT": "PARTY",
}
AUTO_BOTH_ENTITY_TYPES_SOURCE_SYSTEMS = {
    "CEIDG",
    "KRS",
    "KNF_AGENT",
    "KNF_PRACOWNIK_AGENTA",
    "KNF_FIRMY_INWESTYCYJNE",
}
AUTO_BOTH_ENTITY_TYPES = ("PARTY", "PERSON")


def _conf(context: dict[str, Any]) -> dict[str, Any]:
    dag_run = context.get("dag_run")
    params = context.get("params") or {}
    dag_run_conf = dag_run.conf if dag_run and dag_run.conf else {}
    return {**params, **dag_run_conf}


def _post_form(endpoint: str, data: dict[str, Any], files: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE_URL}{endpoint}",
        data=data,
        files=files,
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(
            f"API request failed: POST {endpoint} returned HTTP {response.status_code}. "
            f"Response: {response.text}"
        )
    return response.json()


def _source_system_code(conf: dict[str, Any], file_path: Path) -> str:
    configured = conf.get("source_system_code")
    if configured and str(configured).upper() != DEFAULT_SOURCE_SYSTEM_CODE_PARAM:
        return str(configured).upper()

    source_system_code = SOURCE_SYSTEM_BY_FILE_STEM.get(file_path.stem.lower())
    if source_system_code is None:
        raise ValueError(
            f"Nie wykryto typu/systemu pliku dla '{file_path.name}'. "
            "Podaj source_system_code recznie albo uzyj znanej nazwy pliku."
        )

    return source_system_code


def _entity_types(conf: dict[str, Any]) -> tuple[str, ...]:
    configured = conf.get("entity_type")
    if configured and str(configured).upper() != DEFAULT_ENTITY_TYPE_PARAM:
        return (str(configured).upper(),)

    file_path = Path(conf.get("file_path", DEFAULT_FILE_PATH))
    source_system_code = _source_system_code(conf, file_path)
    if source_system_code in AUTO_BOTH_ENTITY_TYPES_SOURCE_SYSTEMS:
        return AUTO_BOTH_ENTITY_TYPES

    entity_type = DEFAULT_ENTITY_TYPE_BY_SOURCE_SYSTEM.get(source_system_code)
    if entity_type is None:
        raise ValueError(
            f"Nie wykryto typu encji dla systemu '{source_system_code}'. "
            "Podaj entity_type recznie: PERSON albo PARTY."
        )

    return (entity_type,)


def raw_load(**context: Any) -> int:
    conf = _conf(context)
    file_path = Path(conf.get("file_path", DEFAULT_FILE_PATH))
    source_system_code = _source_system_code(conf, file_path)
    created_by = conf.get("created_by", "airflow")

    with file_path.open("rb") as file_handle:
        result = _post_form(
            f"{LAYERS_API_PREFIX}/ingestion/raw-load",
            data={
                "source_system_code": source_system_code,
                "created_by": created_by,
            },
            files={
                "file": (file_path.name, file_handle),
            },
        )

    return int(result["raw_file_id"])


def staging_load(**context: Any) -> dict[str, Any]:
    conf = _conf(context)
    raw_file_id = context["ti"].xcom_pull(task_ids="raw_load")
    entity_types = _entity_types(conf)

    results = {}
    for entity_type in entity_types:
        results[entity_type] = _post_form(
            f"{LAYERS_API_PREFIX}/staging_validation/staging-load",
            data={
                "raw_file_id": raw_file_id,
                "entity_type": entity_type,
            },
        )

    return results


def preprocessing_load(**context: Any) -> dict[str, Any]:
    conf = _conf(context)
    raw_file_id = context["ti"].xcom_pull(task_ids="raw_load")
    entity_types = _entity_types(conf)

    results = {}
    for entity_type in entity_types:
        results[entity_type] = _post_form(
            f"{LAYERS_API_PREFIX}/preprocessing/preprocessing-load",
            data={
                "raw_file_id": raw_file_id,
                "entity_type": entity_type,
            },
        )

    return results


def teryt_load(**context: Any) -> dict[str, Any]:
    simc_path = Path(TERYT_SIMC_PATH)
    ulic_path = Path(TERYT_ULIC_PATH)

    if not simc_path.is_file() or not ulic_path.is_file():
        raise FileNotFoundError(
            f"Brak plików TERYT w Airflow: SIMC={simc_path} ULIC={ulic_path}. "
            "Upewnij się, że katalog ./data/teryt jest zamontowany do /opt/airflow/data/teryt."
        )

    with simc_path.open("rb") as simc_handle, ulic_path.open("rb") as ulic_handle:
        return _post_form(
            f"{LAYERS_API_PREFIX}/validation/teryt-load",
            data={},
            files={
                "simc": (simc_path.name, simc_handle),
                "ulic": (ulic_path.name, ulic_handle),
            },
        )


def validation_load(**context: Any) -> dict[str, Any]:
    conf = _conf(context)
    raw_file_id = context["ti"].xcom_pull(task_ids="raw_load")
    entity_types = _entity_types(conf)
    check_email_dns = str(conf.get("check_email_dns", True)).lower()

    results = {}
    for entity_type in entity_types:
        results[entity_type] = _post_form(
            f"{LAYERS_API_PREFIX}/validation/validation-load",
            data={
                "raw_file_id": raw_file_id,
                "entity_type": entity_type,
                "check_email_dns": check_email_dns,
            },
        )

    return results


with DAG(
    dag_id="goldenizacja_pipeline",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    params={
        "file_path": Param(
            DEFAULT_FILE_PATH,
            type="string",
            description="Sciezka do pliku widoczna z kontenera Airflow.",
        ),
        "source_system_code": Param(
            DEFAULT_SOURCE_SYSTEM_CODE_PARAM,
            type="string",
            description="AUTO = wykryj z nazwy pliku albo podaj PESEL, VAT, REGON, KRS itd.",
        ),
        "entity_type": Param(
            DEFAULT_ENTITY_TYPE_PARAM,
            enum=["AUTO", "PERSON", "PARTY"],
            description="AUTO = wykryj po zrodle albo wybierz PERSON/PARTY.",
        ),
        "created_by": Param(
            "airflow",
            type="string",
            description="Wartosc zapisywana w metadanych importu.",
        ),
        "check_email_dns": Param(
            True,
            type="boolean",
            description="Czy walidacja email ma sprawdzac DNS.",
        ),
    },
    tags=["goldenizacja", "pipeline"],
) as dag:
    raw_load_task = PythonOperator(
        task_id="raw_load",
        python_callable=raw_load,
    )

    staging_load_task = PythonOperator(
        task_id="staging_load",
        python_callable=staging_load,
    )

    preprocessing_load_task = PythonOperator(
        task_id="preprocessing_load",
        python_callable=preprocessing_load,
    )

    teryt_load_task = PythonOperator(
        task_id="teryt_load",
        python_callable=teryt_load,
    )

    validation_load_task = PythonOperator(
        task_id="validation_load",
        python_callable=validation_load,
    )

    raw_load_task >> staging_load_task >> preprocessing_load_task >> teryt_load_task >> validation_load_task
