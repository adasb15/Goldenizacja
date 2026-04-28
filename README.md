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
- DBeaver jako rekomendowane narzędzie do podglądu MS SQL.

## Aktualny stack (docker compose)

Usługi aktywne w `docker-compose.yml`:
- `api` (FastAPI)
- `frontend` (React/Vite)
- `airflow` (Apache Airflow)
- `mssql` (SQL Server 2022)
- `neo4j` (Neo4j 5.24)

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

## Utworzenie tabel w MS SQL

Struktura tabel z pliku `Proponowana_struktura_tabel.pdf` jest przygotowana w skrypcie:

```text
scripts/init_proposed_mssql_schema.sql
```

Skrypt tworzy bazę `goldenizacja`, schematy `meta`, `raw`, `stg`, tabele stagingowe i metadane importu:
- `meta.SourceSystem`
- `meta.ImportBatch`
- `meta.ColumnMapping`
- `meta.ProcessLog`
- `raw.RawFile`
- `stg.Person_Staging`
- `stg.Party_Staging`

Uruchom najpierw kontener MS SQL:

```bash
docker compose up -d mssql
```

Poczekaj, aż kontener będzie zdrowy:

```bash
docker compose ps mssql
```

Skopiuj skrypt do kontenera:

```bash
docker compose cp scripts/init_proposed_mssql_schema.sql mssql:/tmp/init_proposed_mssql_schema.sql
```

Wykonaj skrypt w SQL Serverze:

```bash
docker compose exec mssql sh -lc '/opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$MSSQL_SA_PASSWORD" -i /tmp/init_proposed_mssql_schema.sql -C'
```

Skrypt jest idempotentny, więc można go uruchomić ponownie bez usuwania istniejących tabel. Kolumna `raw.RawFile.File_Content` jest typu `VARBINARY(MAX)`, co zastępuje FILESTREAM w lokalnym kontenerze SQL Server.

## Podgląd bazy w DBeaver

1. Uruchom kontener MS SQL:

```bash
docker compose up -d mssql
```

2. Otwórz DBeaver i wybierz:

```text
Database -> New Database Connection -> SQL Server
```

3. Ustaw parametry połączenia:

```text
Host: localhost
Port: 1433
Authentication: SQL Server Authentication
Username: sa
Password: wartość MSSQL_PASSWORD z pliku .env
```

4. W zakładce sterownika albo ustawień SSL zaznacz zaufanie do certyfikatu serwera, jeśli DBeaver zgłosi problem z certyfikatem:

```text
Trust server certificate: true
```

W niektórych wersjach DBeaver trzeba dodać właściwość sterownika: (nie musiałem tego robić)

```text
trustServerCertificate=true
encrypt=true
```

5. Kliknij `Test Connection`, a potem `Finish`.

6. Po połączeniu rozwiń:

```text
goldenizacja -> Schemas -> meta/raw/stg -> Tables
```

Tam widać utworzone tabele, kolumny, klucze i indeksy. Jeśli lista tabel się nie odświeża, kliknij prawym przyciskiem na połączeniu albo schemacie i wybierz `Refresh`.

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
