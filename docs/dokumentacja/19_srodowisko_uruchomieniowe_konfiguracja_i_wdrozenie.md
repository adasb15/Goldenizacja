# 19. Środowisko uruchomieniowe, konfiguracja i wdrożenie

Projekt został przygotowany przede wszystkim do uruchamiania lokalnego w środowisku kontenerowym. Repozytorium zawiera również zestaw manifestów OpenShift, jednak mają one charakter przygotowanej podstawy wdrożeniowej, a nie potwierdzonego odwzorowania środowiska lokalnego.

W praktyce należy rozróżnić dwa poziomy:

1. środowisko lokalne Docker Compose, które stanowi główną i rzeczywiście używaną ścieżkę uruchomienia,
2. środowisko OpenShift, dla którego przygotowano manifesty wymagające dostosowania i weryfikacji.

## 19.1. Środowisko lokalne Docker Compose

Główny plik uruchomieniowy to:

- `docker-compose.yml`.

Definiuje on sześć usług:

| Usługa | Rola | Port lokalny |
|---|---|---|
| `api` | FastAPI i logika pipeline'u | `8000` |
| `frontend` | React/Vite | `5173` |
| `airflow` | orkiestracja DAG | `8080` |
| `mssql` | centralne repozytorium danych | `1433` |
| `oracle` | demonstracyjne źródło relacyjne | `1521` |
| `neo4j` | demonstracyjna baza grafowa | `7474`, `7687` |

Środowisko to jest developerskie. API i frontend działają w trybie umożliwiającym szybkie przeładowanie zmian, a Airflow uruchamiany jest w uproszczonej konfiguracji z jednym kontenerem i `SequentialExecutor`.

## 19.2. Kontenery i obrazy

### Backend API

Backend budowany jest z:

- `Dockerfile`.

Obraz bazuje na:

- `python:3.14-slim-bookworm`.

Podczas budowy:

- instalowany jest ODBC Driver 18 dla SQL Servera,
- instalowane są zależności z `requirements.txt`,
- kopiowany jest katalog `app/`.

W Compose backend uruchamiany jest poleceniem:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /workspace/app
```

Oznacza to, że lokalny kontener API pracuje w trybie developerskim z hot reloadem dla kodu backendu.

### Frontend

W środowisku lokalnym frontend korzysta z gotowego obrazu:

- `node:20-alpine`.

Zamiast własnego obrazu developerskiego używany jest montowany katalog `./frontend` oraz polecenie:

```text
npm install && npm run dev -- --host 0.0.0.0 --port 5173
```

Dzięki temu zmiany w kodzie React są od razu widoczne bez ręcznej odbudowy obrazu.

Równolegle repozytorium zawiera:

- `frontend/Dockerfile`

do budowy wersji statycznej. Ten obraz:

1. wykonuje `npm ci`,
2. buduje aplikację przez `vite build`,
3. przekazuje wynik do `nginxinc/nginx-unprivileged:stable-alpine`.

Jest to wariant przygotowany pod wdrożenie, a nie tryb używany lokalnie podczas rozwoju.

### Airflow

Airflow budowany jest z:

- `airflow/Dockerfile`.

Obraz bazuje na:

- `apache/airflow:3.2.2-python3.14`.

Rozszerzenie obejmuje instalację:

- `apache-airflow-providers-fab==3.6.5`.

Uruchomienie odbywa się przez:

- `airflow/start-airflow.sh`.

Skrypt wykonuje:

1. `airflow db migrate`,
2. `airflow fab-db migrate`,
3. utworzenie albo reset hasła administratora,
4. start procesów `api-server`, `scheduler`, `dag-processor` i `triggerer`.

W środowisku lokalnym wszystkie te procesy działają w jednym kontenerze.

### Bazy danych

Lokalne środowisko korzysta z gotowych obrazów:

- `mcr.microsoft.com/mssql/server:2022-latest`,
- `gvenzl/oracle-free:23-slim-faststart`,
- `neo4j:5.24`.

SQL Server jest głównym repozytorium procesu.  
Oracle służy jako źródło demonstracyjne dla importu relacyjnego.  
Neo4j pozostaje komponentem demonstracyjnym i nie uczestniczy w głównym pipeline.

## 19.3. Wolumeny i trwałość danych

Docker Compose definiuje wolumeny:

- `mssql_data`,
- `oracle_data`,
- `neo4j_data`,
- `neo4j_logs`,
- `filestream_data`,
- `frontend_node_modules`,
- `airflow_db`.

Ich rola jest następująca:

- trwałość danych SQL Servera i Oracle,
- trwałość danych i logów Neo4j,
- przechowywanie plików pomocniczych pod `FILESTREAM_PATH`,
- zachowanie zależności frontendu,
- zachowanie metadanych i stanu Airflow.

Dodatkowo montowane są katalogi robocze z repozytorium:

- `./app` do kontenera API,
- `./frontend` do kontenera frontendu,
- `./airflow/dags`, `./airflow/logs`, `./airflow/plugins`, `./airflow/config` do kontenera Airflow,
- `./data` do Airflow tylko do odczytu.

## 19.4. Zależności startowe i healthchecki

Usługa `api` oczekuje na zdrowy stan:

- `mssql`,
- `oracle`,
- `neo4j`.

Sprawdzanie gotowości realizowane jest przez healthchecki:

- SQL Server: zapytanie `SELECT 1` przez `sqlcmd`,
- Oracle: skrypt `healthcheck.sh`,
- Neo4j: żądanie HTTP do portu `7474`.

Airflow zależy od API, ponieważ wykonuje wywołania HTTP do warstw backendu.  
Frontend zależy od API, ponieważ pobiera dane z endpointów `serving`.

## 19.5. Konfiguracja backendu

Konfiguracja backendu jest zdefiniowana w:

- `app/core/config.py`.

Wartości są ładowane z:

- pliku `.env`,
- zmiennych środowiskowych kontenera.

Najważniejsze grupy parametrów obejmują:

- nazwę i port aplikacji,
- parametry połączenia z SQL Serverem,
- parametry połączenia z Neo4j,
- ścieżkę `FILESTREAM_PATH`,
- listę `CORS_ORIGINS`,
- parametry Oracle.

Przykładowe kluczowe zmienne:

- `MSSQL_PASSWORD`,
- `NEO4J_PASSWORD`,
- `CORS_ORIGINS`,
- `ORACLE_HOST`,
- `ORACLE_PORT`,
- `ORACLE_SERVICE_NAME`.

Hasła baz danych są wymagane z `.env` albo środowiska uruchomieniowego. Nie powinny być zapisywane w dokumentacji ani publikowane w repozytorium jako wartości produkcyjne.

## 19.6. Konfiguracja frontendu

Frontend korzysta z jednej najważniejszej zmiennej środowiskowej:

- `VITE_API_URL`.

W Docker Compose ustawiana jest ona na:

```text
http://localhost:8000
```

Oznacza to, że aplikacja React kieruje odczyt danych do lokalnego backendu FastAPI. Jeżeli adres API się zmienia, frontend wymaga odpowiedniej aktualizacji tej wartości przy budowie albo uruchomieniu.

## 19.7. Konfiguracja Airflow

W Compose Airflow otrzymuje między innymi:

- `AIRFLOW_HOME=/opt/airflow`,
- `AIRFLOW__CORE__LOAD_EXAMPLES=False`,
- `AIRFLOW__CORE__EXECUTOR=SequentialExecutor`,
- `AIRFLOW__CORE__AUTH_MANAGER=airflow.providers.fab.auth_manager.fab_auth_manager.FabAuthManager`,
- `AIRFLOW__API__SECRET_KEY`,
- `AIRFLOW__API_AUTH__JWT_SECRET`,
- `AIRFLOW_USERNAME`,
- `AIRFLOW_PASSWORD`.

Konfiguracja ta oznacza, że:

- Airflow działa lokalnie bez rozproszonego executora,
- interfejs webowy jest chroniony prostym logowaniem FAB,
- konto administratora jest zakładane albo aktualizowane podczas startu.

Domyślne wartości developerskie dla logowania to `admin/admin`, jeśli nie zostaną zastąpione przez zmienne środowiskowe.

## 19.8. Lokalne uruchomienie

Podstawowe uruchomienie developerskie odbywa się przez:

```bash
docker compose up -d
```

Zatrzymanie środowiska:

```bash
docker compose down
```

Pełny reset wolumenów:

```bash
docker compose down -v
```

Najważniejsze lokalne adresy dostępu:

- Swagger API: `http://localhost:8000/docs`,
- frontend React: `http://localhost:5173`,
- Airflow UI: `http://localhost:8080`,
- Neo4j Browser: `http://localhost:7474`.

## 19.9. Inicjalizacja baz danych

SQL Server korzysta z przygotowanego skryptu:

- `scripts/init_proposed_mssql_schema.sql`.

Skrypt:

- tworzy bazę `goldenizacja`,
- zakłada schematy `meta`, `raw`, `stg`, `gold`,
- tworzy tabele procesu, stagingu i GOLD,
- jest przygotowany jako idempotentny.

Oracle korzysta ze skryptu:

- `scripts/init_oracle_insurance_core.sql`

zamontowanego do kontenera podczas startu. Służy on do zainicjalizowania demonstracyjnego źródła relacyjnego.

Backend przy starcie wykonuje dodatkowo własną inicjalizację bazy przez `init_db()`, aby kontener API był gotowy bez osobnego ręcznego przygotowania struktur ORM.

## 19.10. OpenShift

Repozytorium zawiera katalog:

- `openshift/`

z manifestami dla:

- ConfigMap,
- Secret,
- PVC,
- SQL Server,
- Neo4j,
- API,
- frontendu,
- Airflow,
- Route,
- ConfigMap z przykładowym DAG.

Najważniejsze pliki to:

- `01-configmap.yaml`,
- `02-secrets.yaml`,
- `03-pvc.yaml`,
- `04-mssql.yaml`,
- `05-neo4j.yaml`,
- `06-api.yaml`,
- `08-routes.yaml`,
- `09-frontend.yaml`,
- `10-airflow.yaml`,
- `11-airflow-dags-configmap.yaml`.

Manifesty zakładają użycie obrazów w wewnętrznym rejestrze OpenShift i wymagają podmiany placeholderów takich jak:

- `REPLACE_WITH_PROJECT`,
- `REPLACE_API_ROUTE`,
- `REPLACE_FRONTEND_ROUTE`.

## 19.11. Różnice między Docker Compose i OpenShift

Najważniejsze rozbieżności są następujące:

- OpenShift nie obejmuje Oracle, mimo że środowisko lokalne go używa,
- konfiguracja Airflow w OpenShift montuje jedynie przykładowy DAG `goldenizacja_example`,
- manifesty nie odzwierciedlają pełnej struktury lokalnych wolumenów developerskich,
- frontend w OpenShift jest wdrażany jako zbudowany obraz statyczny, a lokalnie działa w trybie Vite dev,
- OpenShift wymaga wcześniejszego zbudowania i opublikowania obrazów API, frontendu i Airflow.

Z tego powodu środowiska OpenShift nie można traktować jako gotowego, przetestowanego odpowiednika Compose.

## 19.12. Bezpieczeństwo konfiguracji

W repozytorium rozdzielono konfigurację jawną od sekretów:

- ConfigMap przechowuje ustawienia niesekretne,
- Secret przechowuje hasła i klucze.

Dotyczy to zwłaszcza:

- hasła SQL Server,
- hasła Neo4j,
- loginu i hasła Airflow,
- sekretów API i JWT Airflow.

Samo rozdzielenie konfiguracji nie oznacza jednak pełnego zabezpieczenia systemu. API aplikacji nadal nie implementuje własnego mechanizmu uwierzytelniania i autoryzacji.

## 19.13. Ograniczenia środowiskowe

Najważniejsze ograniczenia obecnego sposobu uruchomienia to:

- Docker Compose jest środowiskiem developerskim, a nie produkcyjnym,
- Airflow lokalnie działa w jednym kontenerze i z `SequentialExecutor`,
- Neo4j jest obecny w środowisku, ale nie jest częścią głównego pipeline'u,
- OpenShift nie został przetestowany na docelowym klastrze,
- manifesty OpenShift nie obejmują Oracle,
- ConfigMap Airflow w OpenShift zawiera przykładowy DAG zamiast właściwego pipeline'u.

Ograniczenia te nie uniemożliwiają działania lokalnego rdzenia systemu, ale mają znaczenie przy ocenie gotowości rozwiązania do wdrożenia poza środowiskiem demonstracyjnym.

## 19.14. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `docker-compose.yml` - lokalne środowisko usług,
- `README.md` - podstawowe instrukcje uruchomienia,
- `Dockerfile` - obraz backendu API,
- `frontend/Dockerfile` - obraz wdrożeniowy frontendu,
- `airflow/Dockerfile` - obraz Airflow,
- `airflow/start-airflow.sh` - inicjalizacja i uruchomienie Airflow,
- `app/core/config.py` - konfiguracja aplikacji ze zmiennych środowiskowych,
- `openshift/README.md` - opis wdrożenia na OpenShift,
- `openshift/01-configmap.yaml` i `openshift/02-secrets.yaml` - konfiguracja i sekrety,
- `openshift/06-api.yaml`, `openshift/09-frontend.yaml`, `openshift/10-airflow.yaml` - główne deploymenty usług,
- `openshift/11-airflow-dags-configmap.yaml` - przykładowy DAG Airflow,
- `scripts/init_proposed_mssql_schema.sql` - inicjalizacja schematu SQL Server,
- `scripts/init_oracle_insurance_core.sql` - inicjalizacja demonstracyjnego źródła Oracle.
