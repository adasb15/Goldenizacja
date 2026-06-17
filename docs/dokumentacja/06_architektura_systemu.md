# 6. Architektura systemu

Platforma została zbudowana jako aplikacja warstwowa, w której kolejne etapy przetwarzania są udostępniane przez wspólny interfejs FastAPI i uruchamiane w określonej kolejności przez Apache Airflow. Podstawowym repozytorium jest Microsoft SQL Server. Przechowuje on metadane procesu, dane RAW, rekordy pośrednie oraz wynikowe encje Golden Record. Oracle pełni rolę demonstracyjnego źródła relacyjnego.

Architekturę należy rozpatrywać na trzech poziomach:

- logicznym, opisującym podział procesu na warstwy,
- aplikacyjnym, opisującym organizację kodu backendu,
- uruchomieniowym, opisującym współpracę kontenerów i baz danych.

## 6.1. Architektura logiczna

Główny przepływ danych składa się z pięciu funkcjonalnych obszarów. W kodzie część z nich została rozdzielona na bardziej szczegółowe moduły.

### Pobieranie i rejestracja danych

Warstwa `ingestion` odpowiada za przyjęcie pliku albo wykonanie zapytania do źródła relacyjnego. Tworzy wpis systemu źródłowego i partii importu, zapisuje oryginalną zawartość w warstwie RAW oraz rozpoczyna rejestrowanie przebiegu procesu.

### Przygotowanie i kontrola danych

Obszar stagingu i walidacji został podzielony na trzy moduły:

- `staging_validation` parsuje dane i mapuje je do wspólnego modelu,
- `preprocessing` normalizuje wartości wykorzystywane w walidacji i matchingu,
- `validation` wykonuje reguły jakości oraz sprawdza adresy z użyciem TERYT.

Rozdzielenie preprocessingu od walidacji pozwala wykonać reguły jakości na danych doprowadzonych do porównywalnej postaci, zachowując jednocześnie dane stagingowe i źródłowe.

### Integracja i goldenizacja

Warstwa `integration_golden` odpowiada za:

- wyznaczanie kandydatów do połączenia,
- scoring Levenshteina,
- ponowną ocenę Jaro-Winklera,
- klasyfikację decyzji,
- grupowanie rekordów,
- wybór wartości wynikowych,
- tworzenie i aktualizowanie wymiarów GOLD,
- zapis lineage i zmian danych.

Jest to najbardziej rozbudowana warstwa aplikacji i główny obszar realizujący logikę biznesową projektu.

### Analityka

Warstwa `analytics` została przewidziana jako miejsce dla metryk, raportów, projekcji grafowych i struktur analitycznych. W obecnym kodzie zawiera jedynie szkielet modułu i endpoint statusowy. Część modelu wymiarowego powstaje już podczas goldenizacji, ale nie wykonano osobnej logiki analitycznej.

### Udostępnianie

Warstwa `serving` udostępnia odczytowe widoki danych wynikowych. Obejmuje listy i szczegóły Golden Record, wyszukiwanie osób i podmiotów, lineage, historię zmian, wyniki walidacji, kandydatów matchingu, porównanie rekordów oraz liczniki kolejnych etapów. Endpointy stosują paginację i opcjonalne filtry. Warstwa nie realizuje mechanizmu PUSH ani webhooków.

## 6.2. Architektura aplikacji FastAPI

Punktem wejścia backendu jest `app/main.py`. Podczas uruchamiania aplikacji wykonywana jest funkcja `init_db()`, która:

1. oczekuje na dostępność SQL Servera,
2. tworzy bazę `goldenizacja`, jeżeli jeszcze nie istnieje,
3. tworzy tabele zarejestrowane w metadanych SQLAlchemy.

Aplikacja konfiguruje middleware CORS i dołącza dwa główne routery:

- `app.api.routes` zawiera techniczne endpointy demonstracyjne,
- `app.layers.router` łączy endpointy właściwego pipeline'u danych.

Router warstw używa wspólnego prefiksu `/layers` i dołącza moduły w kolejności odpowiadającej przepływowi danych:

1. ingestion,
2. staging validation,
3. preprocessing,
4. validation,
5. integration golden,
6. analytics,
7. serving.

Każda główna warstwa stosuje zbliżony podział plików:

| Plik | Odpowiedzialność |
|---|---|
| `api.py` | endpointy HTTP, walidacja parametrów i mapowanie błędów na odpowiedzi HTTP |
| `service.py` | logika biznesowa warstwy |
| `repository.py` | operacje bazodanowe i oddzielenie logiki od SQLAlchemy |
| `models.py` | modele ORM i odwzorowanie tabel |
| `schemas.py` | modele żądań i odpowiedzi API |

Warstwa stagingu posiada dodatkowo `mapper.py`, ponieważ mapowanie danych źródłowych do modelu kanonicznego stanowi oddzielny i rozbudowany obszar odpowiedzialności.

Taki podział umożliwia testowanie logiki biznesowej bez uruchamiania pełnego środowiska bazodanowego. Testy integracji i goldenizacji wykorzystują repozytoria zastępcze, które implementują kontrakt potrzebny serwisom.

## 6.3. Główne komponenty

### FastAPI

Backend udostępnia operacje pipeline'u, zarządza logiką biznesową i połączeniem z Microsoft SQL Serverem. Do komunikacji z bazą wykorzystywane są SQLAlchemy i sterownik ODBC Driver 18 for SQL Server.

FastAPI generuje również opis OpenAPI oraz interfejs Swagger dostępny w środowisku lokalnym pod `/docs`.

### Apache Airflow

Airflow jest orkiestratorem procesu. Nie przetwarza danych bezpośrednio w swojej bazie, lecz wywołuje endpointy FastAPI przez HTTP. Identyfikatory plików RAW oraz wyniki kroków są przekazywane pomiędzy zadaniami za pomocą XCom.

DAG jest uruchamiany ręcznie i nie posiada harmonogramu cyklicznego. Pozwala to wybrać plik, źródło, typ encji oraz parametry matchingu dla konkretnego przebiegu.

### Microsoft SQL Server

SQL Server jest centralnym magazynem danych platformy. Schematy bazy rozdzielają odpowiedzialności:

- `meta` przechowuje źródła, partie, mapowania i logi,
- `raw` przechowuje oryginalne dane wejściowe,
- `stg` przechowuje dane stagingowe, preprocessingowe, walidacyjne i kandydatów matchingu,
- `gold` przechowuje wynikowe osoby, podmioty, adresy, identyfikatory, relacje, lineage i rejestr zmian.

Modele ORM są używane przez aplikację, natomiast `scripts/init_proposed_mssql_schema.sql` zawiera pełniejszą definicję struktury, ograniczeń, indeksów, słowników źródeł i mapowań kolumn.

### Oracle

Oracle działa jako demonstracyjny system dziedzinowy. FastAPI łączy się z nim bezpośrednio podczas wywołania importu relacyjnego. Wynik zapytań jest serializowany do JSON i zapisywany w SQL Serverze jako snapshot RAW. Od tego momentu dane relacyjne przechodzą przez te same etapy co dane plikowe.

### React

Frontend React jest osobną aplikacją komunikującą się z FastAPI przez HTTP. W środowisku lokalnym działa przez serwer developerski Vite. W przygotowanym obrazie wdrożeniowym aplikacja jest budowana statycznie i serwowana przez Nginx.

Aktualny frontend wykorzystuje endpointy odczytowe warstwy `serving`. Udostępnia dwa główne widoki:

- tabelę wyników walidacji z filtrowaniem i paginacją,
- tabelę kandydatów matchingu dla Levenshteina i Jaro-Winklera wraz z porównaniem szczegółów pary rekordów.

Interfejs obsługuje już listę Golden Record, szczegóły osoby i podmiotu, zakładki lineage i historii zmian, a także widoki walidacji i matchingu. Nadal nie obsługuje ręcznej obsługi przypadków `REVIEW` ani operacji zapisu do pipeline'u. Nie jest więc pełnym interfejsem biznesowym systemu, ale przestał być już wyłącznie testem technicznego połączenia z API.

### Neo4j

Neo4j znajduje się w konfiguracji Docker Compose i posiada połączenie z demonstracyjnym modułem dokumentów w `app/api/routes.py`. Główny pipeline goldenizacji nie zapisuje jednak danych do Neo4j i nie odczytuje z niego relacji.

Komponent nie został przetestowany jako część procesu integracji osób i podmiotów. Z tego powodu na diagramie architektury jest oznaczony jako element demonstracyjny, a nie część działającej ścieżki przetwarzania.

## 6.4. Komunikacja pomiędzy komponentami

Podstawowa ścieżka wykonania wygląda następująco:

1. Użytkownik uruchamia DAG w Airflow i przekazuje parametry wejściowe.
2. Airflow odczytuje plik z zamontowanego katalogu `data` albo zleca API pobranie danych z Oracle.
3. Airflow wywołuje kolejne endpointy FastAPI przez HTTP.
4. FastAPI wykonuje logikę właściwej warstwy.
5. Repozytoria zapisują lub odczytują dane z Microsoft SQL Servera.
6. Wyniki operacji wracają do Airflow i są przekazywane do kolejnych zadań.

Frontend komunikuje się bezpośrednio z FastAPI, ale nie uczestniczy w wykonywaniu DAG. Neo4j jest osiągany wyłącznie przez demonstracyjne endpointy dokumentów.

## 6.5. Konfiguracja

Konfiguracja backendu jest zdefiniowana w klasie `Settings` w `app/core/config.py`. Wartości są pobierane ze zmiennych środowiskowych oraz pliku `.env`. Obejmują między innymi:

- adres i dane dostępowe SQL Servera,
- adres i dane dostępowe Neo4j,
- parametry Oracle,
- ścieżkę wolumenu pomocniczego,
- listę dozwolonych źródeł CORS,
- nazwę i port aplikacji.

Połączenie z SQL Serverem jest budowane przez `sqlalchemy.engine.URL`, co zapewnia poprawne kodowanie parametrów i hasła. Sesja SQLAlchemy jest tworzona osobno dla każdego żądania API.

Sekrety nie powinny być zapisywane w dokumentacji ani publikowane w repozytorium. W środowisku OpenShift przewidziano oddzielne zasoby ConfigMap i Secret.

## 6.6. Środowisko lokalne

`docker-compose.yml` definiuje sześć usług:

| Usługa | Rola | Port lokalny |
|---|---|---|
| `api` | FastAPI i logika pipeline'u | 8000 |
| `frontend` | React/Vite | 5173 |
| `airflow` | orkiestracja DAG | 8080 |
| `mssql` | centralne repozytorium danych | 1433 |
| `oracle` | demonstracyjne źródło relacyjne | 1521 |
| `neo4j` | demonstracyjna baza grafowa | 7474 i 7687 |

API oczekuje na poprawne uruchomienie SQL Servera, Oracle i Neo4j. Zależność od Neo4j wynika z konfiguracji środowiska i modułu demonstracyjnego, a nie z wymagań głównego pipeline'u.

Wolumeny zapewniają trwałość baz danych, logów Neo4j, środowiska Airflow i pomocniczych plików aplikacji. Katalog `data` jest montowany do kontenera Airflow tylko do odczytu.

Środowisko Docker Compose jest środowiskiem developerskim. API i frontend pracują w trybie umożliwiającym szybkie przeładowanie zmian, a Airflow używa własnego obrazu z `apache/airflow:3.2.2-python3.14`, menedżera uwierzytelniania FAB oraz uruchamia w jednym kontenerze procesy `api-server`, `scheduler`, `dag-processor` i `triggerer`. Lokalny executor pozostaje `SequentialExecutor`.

## 6.7. Przygotowane zasoby OpenShift

Katalog `openshift` zawiera manifesty:

- ConfigMap i Secret,
- PersistentVolumeClaim,
- Deployment i Service dla SQL Servera,
- Deployment i Service dla Neo4j,
- Deployment i Service dla API,
- Deployment i Service dla frontendu,
- Deployment i Service dla Airflow,
- Route dla usług udostępnianych przez HTTP,
- ConfigMap zawierającą przykładowy DAG.

Manifesty nie zostały przetestowane na docelowym klastrze. Nie obejmują także usługi Oracle używanej w aktualnym środowisku Docker Compose. Konfiguracja Airflow w OpenShift zawiera jedynie przykładowy DAG `goldenizacja_example`, a nie właściwy pipeline `goldenizacja_pipeline`. Zawierają również wartości wymagające zastąpienia dla konkretnego projektu i tras klastra. Stanowią więc podstawę wdrożenia, ale nie są potwierdzonym odwzorowaniem działającego środowiska lokalnego.

OpenShift nie jest uwzględniany jako część potwierdzonej ścieżki wykonania systemu. Szczegółowy opis manifestów i rozbieżności zostanie przedstawiony w rozdziale dotyczącym wdrożenia.

## 6.8. Ograniczenia architektury

Najważniejsze ograniczenia obecnej architektury obejmują:

- brak uwierzytelniania i autoryzacji API,
- synchroniczne wykonywanie operacji warstw przez endpointy HTTP,
- `SequentialExecutor` w lokalnym Airflow,
- brak mechanizmu PUSH i webhooków dla zmian Golden Record,
- brak biznesowego interfejsu użytkownika,
- niewykorzystanie Neo4j w głównym pipeline'ie,
- nieprzetestowane manifesty OpenShift,
- brak Oracle w przygotowanych manifestach OpenShift,
- brak mechanizmu kolejkowego dla długotrwałych operacji,
- zależność stagingu od mapowań inicjalizowanych skryptem SQL.

Ograniczenia nie zmieniają podziału odpowiedzialności w działającym rdzeniu systemu, ale mają znaczenie przy ocenie gotowości rozwiązania do pracy poza środowiskiem demonstracyjnym.

## 6.9. Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| Inicjalizacja aplikacji | `app/main.py` |
| Konfiguracja | `app/core/config.py` |
| Router główny warstw | `app/layers/router.py` |
| Połączenie SQL Server | `app/db/sql.py` |
| Inicjalizacja bazy | `app/db/init_db.py` |
| Połączenie Neo4j | `app/db/neo4j.py` |
| Endpointy demonstracyjne | `app/api/routes.py` |
| Konsumenckie API danych | `app/layers/serving/` |
| Warstwy biznesowe | `app/layers/` |
| DAG | `airflow/dags/goldenizacja_pipeline.py` |
| Środowisko lokalne | `docker-compose.yml` |
| Obraz API | `Dockerfile` |
| Obraz frontendu | `frontend/Dockerfile` |
| Manifesty OpenShift | `openshift/` |

