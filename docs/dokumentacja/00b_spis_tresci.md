# Dokumentacja projektu - roboczy spis treści v2

## Status dokumentu

- Typ: uproszczony plan finalnej dokumentacji
- Format docelowy: Microsoft Word (`.docx`)
- Format roboczy: Markdown
- Cel: ograniczenie powtórzeń względem `00_spis_tresci.md` i dopięcie dokumentacji bez dużych zmian w już istniejących plikach

## Zasady przygotowania dokumentacji

1. Dokumentacja opisuje stan faktycznie zaimplementowany w aktualnym kodzie.
2. Rozdziały `03`-`14`, które już istnieją, pozostają podstawą dokumentu i są poprawiane tylko wtedy, gdy rozmijają się z kodem.
3. Nowe rozdziały dopisujemy jako osobne pliki, bez przebudowywania całej dotychczasowej struktury.
4. Scalenie treści wykonujemy dopiero przy składaniu wersji finalnej Word.
5. W dokumencie głównym trzymamy opis, a rozbudowane zestawienia tabel, endpointów i mapowań przenosimy do załączników, jeżeli będą za długie.

---

## Planowana struktura dokumentu

## 1. Strona tytułowa

Zakres:

- pełna nazwa projektu,
- autorzy,
- opiekun projektu,
- nazwa przedmiotu lub programu,
- wersja dokumentu,
- data.

Do uzupełnienia na końcu.

## 2. Metryka dokumentu

Zakres:

- cel dokumentacji,
- odbiorca dokumentu,
- status dokumentu,
- historia zmian,
- lokalizacja repozytorium,
- zakres analizowanej wersji kodu.

Planowane tabele:

- metryka dokumentu,
- historia wersji.

## 3. Wprowadzenie

Zakres:

- problem goldenizacji danych,
- rola centralnego repozytorium danych,
- podstawowe pojęcia,
- krótki opis zrealizowanego rozwiązania.

Wykorzystanie istniejącego pliku:

- `03_wprowadzenie.md`.

## 4. Cel i zakres projektu

Zakres:

- cel przekazany przez opiekuna,
- zakres wynikający z materiałów wejściowych,
- zakres wykonanej wersji,
- granice odpowiedzialności systemu,
- elementy poza zakresem implementacji.

Wykorzystanie istniejącego pliku:

- `04_cel_i_zakres_projektu.md`.

Źródła:

- `docs/Materiały/Projekt studencki - Platforma integracyjna CRP.pdf`,
- materiały zespołu z `docs/Materiały`,
- aktualny kod repozytorium.

## 5. Wymagania

### 5.1. Wymagania funkcjonalne

Zakres:

- import danych,
- przechowywanie RAW,
- mapowanie,
- preprocessing,
- walidacja,
- matching i goldenizacja,
- udostępnianie danych,
- audytowalność,
- frontend,
- orkiestracja.

### 5.2. Wymagania niefunkcjonalne

Zakres:

- modularność,
- konfigurowalność,
- powtarzalność,
- diagnostyka,
- bezpieczeństwo konfiguracji,
- przenośność środowiska,
- ograniczenia wydajnościowe.

### 5.3. Macierz realizacji wymagań

Planowane kolumny:

| Id | Wymaganie | Stan | Realizacja | Dowód w kodzie/testach | Ograniczenia |
|---|---|---|---|---|---|

Wykorzystanie istniejącego pliku:

- `05_wymagania.md`.

## 6. Źródła danych

Zakres:

- rejestry i systemy źródłowe,
- zakres danych `PERSON`,
- zakres danych `PARTY`,
- formaty plikowe,
- źródło relacyjne Oracle,
- dane referencyjne TERYT,
- dane syntetyczne,
- zasady rozpoznawania źródła i typu encji.

Wykorzystanie istniejącego pliku:

- `06_zrodla_danych.md`.

Realizacja w kodzie:

- `app/layers/ingestion/service.py`,
- `app/layers/staging_validation/mapper.py`,
- `airflow/dags/goldenizacja_pipeline.py`,
- `data/manifest.json`,
- `data/README.txt`,
- `data/teryt/README.md`.

Testy:

- `tests/test_relational_ingestion.py`,
- `tests/test_staging_mapper.py`,
- `tests/test_synthetic_data_quality.py`.

## 7. Architektura systemu

Zakres:

- architektura logiczna,
- podział na warstwy,
- główne komponenty systemu,
- komunikacja pomiędzy komponentami,
- środowisko lokalne,
- przygotowane zasoby OpenShift.

Wykorzystanie istniejącego pliku:

- `07_architektura_systemu.md`.

Realizacja w kodzie:

- `app/main.py`,
- `app/layers/router.py`,
- `docker-compose.yml`,
- `Dockerfile`,
- `frontend/Dockerfile`,
- `openshift/`.

Planowany diagram:

- wykorzystanie `diagramy/D-01_architektura_komponentow.md`.

## 8. Technologie i narzędzia

Zakres:

- Python i FastAPI,
- SQLAlchemy i ODBC,
- Microsoft SQL Server,
- Oracle,
- Apache Airflow,
- React i Vite,
- Neo4j,
- Docker Compose,
- OpenShift,
- biblioteki do walidacji i matchingu.

Wykorzystanie istniejącego pliku:

- `08_technologie_i_narzedzia.md`.

Realizacja w kodzie:

- `requirements.txt`,
- `frontend/package.json`,
- `docker-compose.yml`,
- `Dockerfile`,
- `airflow/Dockerfile`.

Planowana tabela:

- technologia, wersja, rola w systemie.

## 9. Model danych

Zakres:

- schematy `meta`, `raw`, `stg`, `gold`,
- metadane procesu,
- dane RAW i stagingowe,
- dane GOLD,
- lineage i historia zmian.

Wykorzystanie istniejącego pliku:

- `09_model_danych.md`.

Realizacja w kodzie:

- `app/layers/*/models.py`,
- `app/models/base.py`,
- `scripts/init_proposed_mssql_schema.sql`.

Planowane diagramy:

- uproszczony model całej platformy,
- model obszaru GOLD.

## 10. Przepływ i orkiestracja danych

Zakres:

- przebieg partii importu,
- `ImportBatch_ID` i `RawFile_ID`,
- zależności między etapami,
- logi i statusy,
- parametry wykonania,
- obsługa błędów,
- rola Airflow.

Wykorzystanie istniejącego pliku:

- `10_przeplyw_i_orkiestracja_danych.md`.

Realizacja w kodzie:

- `airflow/dags/goldenizacja_pipeline.py`,
- `airflow/start-airflow.sh`,
- `docker-compose.yml`,
- `app/layers/ingestion/`,
- `app/layers/staging_validation/`,
- `app/layers/preprocessing/`,
- `app/layers/validation/`,
- `app/layers/integration_golden/`.

Planowane diagramy:

- przepływ danych przez warstwy,
- DAG Airflow,
- sekwencja przetwarzania jednej partii.

## 11. Pobieranie i składowanie danych RAW

Zakres:

- import plików,
- import relacyjny,
- walidacja wejścia,
- obliczanie hashy,
- wykrywanie duplikatów,
- rejestracja partii,
- zachowanie oryginalnej treści,
- uzasadnienie `VARBINARY(MAX)` zamiast FILESTREAM.

Wykorzystanie istniejącego pliku:

- `11_pobieranie_i_skladowanie_danych_raw.md`.

Realizacja w kodzie:

- `app/layers/ingestion/api.py`,
- `app/layers/ingestion/service.py`,
- `app/layers/ingestion/repository.py`,
- `app/layers/ingestion/models.py`,
- `scripts/init_proposed_mssql_schema.sql`.

Testy:

- `tests/test_relational_ingestion.py`.

## 12. Staging i mapowanie danych

Zakres:

- parsowanie CSV, JSON, XML i XLSX,
- mapowanie kolumn,
- ścieżki zagnieżdżone,
- model `PERSON` i `PARTY`,
- normalizacja podstawowych typów,
- zachowanie rekordu źródłowego,
- blokada ponownego załadowania tej samej paczki.

Wykorzystanie istniejącego pliku:

- `12_staging_i_mapowanie_danych.md`.

Realizacja w kodzie:

- `app/layers/staging_validation/api.py`,
- `app/layers/staging_validation/service.py`,
- `app/layers/staging_validation/mapper.py`,
- `app/layers/staging_validation/repository.py`,
- `app/layers/staging_validation/models.py`.

Testy:

- `tests/test_staging_mapper.py`.

## 13. Preprocessing i standaryzacja

Zakres:

- normalizacja tekstu,
- przygotowanie nazw i identyfikatorów,
- normalizacja telefonów i e-maili,
- przetwarzanie dat i wartości logicznych,
- pola wykorzystywane w matchingu,
- zapis zastosowanych reguł.

Wykorzystanie istniejącego pliku:

- `13_preprocessing_i_standaryzacja.md`.

Realizacja w kodzie:

- `app/layers/preprocessing/api.py`,
- `app/layers/preprocessing/service.py`,
- `app/layers/preprocessing/repository.py`,
- `app/layers/preprocessing/models.py`.

Testy:

- `tests/test_preprocessing.py`.

## 14. Walidacja

Zakres:

- walidacja PESEL, NIP, REGON, KRS, LEI i dowodu osobistego,
- kontrola nazw,
- kontrola dat,
- walidacja e-mail i DNS,
- TERYT,
- wyniki per reguła,
- kontynuowanie procesu mimo błędnych rekordów.

Wykorzystanie istniejącego pliku:

- `14_walidacja.md`.

Realizacja w kodzie:

- `app/layers/validation/api.py`,
- `app/layers/validation/service.py`,
- `app/layers/validation/repository.py`,
- `app/layers/validation/models.py`.

Testy:

- `tests/test_validation.py`,
- `tests/test_teryt_validation.py`.

## 15. Matching, grupowanie i budowa Golden Record

Zakres:

- model reguł dopasowania,
- silne identyfikatory,
- scoring Levenshteina,
- druga ocena Jaro-Winklera,
- decyzje `AUTO_MERGE` i `REVIEW`,
- grupowanie rekordów,
- grupy jednoelementowe,
- budowa i aktualizacja rekordów GOLD,
- adresy, identyfikatory i relacje,
- reguły survivorship,
- odrzucanie grup niespełniających wymagań.

Nowy plik:

- `15_matching_grupowanie_i_golden_record.md`.

Realizacja w kodzie:

- `app/layers/integration_golden/api.py`,
- `app/layers/integration_golden/service.py`,
- `app/layers/integration_golden/repository.py`,
- `app/layers/integration_golden/models.py`.

Testy:

- `tests/test_integration_golden_matching.py`,
- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`,
- `tests/test_integration_golden_repository.py`.

Planowane diagramy:

- logika matchingu i grupowania,
- proces wyboru wartości Golden Record.

## 16. Audytowalność, lineage i historia zmian

Zakres:

- śledzenie od źródła do GOLD,
- `ProcessLog`,
- lineage aktualnych wartości,
- historia zmian osoby i podmiotu,
- zakres i ograniczenia `EntityChangeLog`,
- ograniczenia historii lineage.

Nowy plik:

- `16_audytowalnosc_lineage_i_historia_zmian.md`.

Realizacja w kodzie:

- `meta.ImportBatch`,
- `meta.ProcessLog`,
- `gold.EntityChangeLog`,
- tabele `Golden*Lineage`,
- `app/layers/integration_golden/repository.py`,
- `app/layers/integration_golden/service.py`.

Testy:

- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`.

Planowany diagram:

- ścieżka pochodzenia atrybutu Golden Record.

## 17. REST API

Zakres:

- organizacja routerów,
- endpointy techniczne i biznesowe,
- modele żądań i odpowiedzi,
- statusy HTTP,
- obsługa błędów,
- Swagger/OpenAPI,
- endpointy warstwowe,
- endpointy odczytowe warstwy `serving`.

Nowy plik:

- `17_rest_api.md`.

Realizacja w kodzie:

- `app/main.py`,
- `app/api/routes.py`,
- `app/layers/router.py`,
- pliki `api.py` i `schemas.py` w warstwach.

Testy:

- `tests/test_serving_api.py`,
- `tests/test_health.py`.

Planowane zestawienia:

- katalog endpointów,
- podstawowe kody odpowiedzi.

## 18. Interfejs użytkownika

Zakres:

- zastosowana technologia,
- architektura aktualnego frontendu,
- komunikacja z backendem,
- aktualne widoki walidacji i matchingu,
- zakres funkcji przygotowanych poza `main`,
- miejsce frontendu w docelowym systemie,
- ograniczenia obecnej integracji.

Nowy plik:

- `18_interfejs_uzytkownika.md`.

Realizacja w kodzie:

- `frontend/src/App.jsx`,
- `frontend/src/main.jsx`,
- `frontend/src/api/serving.js`,
- `frontend/src/features/validation/`,
- `frontend/src/features/matching/`,
- `frontend/src/components/ui/`,
- `frontend/src/styles/`,
- `frontend/package.json`.

Uwaga:

- rozdział ma opisywać stan faktyczny w `main`, z krótkim zaznaczeniem planowanej integracji bardziej rozbudowanego frontendu, jeżeli będzie to potrzebne i da się to opisać rzeczowo.

## 19. Środowisko uruchomieniowe, konfiguracja i wdrożenie

Zakres:

- wymagania środowiskowe,
- `.env`,
- Docker Compose,
- uruchomienie lokalne,
- porty usług,
- inicjalizacja baz,
- dostęp do Swaggera, Airflow i Neo4j,
- konfiguracja Airflow,
- przygotowane manifesty OpenShift,
- rozbieżności między Compose i OpenShift,
- elementy bezpieczeństwa konfiguracji.

Nowy plik:

- `19_srodowisko_uruchomieniowe_konfiguracja_i_wdrozenie.md`.

Realizacja w kodzie:

- `README.md`,
- `docker-compose.yml`,
- `Dockerfile`,
- `airflow/Dockerfile`,
- `airflow/start-airflow.sh`,
- `openshift/README.md`,
- `openshift/*.yaml`.

Planowane tabele:

- usługi i porty,
- najważniejsze zmienne środowiskowe.

## 20. Testy i ograniczenia

Zakres:

- zakres istniejących testów,
- obszary pokryte testami,
- sposób uruchamiania testów,
- aktualny stan potwierdzenia testów,
- brak testów wydajnościowych,
- ograniczenia funkcjonalne i techniczne wykonanej wersji.

Nowy plik:

- `20_testy_i_ograniczenia.md`.

Realizacja w kodzie:

- katalog `tests/`,
- `requirements.txt`,
- bieżące rozdziały dokumentacji opisujące ograniczenia.

Planowane zestawienia:

- plik testowy i sprawdzany obszar,
- lista najważniejszych ograniczeń.

## 21. Podsumowanie realizacji

Zakres:

- najważniejsze osiągnięte rezultaty,
- stopień realizacji celu projektu,
- rozróżnienie między działającym rdzeniem a elementami demonstracyjnymi,
- syntetyczne podsumowanie braków bez rozwlekania ich ponownie.

Nowy plik:

- `21_podsumowanie_realizacji.md`.

## 22. Załączniki

Zakres:

- pełniejsza macierz wymagań,
- katalog endpointów,
- katalog tabel,
- mapa dokumentacji do kodu,
- ewentualne dodatkowe diagramy.

Nowy plik:

- `22_zalaczniki.md`.

---

## Jak obecne pliki wykorzystać bez dużych zmian

Bez zmian albo z drobnymi korektami:

- `03_wprowadzenie.md`,
- `04_cel_i_zakres_projektu.md`,
- `05_wymagania.md`,
- `06_zrodla_danych.md`,
- `07_architektura_systemu.md`,
- `08_technologie_i_narzedzia.md`,
- `09_model_danych.md`,
- `10_przeplyw_i_orkiestracja_danych.md`,
- `11_pobieranie_i_skladowanie_danych_raw.md`,
- `12_staging_i_mapowanie_danych.md`,
- `13_preprocessing_i_standaryzacja.md`,
- `14_walidacja.md`.

Do dopisania jako nowe pliki:

- `01_strona_tytulowa.md`,
- `02_metryka_dokumentu.md`,
- `15_matching_grupowanie_i_golden_record.md`,
- `16_audytowalnosc_lineage_i_historia_zmian.md`,
- `17_rest_api.md`,
- `18_interfejs_uzytkownika.md`,
- `19_srodowisko_uruchomieniowe_konfiguracja_i_wdrozenie.md`,
- `20_testy_i_ograniczenia.md`,
- `21_podsumowanie_realizacji.md`,
- `22_zalaczniki.md`.

## Proponowana kolejność dalszej pracy

1. `15_matching_grupowanie_i_golden_record.md`
2. `16_audytowalnosc_lineage_i_historia_zmian.md`
3. `17_rest_api.md`
4. `18_interfejs_uzytkownika.md`
5. `19_srodowisko_uruchomieniowe_konfiguracja_i_wdrozenie.md`
6. `20_testy_i_ograniczenia.md`
7. `21_podsumowanie_realizacji.md`
8. `01_strona_tytulowa.md`
9. `02_metryka_dokumentu.md`
10. `22_zalaczniki.md`

## Elementy wymagające ustalenia

1. Dane na stronę tytułową.
2. Czy frontend z innego brancha ma być opisany wyłącznie jako planowana integracja, czy jako osobny wariant rozwiązania.
3. Czy katalog endpointów i katalog tabel mają wejść do głównego dokumentu, czy tylko do załączników.
4. Czy w finalnej wersji Word mają znaleźć się wszystkie diagramy, czy tylko wybrane.
5. Czy rozdział o testach ma zawierać faktyczny wynik pełnego uruchomienia testów po finalizacji środowiska.
