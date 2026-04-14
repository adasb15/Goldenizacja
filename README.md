# Platforma Goldenizacji Danych (FastAPI + React + Airflow)

Projekt studencki do integracji i goldenizacji danych podmiotów/osób.
Aktualny setup developerski działa lokalnie przez `docker compose` i obejmuje backend API, frontend React, MS SQL, Neo4j i Airflow.

## Co działa teraz

- Backend FastAPI z endpointami:
  - `GET /health`
  - `POST /files/line-count` (tylko CSV)
  - `POST /documents`
  - `GET /documents`
  - `GET /documents/search?q=...`
- Frontend React (Vite) do szybkiego testu połączenia z API.
- Airflow do uruchamiania DAG-ów ETL (przykładowy DAG w `airflow/dags`).
- MS SQL jako baza relacyjna.
- Neo4j jako baza grafowa.

## Aktualny stack (docker compose)

Usługi aktywne w `docker-compose.yml`:
- `api` (FastAPI)
- `frontend` (React/Vite)
- `airflow` (Apache Airflow)
- `mssql` (SQL Server 2022)
- `neo4j` (Neo4j 5.24)

Uwaga: `adminer` jest obecnie zakomentowany w `docker-compose.yml`.

## Porty lokalne

- API + Swagger: `http://localhost:8000/docs`
- Frontend React: `http://localhost:5173`
- Airflow UI: `http://localhost:8080`
- Neo4j Browser: `http://localhost:7474`
- Neo4j Bolt: `localhost:7687`
- MS SQL: `localhost:1433`

## Konfiguracja

Plik środowiskowy: `.env`

Kluczowe zmienne:
- `MSSQL_PASSWORD`
- `NEO4J_PASSWORD`
- `CORS_ORIGINS` (domyślnie `http://localhost:5173`)
- `AIRFLOW_UID`
- `AIRFLOW_USERNAME`
- `AIRFLOW_PASSWORD`

Hasła do baz są wymagane z `.env` (nie ma fallbacku w kodzie).

## Uruchomienie (dev)

```bash
docker compose up -d
```

Zatrzymanie:

```bash
docker compose down
```

Pełny reset wolumenów (uwaga: usuwa dane):

```bash
docker compose down -v
```

## Airflow logowanie

Airflow startuje z komendą, która:
1. robi migrację DB,
2. tworzy użytkownika admin z `.env`,
3. jeśli user już istnieje, resetuje mu hasło,
4. uruchamia `airflow standalone`.

Czyli logujesz się danymi:
- `AIRFLOW_USERNAME`
- `AIRFLOW_PASSWORD`

(domyślnie: `admin/admin`).

## Frontend

Frontend działa w trybie dev (`vite`) z hot reloadem.
Połączenie do API idzie przez `VITE_API_URL=http://localhost:8000` ustawione w `docker-compose.yml`.

## Struktura projektu

- `app/` - backend FastAPI
- `frontend/` - frontend React (Vite)
- `airflow/` - DAG-i i pliki Airflow
- `tests/` - testy backendu
- `openshift/` - manifesty pod OpenShift

## OpenShift

Manifesty są w katalogu `openshift/`.
Po dodaniu React + Airflow manifesty zostały rozszerzone o:
- `09-frontend.yaml`
- `10-airflow.yaml`
- `11-airflow-dags-configmap.yaml`

Szczegóły wdrożenia: `openshift/README.md`.
