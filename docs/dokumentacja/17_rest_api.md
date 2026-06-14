# 17. REST API

Interfejs REST jest głównym sposobem uruchamiania kolejnych warstw systemu oraz odczytu wyników procesu. API zostało zbudowane w FastAPI i obejmuje dwa obszary:

1. techniczne endpointy pomocnicze poza głównym pipeline'em,
2. właściwe endpointy warstwowe pod wspólnym prefiksem `/layers`.

Taki podział rozdziela funkcje demonstracyjne od właściwego procesu goldenizacji i ułatwia późniejsze powiązanie operacji z poszczególnymi warstwami kodu.

## 17.1. Organizacja aplikacji

Punktem wejścia jest `app/main.py`. Aplikacja:

- uruchamia inicjalizację bazy przy starcie,
- konfiguruje middleware CORS,
- dołącza router techniczny `app.api.routes`,
- dołącza router warstwowy `app.layers.router`.

Router warstwowy posiada prefiks:

```text
/layers
```

W jego ramach podłączone są routery:

- `ingestion`,
- `staging_validation`,
- `preprocessing`,
- `validation`,
- `integration_golden`,
- `analytics`,
- `serving`.

## 17.2. Styl komunikacji API

API używa dwóch głównych sposobów przekazywania danych:

- formularzy `multipart/form-data` albo `application/x-www-form-urlencoded` dla operacji uruchamiających pipeline,
- parametrów zapytania dla endpointów odczytowych warstwy `serving`.

W praktyce oznacza to, że:

- endpointy importu plików i ładowania warstw przyjmują parametry przez `Form` i `File`,
- endpointy list, wyszukiwania, historii i porównań korzystają z `Query`.

Odpowiedzi są zwracane jako JSON zgodny z modelami Pydantic z plików `schemas.py`.

## 17.3. Endpointy techniczne poza `/layers`

Router `app.api.routes` zawiera pomocnicze trasy demonstracyjne:

```text
GET  /health
POST /documents
GET  /documents
GET  /documents/search
POST /files/line-count
```

Ich rola jest pomocnicza:

- `GET /health` służy do prostego sprawdzenia dostępności API,
- endpointy `/documents` pokazują demonstracyjną integrację SQL i Neo4j,
- `POST /files/line-count` jest niezależnym testowym endpointem uploadu pliku CSV.

Endpointy te nie należą do głównego pipeline'u goldenizacji i nie powinny być traktowane jako interfejs biznesowy systemu.

## 17.4. Endpointy statusowe warstw

Każda główna warstwa posiada prosty endpoint:

```text
GET /layers/<warstwa>/status
```

Dotyczy to warstw:

- `ingestion`,
- `staging_validation`,
- `preprocessing`,
- `validation`,
- `integration_golden`,
- `analytics`,
- `serving`.

Odpowiedź ma jednolity schemat `LayerStatus` i zawiera nazwę warstwy oraz status `ready`. Endpointy te służą głównie do szybkiej diagnostyki i weryfikacji dostępności modułu.

## 17.5. Endpointy sterujące pipeline'em

Główna ścieżka przetwarzania jest udostępniona przez endpointy `POST` pod `/layers`. Najważniejsze z nich to:

```text
POST /layers/ingestion/raw-load
POST /layers/ingestion/relational-load
POST /layers/staging_validation/staging-load
POST /layers/preprocessing/preprocessing-load
POST /layers/validation/teryt-load
POST /layers/validation/validation-load
POST /layers/integration_golden/match-candidates
POST /layers/integration_golden/match-candidates/jaro-winkler
POST /layers/integration_golden/match-groups
POST /layers/integration_golden/golden-load
```

Są to endpointy uruchamiające logikę kolejnych warstw, a nie tylko zapisujące prosty rekord w bazie. Każde wywołanie kończy się uruchomieniem serwisu i zwróceniem podsumowania wykonania.

### Ingestion

Warstwa `ingestion` udostępnia:

- `GET /layers/ingestion/relational-queries` - listę dozwolonych zapytań relacyjnych,
- `POST /layers/ingestion/raw-load` - import pliku do warstwy RAW,
- `POST /layers/ingestion/relational-load` - import danych z Oracle do RAW.

Import plikowy przyjmuje:

- `file`,
- `source_system_code`,
- opcjonalne `created_by`.

Import relacyjny przyjmuje:

- `source_system_code`,
- `query_name`,
- opcjonalne `entity_type`,
- opcjonalne `created_by`.

### Staging i preprocessing

Warstwy pośrednie używają prostszych formularzy:

- `POST /layers/staging_validation/staging-load`,
- `POST /layers/preprocessing/preprocessing-load`.

Obie operacje przyjmują:

- `raw_file_id`,
- `entity_type`.

### Validation

Warstwa `validation` udostępnia:

- `POST /layers/validation/teryt-load`,
- `POST /layers/validation/validation-load`.

`teryt-load` przyjmuje dwa pliki:

- `SIMC.csv`,
- `ULIC.csv`.

`validation-load` przyjmuje:

- `raw_file_id`,
- `entity_type`,
- `check_email_dns`.

### Integration Golden

Warstwa `integration_golden` udostępnia:

- `POST /layers/integration_golden/match-candidates`,
- `POST /layers/integration_golden/match-candidates/jaro-winkler`,
- `POST /layers/integration_golden/match-groups`,
- `POST /layers/integration_golden/golden-load`.

Etapy matchingu przyjmują:

- `entity_type`,
- opcjonalny `raw_file_id`,
- parametr progu `min_score`,
- a dla Levenshteina także `max_pairs`.

`match-groups` przyjmuje wyłącznie `entity_type`, ponieważ grupowanie działa dla całego typu encji.

`golden-load` przyjmuje:

- `entity_type`,
- opcjonalny `raw_file_id`,
- opcjonalny `entity_group_id`.

## 17.6. Endpointy odczytowe warstwy serving

Warstwa `serving` udostępnia interfejs odczytowy wyników procesu. Wszystkie jej endpointy są oparte o `GET` i modele Pydantic ze schematami paginacji, list i szczegółów.

Najważniejsze trasy to:

```text
GET /layers/serving/golden-records
GET /layers/serving/persons/{person_id}
GET /layers/serving/persons/search/by-pesel
GET /layers/serving/parties/search
GET /layers/serving/parties/{party_id}
GET /layers/serving/lineage/{entity_type}/{record_id}
GET /layers/serving/history/{entity_type}/{record_id}
GET /layers/serving/validation-results
GET /layers/serving/match-results/levenshtein
GET /layers/serving/match-results/jaro-winkler
GET /layers/serving/match-results/comparison
GET /layers/serving/counts
```

Zakres funkcjonalny tych endpointów obejmuje:

- listę rekordów GOLD,
- szczegóły osoby i podmiotu,
- wyszukiwanie po identyfikatorach i nazwie,
- lineage,
- historię zmian,
- listę wyników walidacji,
- listę kandydatów matchingu,
- porównanie dwóch rekordów `preprocessed`,
- liczniki etapów procesu.

## 17.7. Typowe odpowiedzi warstwy serving

Warstwa `serving` korzysta z kilku powtarzalnych wzorców odpowiedzi.

### Listy paginowane

Listy takie jak:

- `golden-records`,
- `validation-results`,
- `match-results/levenshtein`,
- `match-results/jaro-winkler`

zwracają:

- `items` - właściwe rekordy,
- `page` - metadane paginacji (`limit`, `offset`, `total`).

### Szczegóły rekordu

Endpointy szczegółów osoby i podmiotu zwracają:

- podstawowe atrybuty wymiaru,
- listy adresów,
- dla podmiotu także listę identyfikatorów.

### Lineage i historia zmian

Endpointy:

- `/lineage/{entity_type}/{record_id}`,
- `/history/{entity_type}/{record_id}`

zwracają:

- identyfikację encji,
- listę wpisów lineage albo historii zmian.

### Porównanie dwóch rekordów

Endpoint `/match-results/comparison` zwraca:

- `entity_type`,
- `left_preprocessed_id`,
- `right_preprocessed_id`,
- szczegóły kandydata Levenshteina,
- szczegóły kandydata Jaro-Winklera,
- dwa rekordy źródłowe w formie słowników.

Jest to endpoint szczególnie istotny dla frontendu, ponieważ zasila modal porównania par rekordów.

## 17.8. Konwencja błędów

API rozróżnia dwa podstawowe typy błędów:

- błędy wejściowe zwracane jako HTTP 400,
- błędy nieoczekiwane zwracane jako HTTP 500.

W warstwie `serving` pojawiają się również odpowiedzi HTTP 404, gdy żądany rekord GOLD nie istnieje.

Typowy wzorzec jest następujący:

- wyjątki domenowe i walidacyjne są mapowane na `HTTPException(status_code=400, detail=...)`,
- brak rekordu szczegółowego jest mapowany na `404`,
- nieobsłużony wyjątek jest opakowany w `500` z nazwą kroku.

Przykłady:

- błędny typ encji,
- brak danych wejściowych do kroku,
- przekroczenie limitu par matchingu,
- nieistniejący `RawFile_ID`,
- nieistniejący `Person_ID` albo `Party_ID`.

## 17.9. CORS i współpraca z frontendem

W `app/main.py` skonfigurowano middleware CORS z listą źródeł pobieraną z konfiguracji. Dzięki temu frontend działający na innym porcie może wywoływać API lokalnie bez dodatkowego proxy.

Ma to bezpośrednie znaczenie dla frontendu React, który pobiera dane z:

- `/layers/serving/validation-results`,
- `/layers/serving/match-results/levenshtein`,
- `/layers/serving/match-results/jaro-winkler`,
- `/layers/serving/match-results/comparison`.

## 17.10. Swagger i OpenAPI

Ponieważ API jest zbudowane w FastAPI, dokumentacja OpenAPI i interfejs Swagger są generowane automatycznie. Pozwala to:

- przeglądać dostępne endpointy,
- sprawdzać parametry i modele odpowiedzi,
- uruchamiać wywołania testowe bez zewnętrznego klienta.

Swagger jest szczególnie przydatny przy ręcznym uruchamianiu etapów pipeline'u niezależnie od Airflow.

## 17.11. Zakres i ograniczenia API

Najważniejsze ograniczenia obecnej wersji są następujące:

- API nie implementuje uwierzytelniania i autoryzacji,
- endpointy warstwowe są synchroniczne z perspektywy klienta HTTP,
- brak mechanizmu PUSH i webhooków dla zmian danych,
- brak endpointów manualnej obsługi decyzji `REVIEW`,
- techniczne endpointy demonstracyjne współistnieją z głównym API, ale nie są częścią właściwego pipeline'u.

Warstwa `serving` jest odczytowa. Nie służy do edycji Golden Record ani do ręcznego zatwierdzania decyzji integracyjnych.

## 17.12. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `app/main.py` - inicjalizacja aplikacji, CORS i podłączenie routerów,
- `app/api/routes.py` - techniczne endpointy demonstracyjne,
- `app/layers/router.py` - wspólny router warstw pod `/layers`,
- `app/layers/ingestion/api.py` - import plików i źródeł relacyjnych,
- `app/layers/staging_validation/api.py` - ładowanie stagingu,
- `app/layers/preprocessing/api.py` - preprocessing,
- `app/layers/validation/api.py` - TERYT i walidacja,
- `app/layers/integration_golden/api.py` - matching, grupowanie i ładowanie GOLD,
- `app/layers/serving/api.py` - odczyt wyników procesu,
- `app/layers/serving/schemas.py` - modele odpowiedzi list, szczegółów, lineage i matchingu,
- `tests/test_serving_api.py` - testy endpointów warstwy serving,
- `tests/test_health.py` - test prostego endpointu zdrowia aplikacji.
