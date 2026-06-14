# Technologie i narzędzia

Dobór technologii podporządkowano warstwowemu przetwarzaniu danych, możliwości uruchomienia kompletnego środowiska lokalnego oraz oddzieleniu logiki biznesowej od sposobu składowania i udostępniania danych. Główny pipeline został wykonany w Pythonie, dane są przechowywane w Microsoft SQL Serverze, a kolejne etapy koordynuje Apache Airflow. Środowisko lokalne uruchamiane jest za pomocą Docker Compose.

Wersje bibliotek backendu są przypięte w `requirements.txt`. W przypadku frontendu `package.json` określa dopuszczalne zakresy wersji, natomiast `package-lock.json` zapisuje wersje faktycznie rozwiązane podczas instalacji.

## Zestawienie technologii

| Technologia | Wersja w projekcie | Zastosowanie | Status wykorzystania |
|---|---:|---|---|
| Python | 3.14 | język backendu i zadań Airflow | główny element systemu |
| FastAPI | 0.136.3 | REST API i organizacja endpointów warstw | używane w głównym pipeline |
| Uvicorn | 0.49.0 | serwer ASGI aplikacji FastAPI | używane lokalnie i w obrazie API |
| Pydantic | 2.13.4 | modele danych wejściowych i odpowiedzi API | używane w głównym pipeline |
| pydantic-settings | 2.14.1 | konfiguracja ze zmiennych środowiskowych | używane w backendzie |
| SQLAlchemy | 2.0.50 | ORM, sesje i operacje bazodanowe | używane w głównym pipeline |
| PyODBC | 5.3.0 | komunikacja SQLAlchemy z SQL Serverem | używane w głównym pipeline |
| ODBC Driver 18 for SQL Server | instalowany w obrazie API | sterownik połączenia z Microsoft SQL Serverem | używane w obrazie backendu |
| Microsoft SQL Server | obraz 2022 latest | centralne repozytorium `meta`, `raw`, `stg` i `gold` | używane w głównym pipeline |
| Oracle Database Free | obraz 23 slim faststart | demonstracyjne źródło relacyjne | używane jako źródło testowe |
| python-oracledb | 4.0.1 | połączenie z Oracle bez klienta natywnego | używane przez import relacyjny |
| Apache Airflow | 3.2.2, Python 3.14 | orkiestracja kolejnych etapów procesu | używane w głównym pipeline |
| FAB Auth Manager | 3.6.5 | logowanie i zarządzanie kontami Airflow | używane przez interfejs Airflow |
| RapidFuzz | 3.14.5 | Levenshtein i Jaro-Winkler | używane w matchingu |
| python-stdnum | 2.2 | walidacja identyfikatorów | używane w walidacji |
| email-validator | 2.3.0 | kontrola składni adresów e-mail | używane w walidacji |
| dnspython | 2.8.0 | opcjonalna kontrola domen pocztowych | używane w walidacji |
| phonenumbers | 9.0.32 | normalizacja numerów telefonów | używane w preprocessingu |
| text-unidecode | 1.3 | uproszczenie tekstu na potrzeby porównań | używane w preprocessingu |
| openpyxl | 3.1.5 | odczyt plików XLSX | używane przez ingestion i staging |
| python-multipart | 0.0.32 | obsługa formularzy i uploadu plików w FastAPI | używane przez API |
| Neo4j Python Driver | 6.2.0 | komunikacja backendu z bazą grafową | używane przez demonstracyjną obsługę dokumentów |
| React | 18.3.1 | frontend prezentujący dane z warstwy `serving` | używane w zakresie widoków walidacji i matchingu |
| Vite | 5.4.21 | środowisko developerskie i budowanie frontendu | używane przez frontend |
| Node.js | obraz 20 Alpine | uruchamianie i budowanie frontendu | używane lokalnie i w buildzie |
| Nginx unprivileged | stable Alpine | serwowanie zbudowanego frontendu | przygotowane w obrazie wdrożeniowym |
| Neo4j | 5.24 | demonstracyjna baza grafowa | poza głównym pipeline, nieprzetestowane |
| Docker Compose | plik Compose w repozytorium | lokalne uruchomienie usług | podstawowe środowisko developerskie |
| OpenShift | manifesty YAML | przygotowanie zasobów wdrożeniowych | nieprzetestowane na docelowym klastrze |

## Backend

### Python

Backend i DAG Airflow działają na Pythonie 3.14. Obraz API bazuje na `python:3.14-slim-bookworm`, zgodnym z repozytorium ODBC Driver 18 dla Debiana 12. Obraz Airflow rozszerza `apache/airflow:3.2.2-python3.14` o FAB Auth Manager.

### FastAPI i Uvicorn

FastAPI udostępnia operacje warstw przez REST, waliduje parametry oraz generuje OpenAPI i interfejs Swagger.

Uvicorn pełni funkcję serwera ASGI. W Docker Compose uruchamiany jest z opcją automatycznego przeładowania kodu, co odpowiada środowisku developerskiemu. Obraz API posiada również standardową komendę uruchamiającą serwer bez opcji developerskich.

### Pydantic i konfiguracja

Pydantic definiuje modele danych API, a `pydantic-settings` pobiera konfigurację ze zmiennych środowiskowych i pliku `.env`. Klasa `Settings` w `app/core/config.py` obejmuje parametry aplikacji, baz danych i CORS.

## Dostęp do danych

### SQLAlchemy

SQLAlchemy 2.0 odpowiada za modele ORM, sesje i operacje repozytoriów. Sesja jest tworzona dla każdego żądania, a `pool_pre_ping` sprawdza połączenie przed użyciem. Pełna definicja bazy, obejmująca również ograniczenia, indeksy, słowniki i mapowania, znajduje się w `scripts/init_proposed_mssql_schema.sql`.

### Microsoft SQL Server

Microsoft SQL Server 2022 jest centralnym repozytorium schematów `meta`, `raw`, `stg` i `gold`. Połączenie wykorzystuje `mssql+pyodbc` i ODBC Driver 18, a dane RAW są przechowywane jako `VARBINARY(MAX)` mapowany przez `LargeBinary`.

### Oracle

Oracle Database Free 23 jest demonstracyjnym źródłem relacyjnym inicjalizowanym przez `scripts/init_oracle_insurance_core.sql`. Backend łączy się przez ODBC albo bibliotekę `oracledb`, a wyniki zapytań zapisuje jako snapshoty JSON w warstwie RAW SQL Servera.

## Orkiestracja

Apache Airflow wywołuje przez HTTP kolejne operacje FastAPI. Lokalnie używa `SequentialExecutor`, a API server, scheduler, DAG processor i triggerer działają w jednym kontenerze. FAB Auth Manager zapewnia logowanie kontem administratora skonfigurowanym przez zmienne środowiskowe. Szczegóły przepływu i parametrów opisano w rozdziale 10.

## Biblioteki przetwarzania danych

### RapidFuzz

RapidFuzz dostarcza implementacje Levenshteina i Jaro-Winklera używane do oceny podobieństwa tekstowego oraz ponownej oceny kandydatów matchingu.

### Biblioteki walidacyjne

`python-stdnum` wspiera sprawdzanie identyfikatorów, natomiast część reguł kontrolnych została zaimplementowana również bezpośrednio w warstwie validation. Dotyczy to między innymi sum kontrolnych i zależności wynikających z numeru PESEL.

`email-validator` sprawdza składnię adresów e-mail. Jeżeli parametr procesu włącza kontrolę DNS, `dnspython` jest używany do wyszukania rekordów domeny.

### Biblioteki normalizacyjne

`phonenumbers` standaryzuje numery telefonów do wspólnego formatu. `text-unidecode` upraszcza znaki tekstowe wykorzystywane podczas porównań. Funkcje aplikacji uzupełniają działanie bibliotek o reguły właściwe dla polskich danych, nazw podmiotów, form prawnych i adresów.

### openpyxl

`openpyxl` umożliwia odczyt plików XLSX. Arkusze są otwierane w trybie tylko do odczytu, co ogranicza niepotrzebne zużycie pamięci podczas parsowania większych plików.

## Frontend

Frontend wykorzystuje React 18 i Vite. Lokalnie działa na obrazie `node:20-alpine`, natomiast wieloetapowy `frontend/Dockerfile` buduje pliki statyczne i przekazuje je do Nginx unprivileged. Aplikacja korzysta z endpointów warstwy `serving` i udostępnia widoki walidacji oraz matchingu, w tym filtrowanie, paginację i porównanie wybranej pary rekordów. Zakres nadal pozostaje odczytowy i nie obejmuje pełnego widoku Golden Record ani ręcznej obsługi decyzji integracyjnych.

## Neo4j

Backend używa sterownika Neo4j 6.2.0, natomiast serwer działa na obrazie Neo4j 5.24. Komponent obsługuje demonstracyjny zapis dokumentów, ale nie jest częścią przetestowanego pipeline'u i nie przechowuje relacji Golden Record.

## Konteneryzacja i wdrożenie

### Docker Compose

Docker Compose jest podstawowym sposobem uruchamiania kompletnego środowiska lokalnego. Definiuje usługi, zależności startowe, healthchecki, wolumeny i zmienne środowiskowe.

### OpenShift

Manifesty OpenShift obejmują ConfigMap, Secret, PVC, Deployment, Service i Route. Nie zostały przetestowane na docelowym klastrze i nie obejmują Oracle, dlatego są wariantem wymagającym dostosowania i weryfikacji.

## Narzędzia developerskie

Skrypty w katalogu `scripts` inicjalizują bazy i wspierają przygotowanie danych syntetycznych. Testy znajdują się w `tests`, Swagger służy do ręcznego wywoływania API, a Airflow UI do uruchamiania i obserwowania DAG. DBeaver może być używany do przeglądania SQL Servera, ale nie jest częścią aplikacji.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| Zależności Python | `requirements.txt` |
| Zależności frontendowe | `frontend/package.json`, `frontend/package-lock.json` |
| Obraz backendu | `Dockerfile` |
| Obraz frontendu | `frontend/Dockerfile` |
| Obraz i inicjalizacja Airflow | `airflow/Dockerfile`, `airflow/start-airflow.sh` |
| Środowisko lokalne | `docker-compose.yml` |
| Konfiguracja backendu | `app/core/config.py` |
| Połączenie SQL Server | `app/db/sql.py` |
| Połączenie Neo4j | `app/db/neo4j.py` |
| Orkiestracja | `airflow/dags/goldenizacja_pipeline.py` |
| Matching | `app/layers/integration_golden/service.py` |
| Walidacja | `app/layers/validation/service.py` |
| Preprocessing | `app/layers/preprocessing/service.py` |
| Manifesty OpenShift | `openshift/` |
