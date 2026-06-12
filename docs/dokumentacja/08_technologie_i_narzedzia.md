# Technologie i narzędzia

Dobór technologii podporządkowano warstwowemu przetwarzaniu danych, możliwości uruchomienia kompletnego środowiska lokalnego oraz oddzieleniu logiki biznesowej od sposobu składowania i udostępniania danych. Główny pipeline został wykonany w Pythonie, dane są przechowywane w Microsoft SQL Serverze, a kolejne etapy koordynuje Apache Airflow. Środowisko lokalne uruchamiane jest za pomocą Docker Compose.

Wersje bibliotek backendu są przypięte w `requirements.txt`. W przypadku frontendu `package.json` określa dopuszczalne zakresy wersji, natomiast `package-lock.json` zapisuje wersje faktycznie rozwiązane podczas instalacji.

## Zestawienie technologii

| Technologia | Wersja w projekcie | Zastosowanie | Status wykorzystania |
|---|---:|---|---|
| Python | 3.12 | język backendu i zadań Airflow | główny element systemu |
| FastAPI | 0.115.0 | REST API i organizacja endpointów warstw | używane w głównym pipeline |
| Uvicorn | 0.30.6 | serwer ASGI aplikacji FastAPI | używane lokalnie i w obrazie API |
| Pydantic | 2.9.2 | modele danych wejściowych i odpowiedzi API | używane w głównym pipeline |
| pydantic-settings | 2.5.2 | konfiguracja ze zmiennych środowiskowych | używane w backendzie |
| SQLAlchemy | 2.0.35 | ORM, sesje i operacje bazodanowe | używane w głównym pipeline |
| PyODBC | 5.1.0 | komunikacja SQLAlchemy z SQL Serverem | używane w głównym pipeline |
| ODBC Driver 18 for SQL Server | instalowany w obrazie API | sterownik połączenia z Microsoft SQL Serverem | używane w obrazie backendu |
| Microsoft SQL Server | obraz 2022 latest | centralne repozytorium `meta`, `raw`, `stg` i `gold` | używane w głównym pipeline |
| Oracle Database Free | obraz 23 slim faststart | demonstracyjne źródło relacyjne | używane jako źródło testowe |
| python-oracledb | 2.5.1 | połączenie z Oracle bez klienta natywnego | używane przez import relacyjny |
| Apache Airflow | 2.10.2, Python 3.12 | orkiestracja kolejnych etapów procesu | używane w głównym pipeline |
| RapidFuzz | 3.9.7 | Levenshtein i Jaro-Winkler | używane w matchingu |
| python-stdnum | 1.20 | walidacja identyfikatorów | używane w walidacji |
| email-validator | 2.2.0 | kontrola składni adresów e-mail | używane w walidacji |
| dnspython | 2.8.0 | opcjonalna kontrola domen pocztowych | używane w walidacji |
| phonenumbers | 8.13.47 | normalizacja numerów telefonów | używane w preprocessingu |
| text-unidecode | 1.3 | uproszczenie tekstu na potrzeby porównań | używane w preprocessingu |
| openpyxl | 3.1.5 | odczyt plików XLSX | używane przez ingestion i staging |
| python-multipart | 0.0.12 | obsługa formularzy i uploadu plików w FastAPI | używane przez API |
| React | 18.3.1 | frontend techniczny | używane w ograniczonym zakresie |
| Vite | 5.4.21 | środowisko developerskie i budowanie frontendu | używane przez frontend |
| Node.js | obraz 20 Alpine | uruchamianie i budowanie frontendu | używane lokalnie i w buildzie |
| Nginx unprivileged | stable Alpine | serwowanie zbudowanego frontendu | przygotowane w obrazie wdrożeniowym |
| Neo4j | 5.24 | demonstracyjna baza grafowa | poza głównym pipeline, nieprzetestowane |
| Docker Compose | plik Compose w repozytorium | lokalne uruchomienie usług | podstawowe środowisko developerskie |
| OpenShift | manifesty YAML | przygotowanie zasobów wdrożeniowych | nieprzetestowane na docelowym klastrze |

## Backend

### Python

Backend i DAG Airflow zostały napisane w Pythonie 3.12. Język został wykorzystany do:

- implementacji endpointów REST,
- parsowania i mapowania danych,
- normalizacji i walidacji,
- matchingu oraz grupowania rekordów,
- budowy Golden Record,
- komunikacji z bazami danych,
- orkiestracji procesu.

Obraz API bazuje na `python:3.12-slim`. Obraz Airflow używa wariantu `apache/airflow:2.10.2-python3.12`, dzięki czemu główne elementy środowiska korzystają z tej samej wersji języka.

### FastAPI i Uvicorn

FastAPI udostępnia operacje poszczególnych warstw przez REST. Routery są organizowane zgodnie ze strukturą procesu i łączone pod prefiksem `/layers`. Framework wykonuje walidację parametrów, generuje OpenAPI oraz udostępnia interfejs Swagger.

Uvicorn pełni funkcję serwera ASGI. W Docker Compose uruchamiany jest z opcją automatycznego przeładowania kodu, co odpowiada środowisku developerskiemu. Obraz API posiada również standardową komendę uruchamiającą serwer bez opcji developerskich.

Najważniejsze pliki:

- `app/main.py`,
- `app/layers/router.py`,
- `app/layers/*/api.py`,
- `Dockerfile`.

### Pydantic i konfiguracja

Modele Pydantic definiują struktury odpowiedzi API dla każdej warstwy. `pydantic-settings` służy do pobierania konfiguracji ze zmiennych środowiskowych i pliku `.env`.

Klasa `Settings` w `app/core/config.py` przechowuje między innymi parametry FastAPI, SQL Servera, Oracle, Neo4j i CORS. Umożliwia to zmianę konfiguracji bez modyfikowania logiki aplikacji.

## Dostęp do danych

### SQLAlchemy

SQLAlchemy 2.0 jest warstwą dostępu do Microsoft SQL Servera. Modele ORM odwzorowują tabele wykorzystywane przez aplikację, a repozytoria oddzielają operacje bazodanowe od logiki biznesowej.

Sesja jest tworzona osobno dla każdego żądania API. Opcja `pool_pre_ping` sprawdza połączenie przed jego wykorzystaniem, co ogranicza problemy po restarcie kontenera bazy.

Modele SQLAlchemy nie są jedynym źródłem definicji bazy. Skrypt `scripts/init_proposed_mssql_schema.sql` zawiera dodatkowo:

- ograniczenia kontrolne,
- indeksy,
- słowniki,
- poziomy zaufania źródeł,
- mapowania kolumn.

Z tego względu pełne przygotowanie bazy wymaga wykonania skryptu SQL, a nie wyłącznie automatycznego `Base.metadata.create_all()`.

### Microsoft SQL Server

Microsoft SQL Server 2022 jest centralnym repozytorium platformy. Przechowuje zarówno dane operacyjne procesu, jak i dane wynikowe. W projekcie zastosowano cztery schematy:

- `meta`,
- `raw`,
- `stg`,
- `gold`.

Połączenie jest realizowane przez dialekt `mssql+pyodbc` i ODBC Driver 18 for SQL Server. Parametry szyfrowania oraz zaufania do certyfikatu są konfigurowalne.

W środowisku projektu dane RAW są przechowywane w `VARBINARY(MAX)`. Typ jest mapowany w SQLAlchemy jako `LargeBinary`.

### Oracle

Oracle Database Free 23 jest demonstracyjnym źródłem relacyjnym. Kontener podczas pierwszego uruchomienia wykonuje `scripts/init_oracle_insurance_core.sql`, który tworzy syntetyczną strukturę systemu ubezpieczeniowego i dane testowe.

Backend obsługuje dwa sposoby konfiguracji połączenia:

- jawny connection string ODBC,
- bezpośrednie połączenie przez bibliotekę `oracledb`.

Wynik zapytania jest serializowany do JSON i zapisywany w warstwie RAW SQL Servera. Oracle nie pełni roli repozytorium wynikowego.

## Orkiestracja

Apache Airflow zarządza kolejnością wykonania pipeline'u. DAG używa operatorów Python, ale poszczególne zadania wywołują FastAPI przez HTTP. Taki podział pozostawia logikę biznesową w aplikacji backendowej i ogranicza kod DAG do orkiestracji.

W środowisku lokalnym zastosowano `SequentialExecutor`. Jest on wystarczający dla demonstracyjnego procesu wykonywanego sekwencyjnie, ale nie służy do równoległego przetwarzania wielu dużych zadań.

DAG nie posiada automatycznego harmonogramu. Uruchomienie następuje ręcznie z parametrami określającymi źródło, plik, typ encji i progi matchingu.

Implementacja znajduje się w `airflow/dags/goldenizacja_pipeline.py`.

## Biblioteki przetwarzania danych

### RapidFuzz

RapidFuzz dostarcza implementacje algorytmów Levenshteina i Jaro-Winklera. Biblioteka jest używana przez `app/layers/integration_golden/service.py` do:

- obliczania podobieństwa wartości tekstowych,
- tworzenia wyniku ważonego,
- ponownej oceny kandydatów po pierwszym etapie,
- klasyfikowania decyzji matchingu.

Wybór biblioteki pozwala korzystać z gotowych, zoptymalizowanych implementacji zamiast utrzymywać własny kod algorytmów odległości tekstowej.

### Biblioteki walidacyjne

`python-stdnum` wspiera sprawdzanie identyfikatorów, natomiast część reguł kontrolnych została zaimplementowana również bezpośrednio w warstwie validation. Dotyczy to między innymi sum kontrolnych i zależności wynikających z numeru PESEL.

`email-validator` sprawdza składnię adresów e-mail. Jeżeli parametr procesu włącza kontrolę DNS, `dnspython` jest używany do wyszukania rekordów domeny.

### Biblioteki normalizacyjne

`phonenumbers` standaryzuje numery telefonów do wspólnego formatu. `text-unidecode` upraszcza znaki tekstowe wykorzystywane podczas porównań. Funkcje aplikacji uzupełniają działanie bibliotek o reguły właściwe dla polskich danych, nazw podmiotów, form prawnych i adresów.

### openpyxl

`openpyxl` umożliwia odczyt plików XLSX. Arkusze są otwierane w trybie tylko do odczytu, co ogranicza niepotrzebne zużycie pamięci podczas parsowania większych plików.

## Frontend

Frontend został wykonany w React 18 i budowany przez Vite. W środowisku lokalnym działa na obrazie `node:20-alpine`, a kod jest montowany do kontenera w celu obsługi szybkich zmian.

Przygotowany `frontend/Dockerfile` stosuje build wieloetapowy:

1. Node.js instaluje zależności i buduje pliki statyczne,
2. Nginx w wariancie unprivileged serwuje wynik kompilacji.

Adres API jest przekazywany przez zmienną `VITE_API_URL`. Obecna aplikacja frontendowa wywołuje wyłącznie endpoint `/health`, dlatego React i Vite są elementami działającego środowiska, ale ich użycie biznesowe pozostaje ograniczone.

Najważniejsze pliki:

- `frontend/package.json`,
- `frontend/package-lock.json`,
- `frontend/src/App.jsx`,
- `frontend/vite.config.js`,
- `frontend/Dockerfile`.

## Neo4j

Biblioteka kliencka `neo4j` w wersji 5.24.0 oraz obraz bazy Neo4j 5.24 są dostępne w projekcie. `app/db/neo4j.py` tworzy sterownik, a demonstracyjne endpointy dokumentów wykonują prostą operację `MERGE`.

Neo4j nie został włączony do warstwy `integration_golden`, nie przechowuje relacji Golden Record i nie został przetestowany w głównym przepływie. Nie należy więc traktować go jako technologii realizującej widok 360 stopni w wykonanej wersji.

## Konteneryzacja i wdrożenie

### Docker Compose

Docker Compose definiuje lokalne środowisko składające się z API, frontendu, Airflow, SQL Servera, Oracle i Neo4j. Konfiguracja obejmuje:

- porty usług,
- zależności startowe,
- healthchecki baz danych,
- wolumeny trwałe,
- montowanie kodu i danych,
- przekazywanie zmiennych środowiskowych.

Jest to podstawowy i faktycznie wykorzystywany sposób uruchamiania kompletnego środowiska projektu.

### OpenShift

W katalogu `openshift` znajdują się manifesty ConfigMap, Secret, PVC, Deployment, Service i Route. Nie zostały one przetestowane na docelowym klastrze i nie obejmują usługi Oracle obecnej w aktualnym Docker Compose.

OpenShift należy traktować jako przygotowany wariant wdrożeniowy wymagający dostosowania i weryfikacji, a nie jako potwierdzone środowisko działania systemu.

## Narzędzia developerskie

Repozytorium zawiera skrypty i konfiguracje wspierające pracę nad systemem:

- `scripts/init_proposed_mssql_schema.sql` inicjalizuje pełny model SQL Servera,
- `scripts/init_oracle_insurance_core.sql` przygotowuje demonstracyjne źródło Oracle,
- `scripts/refine_synthetic_data.js` generuje i poprawia dane syntetyczne,
- katalog `tests` zawiera testy logiki biznesowej i API,
- Swagger umożliwia ręczne wywoływanie endpointów,
- Airflow UI służy do uruchamiania i obserwowania DAG.

Do przeglądania SQL Servera w środowisku lokalnym rekomendowany jest DBeaver. Narzędzie nie stanowi części aplikacji i nie jest wymagane do jej działania.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| Zależności Python | `requirements.txt` |
| Zależności frontendowe | `frontend/package.json`, `frontend/package-lock.json` |
| Obraz backendu | `Dockerfile` |
| Obraz frontendu | `frontend/Dockerfile` |
| Środowisko lokalne | `docker-compose.yml` |
| Konfiguracja backendu | `app/core/config.py` |
| Połączenie SQL Server | `app/db/sql.py` |
| Połączenie Neo4j | `app/db/neo4j.py` |
| Orkiestracja | `airflow/dags/goldenizacja_pipeline.py` |
| Matching | `app/layers/integration_golden/service.py` |
| Walidacja | `app/layers/validation/service.py` |
| Preprocessing | `app/layers/preprocessing/service.py` |
| Manifesty OpenShift | `openshift/` |
