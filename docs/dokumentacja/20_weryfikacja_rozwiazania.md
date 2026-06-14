# 20. Weryfikacja rozwiązania

Weryfikacja rozwiązania została oparta przede wszystkim na testach automatycznych backendu oraz na uruchomieniu lokalnego środowiska Docker Compose.

## 20.1. Zakres przyjętej weryfikacji

W aktualnej wersji projektu weryfikacja obejmuje trzy poziomy:

1. testy jednostkowe i komponentowe dla logiki backendowej,
2. testy endpointów odczytowych i wybranych endpointów pipeline'u,
3. lokalne uruchomienie środowiska developerskiego z API, bazami danych, frontendem i Airflow.

Najszersze pokrycie testowe dotyczy warstw:

- `staging_validation`,
- `preprocessing`,
- `validation`,
- `integration_golden`,
- `serving`.

## 20.2. Testy automatyczne backendu

Katalog `tests/` zawiera zestaw testów obejmujących kluczowe elementy przetwarzania danych.

### Import i RAW

Pliki:

- `tests/test_relational_ingestion.py`,
- `tests/test_file_line_count.py`.

Sprawdzane są między innymi:

- ekstrakcja danych relacyjnych i budowa snapshotu JSON,
- dobór zapytań dla `PERSON` i `PARTY`,
- walidacja poprawności parametrów wejściowych,
- pomocniczy endpoint liczenia wierszy CSV.

### Mapowanie do stagingu

Plik:

- `tests/test_staging_mapper.py`.

Zakres testów obejmuje:

- mapowanie rekordów `PERSON` i `PARTY`,
- obsługę różnych struktur wejściowych CSV, JSON i XML,
- budowę `Identifiers_JSON`,
- normalizację dat i wartości logicznych,
- zachowanie linii adresowych i danych relacyjnych,
- ochronę przed ponownym załadowaniem tego samego `RawFile_ID` do tego samego obszaru staging.

### Preprocessing i standaryzacja

Plik:

- `tests/test_preprocessing.py`.

Sprawdzane są między innymi:

- normalizacja tekstu, telefonu i adresu e-mail,
- wydzielanie nazwy i formy prawnej podmiotu,
- rozbicie adresu na pola strukturalne,
- przygotowanie rozszerzonych pól wykorzystywanych później w matchingu.

### Walidacja danych

Pliki:

- `tests/test_validation.py`,
- `tests/test_teryt_validation.py`.

Testy obejmują:

- sumy kontrolne PESEL, NIP, REGON, LEI i dowodu osobistego,
- zgodność PESEL z datą urodzenia i płcią,
- walidację składni e-mail,
- walidację nazw osobowych,
- reguły zakresów dat dla rekordów `PARTY`,
- weryfikację miasta i ulicy względem słowników TERYT.

### Matching, grupowanie i GOLD

Pliki:

- `tests/test_integration_golden_matching.py`,
- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`,
- `tests/test_integration_golden_repository.py`.

Zakres obejmuje:

- decyzje `AUTO_MERGE`, `REVIEW`, `CANDIDATE` i `NO_MATCH`,
- działanie sit Levenshteina i Jaro-Winklera,
- reguły doboru wartości zwycięskiej,
- grupowanie rekordów do `EntityGroup`,
- zapis rekordów GOLD,
- idempotencję zapisów adresów, tożsamości i lineage,
- zapis historii zmian oraz odrzutów przy niespełnieniu warunków biznesowych,
- poprawność obsługi `raw_file_id` w `golden-load`.

### Serving i warstwa API

Pliki:

- `tests/test_serving_api.py`,
- `tests/test_health.py`.

Sprawdzane są:

- odpowiedzi endpointów odczytowych `serving`,
- filtrowanie i paginacja,
- szczegóły rekordów `PERSON` i `PARTY`,
- endpointy wyników walidacji i matchingu,
- endpoint porównania par rekordów,
- endpoint liczników etapów,
- obecność konfiguracji CORS potrzebnej frontendowi,
- podstawowy endpoint zdrowia `/health`.

### Jakość danych syntetycznych

Plik:

- `tests/test_synthetic_data_quality.py`.

Testy te nie sprawdzają logiki API, ale kontrolują jakość przygotowanych danych wejściowych, między innymi przez:

- ograniczenie konfliktów identyfikatorów,
- spójność danych osobowych i firmowych,
- zgodność chronologii wybranych dat.

## 20.3. Weryfikacja lokalnego uruchomienia

Poza testami kod został weryfikowany w lokalnym środowisku kontenerowym opisanym w rozdziale 19.

W praktyce potwierdzony został następujący zakres:

- start backendu FastAPI z inicjalizacją bazy,
- dostępność Swaggera,
- start środowiska Airflow po dostosowaniu obrazu i skryptu startowego do aktualnej wersji,
- rejestracja DAG `goldenizacja_pipeline`,
- działanie lokalnego frontendu React komunikującego się z endpointami `serving`,
- wykonanie pipeline'u z użyciem endpointów warstw backendowych.

Oznacza to, że zweryfikowano nie tylko pojedyncze funkcje, ale również podstawowy przepływ lokalny: API -> warstwy przetwarzania -> zapis do SQL Server -> odczyt przez `serving` i frontend.

## 20.4. Zakres nieobjęty pełną automatyzacją

Obecna weryfikacja ma charakter głównie backendowy.

W szczególności:

- frontend nie ma osobnego zestawu testów automatycznych w repozytorium,
- testy Airflow nie są prowadzone jako osobna warstwa testów jednostkowych DAG-a, lecz przez lokalne uruchomienie i wykonanie pipeline'u,
- manifesty `openshift/` nie stanowią obecnie części potwierdzonego, regularnie testowanego procesu wdrożeniowego.

Nie zmienia to faktu, że rdzeń logiki przetwarzania danych jest objęty testami w kodzie w znacznie większym stopniu niż elementy interfejsu i wdrożenia.

## 20.5. Odniesienia do implementacji

Najważniejsze pliki związane z weryfikacją rozwiązania:

- `tests/test_relational_ingestion.py`,
- `tests/test_staging_mapper.py`,
- `tests/test_preprocessing.py`,
- `tests/test_validation.py`,
- `tests/test_teryt_validation.py`,
- `tests/test_integration_golden_matching.py`,
- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`,
- `tests/test_integration_golden_repository.py`,
- `tests/test_serving_api.py`,
- `tests/test_health.py`,
- `tests/test_synthetic_data_quality.py`,
- `docker-compose.yml`,
- `airflow/dags/goldenizacja_pipeline.py`,
- `app/main.py`.
