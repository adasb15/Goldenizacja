# Przepływ i orkiestracja danych

Proces integracji danych jest wykonywany jako sekwencja operacji rozpoczynająca się od utworzenia partii importu i zapisu materiału RAW, a kończąca utworzeniem lub aktualizacją rekordów w schemacie GOLD. Orkiestratorem procesu jest Apache Airflow, natomiast logika poszczególnych etapów znajduje się w aplikacji FastAPI.

Airflow nie wykonuje bezpośrednio operacji na SQL Serverze. Zadania DAG-u wywołują endpointy HTTP odpowiednich warstw, a backend realizuje przetwarzanie za pomocą serwisów i repozytoriów. Dzięki temu te same operacje mogą być uruchamiane z DAG-u, interfejsu Swagger albo innego klienta API.

Główna definicja procesu znajduje się w `airflow/dags/goldenizacja_pipeline.py`. DAG ma identyfikator `goldenizacja_pipeline`, nie posiada harmonogramu cyklicznego i jest uruchamiany ręcznie z wybranymi parametrami.

## Ogólny przebieg procesu

Przepływ obejmuje siedem zadań Airflow:

1. `raw_load`,
2. `staging_load`,
3. `preprocessing_load`,
4. `teryt_load`,
5. `validation_load`,
6. `integration_golden_match`,
7. `golden_load`.

Zadanie `integration_golden_match` obejmuje trzy kolejne operacje backendu: wyszukanie kandydatów metodą Levenshteina, ich ponowną ocenę metodą Jaro-Winklera oraz utworzenie grup encji. DAG zawiera więc siedem zadań Airflow, mimo że etap integracji wykonuje trzy wywołania API.

Zależności w DAG-u są liniowe. Następne zadanie rozpoczyna się dopiero po poprawnym zakończeniu poprzedniego:

```text
raw_load
  -> staging_load
  -> preprocessing_load
  -> teryt_load
  -> validation_load
  -> integration_golden_match
  -> golden_load
```

Takie wykonanie odpowiada zależnościom danych: staging wymaga materiału RAW, preprocessing wymaga stagingu, walidacja korzysta z danych po preprocessingu, a goldenizacja wymaga wyników matchingu i grupowania.

## Parametry uruchomienia DAG-u

DAG przyjmuje parametry opisujące źródło danych, typ encji oraz konfigurację walidacji i matchingu.

| Parametr | Wartość domyślna | Znaczenie |
|---|---|---|
| `file_path` | `/opt/airflow/data/csv/pesel.csv` | ścieżka pliku dostępna w kontenerze Airflow |
| `input_type` | `FILE` | sposób pobrania danych: `FILE` albo `RELATIONAL` |
| `source_system_code` | `AUTO` | kod źródła lub automatyczne rozpoznanie |
| `query_name` | `insurance_core_export` | nazwa dozwolonego zapytania dla źródła relacyjnego |
| `entity_type` | `AUTO` | `PERSON`, `PARTY` albo automatyczny wybór |
| `created_by` | `airflow` | oznaczenie procesu inicjującego import |
| `check_email_dns` | `true` | włączenie kontroli DNS domen adresów e-mail |
| `matching_min_score` | `0.50` | minimalny wynik pierwszego etapu matchingu |
| `matching_max_pairs` | `2000000` | limit liczby porównywanych par |
| `jaro_winkler_min_score` | `0.78` | minimalny wynik drugiego etapu matchingu |

Wartości z konfiguracji konkretnego uruchomienia `dag_run.conf` mają pierwszeństwo przed wartościami zdefiniowanymi w `params`. Łączenie konfiguracji realizuje funkcja `_conf()`.

### Automatyczne rozpoznawanie źródła

Dla importu plikowego funkcja `_source_system_code()` ustala kod źródła z nazwy pliku zgodnie z mapą `SOURCE_SYSTEM_BY_FILE_STEM`. Obejmuje ona przygotowane zbiory CEIDG, GLEIF, KRS, PESEL, REGON, VAT oraz rejestry KNF używane w danych syntetycznych. Dla nieznanej nazwy wymagane jest jawne podanie `source_system_code`. Dla `input_type=RELATIONAL` domyślnym źródłem jest `INSURANCE_CORE`.

### Automatyczne rozpoznawanie typu encji

Typ encji może zostać podany bezpośrednio jako `PERSON` lub `PARTY`. Przy wartości `AUTO` jest wybierany na podstawie źródła.

Źródła `GLEIF`, `REGON`, `VAT`, `KNF_PIENIADZ_ELEKTRONICZNY` oraz `INSURANCE_CORE` mają określony domyślny typ. Dla CEIDG, KRS i części rejestrów KNF proces wykonuje obie ścieżki: `PARTY` i `PERSON`.

Import relacyjny również domyślnie wykonuje oba typy encji. W takim przypadku backend pobiera dane osobno dla osoby i podmiotu, tworząc dwa materiały RAW i dwie partie importu.

## Komunikacja Airflow z FastAPI

Wszystkie operacje są wywoływane metodą HTTP `POST`. Adres bazowy API w środowisku kontenerowym to:

```text
http://api:8000/layers
```

Funkcja `_post_form()` wysyła formularz, opcjonalnie wraz z plikami. Limit czasu pojedynczego żądania wynosi 300 sekund. Odpowiedź HTTP spoza zakresu powodzenia powoduje zgłoszenie `RuntimeError` zawierającego:

- metodę i endpoint,
- kod odpowiedzi,
- treść odpowiedzi backendu.

Poprawna odpowiedź jest deserializowana z JSON i zwracana przez zadanie. PythonOperator automatycznie zapisuje zwracaną wartość w XCom.

### Zestawienie wywołań API

| Operacja | Endpoint |
|---|---|
| import pliku | `POST /layers/ingestion/raw-load` |
| import relacyjny | `POST /layers/ingestion/relational-load` |
| staging | `POST /layers/staging_validation/staging-load` |
| preprocessing | `POST /layers/preprocessing/preprocessing-load` |
| załadowanie TERYT | `POST /layers/validation/teryt-load` |
| walidacja | `POST /layers/validation/validation-load` |
| Levenshtein | `POST /layers/integration_golden/match-candidates` |
| Jaro-Winkler | `POST /layers/integration_golden/match-candidates/jaro-winkler` |
| grupowanie | `POST /layers/integration_golden/match-groups` |
| materializacja GOLD | `POST /layers/integration_golden/golden-load` |

Endpointy przekazują logikę do funkcji serwisowych. Serwisy korzystają z repozytoriów SQLAlchemy, które wykonują odczyt i zapis w SQL Serverze.

## Przekazywanie identyfikatorów

### ImportBatch_ID

`ImportBatch_ID` jest tworzony przez backend podczas operacji RAW load. Reprezentuje pojedynczy import z określonego systemu źródłowego.

Identyfikator partii nie jest bezpośrednio przekazywany pomiędzy zadaniami Airflow. Kolejne warstwy otrzymują `RawFile_ID` i odczytują z `raw.RawFile` powiązany `ImportBatch_ID`. Ogranicza to liczbę parametrów przekazywanych przez DAG i zapewnia, że dalsze kroki używają partii przypisanej w bazie do konkretnego materiału RAW.

### RawFile_ID

`RawFile_ID` jest podstawowym identyfikatorem przekazywanym pomiędzy zadaniami. `raw_load` zwraca go z odpowiedzi backendu, a kolejne zadania pobierają wartość przez:

```python
context["ti"].xcom_pull(task_ids="raw_load")
```

Dla procesu obejmującego jeden materiał RAW wartością XCom jest liczba całkowita. Dla importu relacyjnego obejmującego obie encje wynik jest słownikiem:

```text
{
  "PERSON": <RawFile_ID>,
  "PARTY": <RawFile_ID>
}
```

Każdy kolejny krok wybiera identyfikator właściwy dla aktualnie przetwarzanego typu encji.

Przy pliku zawierającym oba typy encji ten sam `RawFile_ID` jest używany dwukrotnie: raz do zbudowania stagingu `PERSON`, a drugi raz do stagingu `PARTY`. Rozdzielenie następuje przez parametr `entity_type` i osobne tabele docelowe.

## Zakres zadań DAG-u

| Zadanie | Odpowiedzialność orkiestracyjna | Wynik |
|---|---|---|
| `raw_load` | wybór trybu FILE lub RELATIONAL i wywołanie rejestracji RAW | pojedynczy `RawFile_ID` albo mapa identyfikatorów według typu encji |
| `staging_load` | uruchomienie ładowania STAGING dla ustalonych typów encji | wyniki wywołań API |
| `preprocessing_load` | uruchomienie standaryzacji i deduplikacji technicznej | wyniki wywołań API |
| `teryt_load` | przekazanie do API plików SIMC i ULIC | wynik ładowania danych referencyjnych |
| `validation_load` | uruchomienie walidacji, w tym opcjonalnej kontroli DNS poczty elektronicznej | wyniki walidacji |
| `integration_golden_match` | sekwencyjne uruchomienie Levenshteina, Jaro-Winklera i grupowania | zbiorczy wynik trzech operacji |
| `golden_load` | uruchomienie materializacji złotych rekordów dla bieżącej partii | utworzone lub zaktualizowane rekordy GOLD |

Dla zakresu obejmującego obie encje zadania warstwowe wykonują osobne wywołania dla `PARTY` i `PERSON`. Plik zawierający oba typy danych wykorzystuje ten sam `RawFile_ID`, natomiast wejście relacyjne zwraca osobne identyfikatory partii. Grupowanie działa dla całego typu encji i nie otrzymuje `RawFile_ID`.

Pliki `/opt/airflow/data/teryt/SIMC.csv` i `/opt/airflow/data/teryt/ULIC.csv` są przesyłane przy każdym uruchomieniu DAG-u. Brak jednego z nich powoduje błąd przed wywołaniem API. Szczegółowe reguły przetwarzania poszczególnych warstw opisano w kolejnych rozdziałach.

## Statusy i logowanie

Stan procesu jest widoczny na dwóch poziomach:

- Airflow rejestruje stan zadań DAG-u i ich logi wykonania,
- SQL Server przechowuje stan partii oraz wpisy `meta.ProcessLog`.

### Status partii

`meta.ImportBatch.Import_Status` obsługuje wartości:

- `NEW`,
- `PROCESSING`,
- `RAW_LOADED`,
- `STAGING_LOADED`,
- `COMPLETED`,
- `FAILED`.

Aktualna implementacja ustawia statusy podczas RAW load i staging load. Po poprawnym stagingu partia ma status `STAGING_LOADED`. Dalsze etapy nie zmieniają obecnie partii na `COMPLETED`; ich wykonanie jest widoczne w logach właściwych etapów oraz w stanie zadań Airflow.

Status partii `FAILED` jest ustawiany przy błędzie RAW load albo staging load. Błędy preprocessingu, walidacji i ładowania GOLD są zapisywane również w `ProcessLog`, natomiast błędy matchingu i grupowania pozostają widoczne w stanie i logach zadania Airflow.

### ProcessLog

Wpis `ProcessLog` zawiera:

- `ImportBatch_ID`,
- opcjonalny `RawFile_ID`,
- nazwę kroku,
- status `STARTED`, `SUCCESS` albo `FAILED`,
- czas rozpoczęcia i zakończenia,
- liczniki wejścia i wyjścia,
- komunikat błędu.

Logi bazodanowe są tworzone dla:

- `RAW_LOAD`,
- `STAGING_LOAD`,
- `STANDARDIZATION`,
- `VALIDATION`,
- `GOLDEN_LOAD`.

Matching Levenshteina, Jaro-Winklera i grupowanie nie tworzą oddzielnych wpisów `ProcessLog`. Ich przebieg jest widoczny w logach zadania `integration_golden_match` oraz w tabelach wynikowych matchingu.

## Transakcje i powtarzalność

Repozytoria wykonują zatwierdzenia po utworzeniu logów oraz po zapisaniu wyników etapów. W razie błędu serwis wycofuje bieżącą transakcję i, jeżeli log został już utworzony, kończy go statusem `FAILED`.

Powtarzalność operacji zależy od etapu:

| Etap | Zachowanie przy ponownym uruchomieniu |
|---|---|
| RAW load | unikalny hash ogranicza ponowny zapis identycznej zawartości |
| staging | ponowny zapis tego samego RAW i typu encji jest blokowany |
| preprocessing | ponowne przetworzenie istniejących rekordów jest blokowane |
| TERYT | pliki pomocnicze są nadpisywane |
| validation | wcześniejsze wyniki dla RAW i typu encji są zastępowane |
| matching | kandydaci są zastępowani dla tej samej kombinacji typu encji i `RawFile_ID`; ponowienie Levenshteina usuwa również zależne wyniki Jaro-Winklera z tego zakresu |
| grouping | członkostwa grup danego typu są budowane ponownie na podstawie wszystkich aktualnych kandydatów `AUTO_MERGE` tego typu |
| GOLD | repozytorium wyszukuje istniejące wymiary i relacje, a następnie wykonuje create albo update |

Mechanizmy te ograniczają powstawanie duplikatów, ale pełne ponowienie całego DAG-u od początku tworzy nową próbę RAW load. W przypadku potrzeby powtórzenia tylko późniejszego etapu można wywołać odpowiedni endpoint bezpośrednio z istniejącym `RawFile_ID`, z uwzględnieniem zasad danego etapu.

## Obsługa błędów

Backend rozróżnia błędy wejściowe i błędy nieoczekiwane:

- znane problemy danych lub konfiguracji zwracają HTTP 400,
- nieobsłużone wyjątki zwracają HTTP 500 z nazwą etapu.

Przykładowe błędy HTTP 400 obejmują:

- nieobsługiwany format lub system źródłowy,
- brak mapowania kolumn,
- brak materiału RAW,
- ponowne ładowanie stagingu,
- brak rekordów preprocessingowych,
- błędny typ encji,
- przekroczenie limitu par matchingu,
- brak kandydatów wymaganych przez drugi etap.

Airflow traktuje każdą odpowiedź spoza zakresu powodzenia jako wyjątek zadania. Ponieważ zależności są liniowe, niepowodzenie zatrzymuje uruchomienie przed kolejnymi etapami.

Operatory nie mają jawnie skonfigurowanej liczby ponowień ani opóźnienia pomiędzy próbami. Proces korzysta więc z ustawień domyślnych środowiska Airflow. W dostarczonej konfiguracji DAG-u nie zdefiniowano automatycznej polityki retry właściwej dla poszczególnych zadań.

## Ograniczenia orkiestracji

Aktualna orkiestracja jest przeznaczona do kontrolowanego uruchamiania procesu demonstracyjnego. Należy uwzględnić następujące właściwości:

- DAG jest uruchamiany ręcznie i nie ma harmonogramu;
- wszystkie zadania są wykonywane sekwencyjnie;
- lokalny Airflow używa `SequentialExecutor`;
- limit czasu pojedynczego wywołania API wynosi 300 sekund;
- nie skonfigurowano indywidualnych retry zadań;
- TERYT jest przesyłany przy każdym przebiegu;
- trzy operacje matchingu są ukryte w jednym zadaniu Airflow;
- status `ImportBatch` nie jest kończony wartością `COMPLETED` przez ostatnie etapy;
- grupowanie jest wykonywane dla typu encji bez parametru `RawFile_ID`.

Nie uniemożliwia to wykonania pełnego procesu. Właściwości te wpływają przede wszystkim na obserwowalność, selektywne ponawianie kroków i skalowanie wielu równoległych importów.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| definicja DAG-u i parametry | `airflow/dags/goldenizacja_pipeline.py` |
| router warstw | `app/layers/router.py` |
| RAW load | `app/layers/ingestion/api.py`, `service.py`, `repository.py` |
| staging load | `app/layers/staging_validation/api.py`, `service.py`, `repository.py` |
| preprocessing | `app/layers/preprocessing/api.py`, `service.py`, `repository.py` |
| TERYT i walidacja | `app/layers/validation/api.py`, `service.py`, `repository.py` |
| matching, grupowanie i GOLD | `app/layers/integration_golden/api.py`, `service.py`, `repository.py` |
| modele statusów i logów | `app/layers/ingestion/models.py` |
| konfiguracja Airflow | `docker-compose.yml` |
