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

Zadanie `integration_golden_match` wykonuje trzy kolejne operacje backendu:

1. wyszukanie kandydatów metodą Levenshteina,
2. ponowną ocenę kandydatów metodą Jaro-Winklera,
3. utworzenie grup encji.

Na poziomie funkcjonalnym pełny proces składa się zatem z dziewięciu kolejnych operacji:

| Lp. | Operacja | Warstwa docelowa | Wynik |
|---:|---|---|---|
| 1 | pobranie danych i RAW load | `meta`, `raw` | partia importu i materiał RAW |
| 2 | staging load | `stg` | rekordy osoby lub podmiotu w modelu kanonicznym |
| 3 | preprocessing | `stg` | wartości znormalizowane |
| 4 | załadowanie TERYT | pliki pomocnicze API | dane referencyjne miejscowości i ulic |
| 5 | validation | `stg` | wyniki reguł jakości |
| 6 | matching Levenshteina | `stg` | pierwszy zbiór par kandydatów |
| 7 | matching Jaro-Winklera | `stg` | ponowna ocena kandydatów tekstowych |
| 8 | grouping | `stg` | grupy rekordów opisujących tę samą encję |
| 9 | Golden Record load | `gold` | wymiary, relacje, lineage i historia zmian |

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

Dla importu plikowego kod źródła może zostać ustalony na podstawie nazwy pliku. Funkcja `_source_system_code()` porównuje nazwę bez rozszerzenia z mapą `SOURCE_SYSTEM_BY_FILE_STEM`.

Obsługiwane automatycznie nazwy obejmują między innymi:

- `ceidg`,
- `gleif`,
- `krs`,
- `pesel`,
- `regon`,
- `vat`,
- cztery pliki rejestrów KNF używane w danych syntetycznych.

Jeżeli nazwa pliku nie występuje w mapie, uruchamiający musi podać `source_system_code`. Zapobiega to przypisaniu danych do przypadkowego źródła.

Dla `input_type=RELATIONAL` domyślnym źródłem jest `INSURANCE_CORE`.

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

## Szczegółowy przebieg zadań

### RAW load

Zadanie `raw_load` ustala typ wejścia, źródło i typy encji.

Dla wejścia `FILE`:

1. otwiera plik ze ścieżki widocznej w kontenerze Airflow,
2. wysyła go jako `multipart/form-data`,
3. przekazuje kod źródła i `created_by`,
4. odbiera `import_batch_id` i `raw_file_id`,
5. zwraca `raw_file_id` do XCom.

Dla wejścia `RELATIONAL`:

1. wybiera dozwolone zapytanie,
2. wykonuje osobne wywołanie dla każdego typu encji,
3. backend pobiera dane z Oracle,
4. serializuje wynik do JSON,
5. zapisuje snapshot w `raw.RawFile`,
6. zwraca mapę identyfikatorów RAW.

Backend tworzy `meta.ImportBatch` ze statusem `NEW`, następnie zmienia go na `PROCESSING`. Tworzy także log `RAW_LOAD` ze statusem `STARTED`. Po poprawnym zapisie RAW log otrzymuje status `SUCCESS`, a partia status `RAW_LOADED`.

### Staging load

Zadanie `staging_load` wykonuje endpoint osobno dla każdego typu encji.

Backend:

1. pobiera materiał RAW,
2. ustala jego partię i system źródłowy,
3. odczytuje mapowania kolumn,
4. parsuje format wejściowy,
5. mapuje rekordy do modelu kanonicznego,
6. zapisuje `Person_Staging` albo `Party_Staging`.

Przed zapisem sprawdzane jest, czy ten sam `RawFile_ID` nie został już załadowany do wybranej tabeli stagingowej. Mechanizm ogranicza przypadkowe duplikowanie danych po ręcznym ponowieniu operacji.

Na początku partia otrzymuje status `PROCESSING`, a tworzony log `STAGING_LOAD` ma status `STARTED`. Po sukcesie log otrzymuje liczniki rekordów i status `SUCCESS`, natomiast partia przechodzi do `STAGING_LOADED`.

### Preprocessing

Zadanie `preprocessing_load` przekazuje `RawFile_ID` i `entity_type`.

Warstwa:

1. odczytuje rekordy stagingowe materiału RAW,
2. sprawdza, czy nie zostały już przetworzone,
3. normalizuje wartości,
4. zapisuje rekordy w `Person_Preprocessed` albo `Party_Preprocessed`,
5. rejestruje liczbę rekordów wejściowych i wynikowych.

Log procesu używa nazwy kroku `STANDARDIZATION`, ponieważ preprocessing realizuje standaryzację wartości. Powtórna próba przetworzenia już zapisanych rekordów jest zwracana jako kontrolowany błąd danych wejściowych.

### Ładowanie TERYT

Zadanie `teryt_load` odczytuje pliki:

- `/opt/airflow/data/teryt/SIMC.csv`,
- `/opt/airflow/data/teryt/ULIC.csv`.

Jeżeli któregoś pliku brakuje, zadanie kończy się błędem przed wywołaniem API. Pliki są wysyłane do backendu, który zapisuje je w podkatalogu `teryt` ścieżki określonej przez zmienną `FILESTREAM_PATH`.

Jest to operacja przygotowująca dane referencyjne dla walidacji adresów. W obecnym DAG-u wykonywana jest przy każdym uruchomieniu procesu, niezależnie od tego, czy pliki zmieniły się od poprzedniego przebiegu.

### Walidacja

Zadanie `validation_load` wywołuje walidację dla każdego typu encji. Parametr `check_email_dns` jest przekazywany jako wartość formularza.

Backend łączy rekord stagingowy z odpowiadającym mu rekordem preprocessingowym i wykonuje reguły jakości. Przed zapisem usuwa wcześniejsze wyniki dla tej samej kombinacji `RawFile_ID` i `Entity_Type`, dzięki czemu ponowne uruchomienie walidacji zastępuje wynik poprzedniego przebiegu.

Wyniki są zapisywane w `stg.Validation_Result`. Log `VALIDATION` zawiera liczbę rekordów poddanych kontroli oraz liczbę zapisanych wyników reguł. Jeden rekord może wygenerować wiele wpisów walidacyjnych.

### Matching i grupowanie

Zadanie `integration_golden_match` wykonuje sekwencyjnie trzy endpointy dla każdego typu encji.

#### Etap Levenshteina

`match-candidates`:

- pobiera rekordy preprocessingowe wskazanego materiału RAW,
- wyszukuje rekordy możliwe do porównania,
- oblicza wyniki ważone,
- odrzuca wyniki niższe od `matching_min_score`,
- zapisuje kandydatów w `Match_Candidate_Levenshtein`.

Parametr `matching_max_pairs` ogranicza liczbę porównań. Wartość `0` wyłącza limit. Przekroczenie limitu jest kontrolowanym błędem HTTP 400, a nie awarią serwera.

#### Etap Jaro-Winklera

`match-candidates/jaro-winkler` ponownie ocenia kandydatów zapisanych przez pierwszy etap. Wynik jest zapisywany w `Match_Candidate_JaroWinkler`, razem z odwołaniem do kandydata Levenshteina.

Próg `jaro_winkler_min_score` określa minimalny wynik drugiego etapu. Brak kandydatów pierwszego etapu jest obsługiwany jako błąd wejściowy.

#### Grupowanie

`match-groups` buduje grupy na podstawie decyzji `AUTO_MERGE`. Algorytm łączy powiązane rekordy i dodaje grupy jednoelementowe dla rekordów, które nie zostały połączone z innymi.

Endpoint grupowania otrzymuje typ encji, ale nie `RawFile_ID`. Operuje na aktualnym zbiorze kandydatów danego typu i zapisuje wynik do `Entity_Group` oraz `Entity_Group_Member`.

Odpowiedzi trzech operacji są zwracane jako jeden zagnieżdżony wynik zadania Airflow.

### Golden Record load

Ostatnie zadanie wywołuje `golden-load` osobno dla każdego typu encji.

Backend:

1. wybiera grupy dotyczące wskazanego materiału RAW,
2. pobiera rekordy preprocessingowe należące do grupy,
3. buduje kandydatów wartości dla poszczególnych atrybutów,
4. uwzględnia priorytet źródła i wynik walidacji,
5. wybiera wartości wynikowe,
6. wyszukuje istniejący wymiar po silnych identyfikatorach,
7. tworzy albo aktualizuje `DimPerson` lub `DimParty`,
8. zapisuje adresy i identyfikatory,
9. zapisuje lineage wybranych wartości i relacji,
10. rejestruje zmiany w `EntityChangeLog`.

W przypadku encji `PARTY` grupa, dla której po wyborze wartości wynikowych brakuje wymaganej nazwy, nie powoduje przerwania całego zadania. Jest zapisywana w `Golden_Record_Reject` z kodem `MISSING_REQUIRED_GOLDEN_FIELD`, a przetwarzanie pozostałych grup jest kontynuowane.

Log `GOLDEN_LOAD` przechowuje liczbę grup wejściowych i przetworzonych. Odpowiedź API zawiera również liczbę grup odrzuconych oraz zestawienie utworzonych i zaktualizowanych wymiarów.

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

Aktualna implementacja ustawia statusy podczas RAW load i staging load. Po poprawnym stagingu partia ma status `STAGING_LOADED`. Dalsze etapy nie zmieniają obecnie partii na `COMPLETED`; ich wykonanie jest rejestrowane przez `ProcessLog` i stan zadań Airflow.

Status `FAILED` jest ustawiany, jeżeli wystąpi błąd podczas RAW load albo staging load. Błędy późniejszych warstw są zapisywane w odpowiadającym im logu procesu.

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
