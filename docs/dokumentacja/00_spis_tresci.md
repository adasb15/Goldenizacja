# Dokumentacja projektu - Platforma Goldenizacji Danych

## Status dokumentu

- Typ: szkielet dokumentacji do zatwierdzenia
- Format docelowy: Microsoft Word (`.docx`)
- Format roboczy: Markdown
- Zakres na tym etapie: spis treści, zakres rozdziałów, plan diagramów i odwołań do kodu
- Dokument źródłowy wymagań: `docs/Materiały/Projekt studencki - Platforma integracyjna CRP.pdf`
- Materiały koncepcyjne zespołu:
  - `docs/Materiały/Prezentacja_1_goldenizacja (1).pdf`
  - `docs/Materiały/Szerszy opis warstw systemu.pdf`

## Zasady przygotowania dokumentacji

1. Dokumentacja opisuje stan faktycznie zaimplementowany.
2. Założenia koncepcyjne niezrealizowane w kodzie są wyraźnie oznaczane jako ograniczenia, elementy poza zakresem albo rozwiązania rozważane.
3. Każdy rozdział techniczny zawiera sekcję **Realizacja w kodzie**, wskazującą:
   - pliki źródłowe,
   - najważniejsze klasy i funkcje,
   - tabele lub inne artefakty danych,
   - testy potwierdzające działanie.
4. W dokumencie nie umieszcza się pełnych listingów kodu. Krótkie fragmenty są używane tylko wtedy, gdy pomagają wyjaśnić mechanizm.
5. Ścieżki do kodu są podawane względem katalogu głównego repozytorium GitLab.
6. Dokumentacja nie zawiera wartości sekretów ani danych dostępowych.
7. Dokument Word powstaje dopiero po zatwierdzeniu rozdziałów roboczych.

---

## Planowana struktura dokumentu

## 1. Strona tytułowa

Zakres:

- pełna nazwa projektu,
- nazwa przedmiotu lub programu,
- autorzy,
- opiekun projektu,
- organizacja,
- wersja dokumentu,
- data opracowania.

Do uzupełnienia przed wygenerowaniem Worda.

## 2. Metryka dokumentu

Zakres:

- cel dokumentacji,
- grupa odbiorców,
- właściciele dokumentu,
- status dokumentu,
- historia zmian i zatwierdzeń,
- lokalizacja kodu źródłowego.

Planowane tabele:

- metryka dokumentu,
- historia wersji.

## 3. Wprowadzenie

Zakres:

- problem integracji danych podstawowych osób i podmiotów,
- rola centralnego repozytorium danych,
- znaczenie goldenizacji,
- przeznaczenie zrealizowanej platformy,
- skrócony opis rozwiązania.

Pojęcia wprowadzane w rozdziale:

- Golden Record,
- matching,
- survivorship,
- lineage,
- partia importu,
- źródło referencyjne.

## 4. Cel i zakres projektu

Zakres:

- cel przekazany przez opiekuna projektu,
- zakres prac wynikający z materiału wejściowego,
- przyjęty zakres wykonanej wersji,
- granice odpowiedzialności systemu,
- elementy pozostające poza wykonanym zakresem.

Źródła:

- `docs/Materiały/Projekt studencki - Platforma integracyjna CRP.pdf`,
- dwa materiały koncepcyjne zespołu,
- aktualny kod repozytorium.

## 5. Wymagania

### 5.1. Wymagania funkcjonalne

Zakres:

- przyjmowanie danych,
- składowanie danych surowych,
- mapowanie i standaryzacja,
- walidacja,
- integracja i goldenizacja,
- audytowalność,
- udostępnianie danych,
- interfejs użytkownika,
- orkiestracja procesu.

### 5.2. Wymagania niefunkcjonalne

Zakres:

- modularność,
- przenośność środowiska,
- konfigurowalność,
- idempotencja,
- diagnostyka i obsługa błędów,
- bezpieczeństwo konfiguracji,
- skalowalność i ograniczenia wydajnościowe.

### 5.3. Macierz realizacji wymagań

Planowane kolumny:

| Id | Wymaganie | Źródło wymagania | Stan | Sposób realizacji | Dowód w kodzie/testach | Ograniczenia |
|---|---|---|---|---|---|---|

Stany:

- zrealizowane,
- zrealizowane z ograniczeniem,
- częściowo zrealizowane,
- niezrealizowane,
- poza zakresem wykonanej wersji.

## 6. Źródła danych i zakres informacyjny

Zakres:

- wykorzystywane rejestry i systemy źródłowe,
- dane osób (`PERSON`),
- dane podmiotów (`PARTY`),
- formaty CSV, JSON, XML i XLSX,
- demonstracyjne relacyjne źródło Oracle,
- dane referencyjne TERYT,
- syntetyczne dane testowe,
- zasady identyfikacji źródła i typu encji.

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

Planowane tabele:

- systemy źródłowe,
- obsługiwane formaty,
- mapowanie źródeł na typ encji.

## 7. Architektura systemu

### 7.1. Architektura logiczna

Zakres:

- podział na warstwy,
- odpowiedzialność modułów,
- kierunek przepływu danych,
- separacja API, logiki biznesowej, repozytoriów i modeli.

### 7.2. Architektura komponentów

Zakres:

- FastAPI,
- React,
- Apache Airflow,
- Microsoft SQL Server,
- Oracle,
- Neo4j,
- wolumeny danych,
- komunikacja pomiędzy komponentami.

### 7.3. Architektura uruchomieniowa

Zakres:

- środowisko lokalne Docker Compose,
- obrazy i kontenery,
- porty i zależności,
- trwałość danych,
- przygotowane zasoby OpenShift.

Realizacja w kodzie:

- `app/main.py`,
- `app/layers/router.py`,
- `docker-compose.yml`,
- `Dockerfile`,
- `frontend/Dockerfile`,
- `openshift/`.

Planowany diagram:

- D-01: diagram architektury komponentów.

## 8. Technologie i narzędzia

Zakres:

- Python i FastAPI,
- SQLAlchemy i PyODBC,
- Microsoft SQL Server,
- Oracle i ODBC,
- Apache Airflow,
- React i Vite,
- Neo4j,
- Docker Compose,
- OpenShift,
- biblioteki walidacji i matchingu.

Realizacja w kodzie:

- `requirements.txt`,
- `frontend/package.json`,
- `docker-compose.yml`,
- pliki Dockerfile.

Planowana tabela:

- technologia, wersja, rola w systemie.

## 9. Model danych

### 9.1. Organizacja schematów

Zakres:

- `meta`,
- `raw`,
- `stg`,
- `gold`.

### 9.2. Metadane i audyt procesu

Najważniejsze tabele:

- `meta.SourceSystem`,
- `meta.ImportBatch`,
- `meta.ColumnMapping`,
- `meta.ProcessLog`.

### 9.3. Warstwa RAW i staging

Najważniejsze tabele:

- `raw.RawFile`,
- `stg.Person_Staging`,
- `stg.Party_Staging`,
- `stg.Person_Preprocessed`,
- `stg.Party_Preprocessed`,
- `stg.Validation_Result`,
- tabele kandydatów i grup.

### 9.4. Warstwa GOLD

Najważniejsze tabele:

- `gold.DimPerson`,
- `gold.DimParty`,
- `gold.DimAddress`,
- tabele identyfikatorów i relacji,
- `gold.EntityChangeLog`,
- tabele lineage.

Realizacja w kodzie:

- `app/layers/*/models.py`,
- `app/models/base.py`,
- `scripts/init_proposed_mssql_schema.sql`.

Planowane diagramy:

- D-02: uproszczony model danych całej platformy,
- D-03: szczegółowy model obszaru GOLD i lineage.

## 10. Przepływ i orkiestracja danych

Zakres:

- przebieg pojedynczej partii importu,
- identyfikatory `ImportBatch_ID` i `RawFile_ID`,
- zależności pomiędzy etapami,
- statusy i logi procesu,
- parametry wykonania,
- obsługa błędów.

Etapy:

1. RAW load,
2. staging load,
3. preprocessing,
4. załadowanie TERYT,
5. validation,
6. matching,
7. grouping,
8. Golden Record load.

Realizacja w kodzie:

- `airflow/dags/goldenizacja_pipeline.py`,
- `app/layers/ingestion/`,
- `app/layers/staging_validation/`,
- `app/layers/preprocessing/`,
- `app/layers/validation/`,
- `app/layers/integration_golden/`.

Planowane diagramy:

- D-04: przepływ danych przez warstwy,
- D-05: DAG Airflow,
- D-06: diagram sekwencji przetwarzania jednej partii.

## 11. Pobieranie i składowanie danych RAW

Zakres:

- import plików,
- import danych relacyjnych,
- walidacja typu i podstawowej struktury wejścia,
- obliczanie SHA-256,
- wykrywanie duplikatów,
- rejestracja źródła i partii,
- zachowanie oryginalnej zawartości,
- logowanie kroku `RAW_LOAD`.

### 11.1. Uzasadnienie użycia VARBINARY(MAX)

Zakres:

- pierwotna koncepcja FILESTREAM,
- środowisko realizacyjne z SQL Server w kontenerze Linux,
- zastosowanie `VARBINARY(MAX)` i mapowania `LargeBinary`,
- zachowanie binarnej, niezmodyfikowanej treści,
- ograniczenie dotyczące dostępu strumieniowego do dużych obiektów.

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
- mapowanie kolumn źródłowych,
- obsługa ścieżek zagnieżdżonych,
- mapowanie do `PERSON` i `PARTY`,
- normalizacja podstawowych typów,
- zachowanie reprezentacji rekordu źródłowego,
- ochrona przed ponownym załadowaniem tej samej paczki.

Realizacja w kodzie:

- `app/layers/staging_validation/api.py`,
- `app/layers/staging_validation/service.py`,
- `app/layers/staging_validation/mapper.py`,
- `app/layers/staging_validation/repository.py`,
- `app/layers/staging_validation/models.py`.

Testy:

- `tests/test_staging_mapper.py`.

Planowana tabela:

- przykładowe mapowania kolumn źródłowych na model kanoniczny.

## 13. Preprocessing i standaryzacja

Zakres:

- normalizacja tekstu,
- standaryzacja nazw,
- normalizacja telefonów i adresów e-mail,
- przetwarzanie dat i wartości logicznych,
- rozdzielanie adresów,
- normalizacja identyfikatorów,
- zapis zastosowanych reguł,
- przygotowanie pól do matchingu.

Realizacja w kodzie:

- `app/layers/preprocessing/api.py`,
- `app/layers/preprocessing/service.py`,
- `app/layers/preprocessing/repository.py`,
- `app/layers/preprocessing/models.py`.

Testy:

- `tests/test_preprocessing.py`.

## 14. Walidacja

Zakres:

- walidacja PESEL, NIP, REGON, KRS, LEI i numeru dowodu osobistego,
- kontrola zależności daty urodzenia i płci z numerem PESEL,
- walidacja nazw,
- kontrola adresu e-mail i opcjonalne sprawdzenie DNS,
- walidacja zakresów dat,
- kontrola adresów z wykorzystaniem TERYT,
- rejestrowanie wyników per reguła,
- kontynuowanie procesu pomimo błędnych rekordów.

Realizacja w kodzie:

- `app/layers/validation/api.py`,
- `app/layers/validation/service.py`,
- `app/layers/validation/repository.py`,
- `app/layers/validation/models.py`.

Testy:

- `tests/test_validation.py`,
- `tests/test_teryt_validation.py`.

Planowana tabela:

- katalog najważniejszych reguł walidacyjnych.

## 15. Matching i grupowanie

### 15.1. Model reguł dopasowania

Zakres:

- identyfikatory silne,
- atrybuty stabilne, półstabilne i dynamiczne,
- pola konfliktowe,
- priorytety i wagi.

### 15.2. Etap Levenshteina

Zakres:

- generowanie kandydatów,
- podobieństwo pól,
- scoring,
- limit liczby par,
- zapis wyników.

### 15.3. Etap Jaro-Winklera

Zakres:

- drugie sito kandydatów,
- podobieństwo tekstowe,
- klasyfikacja wyników.

### 15.4. Decyzje i grupowanie

Zakres:

- `AUTO_MERGE`,
- `REVIEW`,
- kandydaci odrzuceni przez progi,
- tworzenie stabilnych grup,
- grupy jednoelementowe,
- idempotencja ponownego grupowania.

Realizacja w kodzie:

- `app/layers/integration_golden/api.py`,
- `app/layers/integration_golden/service.py`,
- `app/layers/integration_golden/repository.py`,
- `app/layers/integration_golden/models.py`.

Testy:

- `tests/test_integration_golden_matching.py`,
- `tests/test_integration_golden_repository.py`.

Planowane tabele:

- progi decyzyjne,
- pola i role w matchingu,
- interpretacja decyzji.

## 16. Budowa Golden Record

Zakres:

- przetwarzanie grup encji,
- wyszukiwanie istniejących wymiarów,
- tworzenie i aktualizacja osoby lub podmiotu,
- tworzenie i ponowne użycie adresów,
- zapis identyfikatorów podmiotu,
- zapis relacji,
- obsługa wymaganych atrybutów,
- rejestr odrzuconych grup.

### 16.1. Reguły survivorship

Kolejność kryteriów:

1. obecność wartości,
2. wynik walidacji,
3. potwierdzenie adresu w TERYT,
4. priorytet źródła dla danego atrybutu,
5. poziom zaufania źródła,
6. aktualność partii importu,
7. kolejność wejściowa jako rozstrzygnięcie awaryjne.

Realizacja w kodzie:

- funkcje `select_survivor_value()`,
- `create_or_update_golden_person()`,
- `create_or_update_golden_party()`,
- `golden_load_dimensions()`,
- modele i repozytorium `integration_golden`.

Testy:

- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`,
- `tests/test_integration_golden_repository.py`.

Planowany diagram:

- D-07: proces wyboru wartości Golden Record.

## 17. Audytowalność, lineage i zmiany Golden Record

Zakres:

- śledzenie danych od źródła do wymiaru GOLD,
- źródło i identyfikator rekordu źródłowego,
- partia importu,
- reguła wyboru atrybutu,
- poziom zaufania,
- wynik jakości i walidacji,
- historia zmian wartości osoby i podmiotu,
- stara i nowa wartość,
- czas zmiany.

Ocena wymagania:

- audytowalność powstania i zmian Golden Record jest zrealizowana,
- ograniczeniem jest zastępowanie wcześniejszego wpisu lineage dla atrybutu jego aktualnym pochodzeniem.

Realizacja w kodzie:

- `meta.ImportBatch`,
- `meta.ProcessLog`,
- `gold.EntityChangeLog`,
- tabele `Golden*Lineage`,
- `app/layers/integration_golden/repository.py`,
- `app/layers/integration_golden/service.py`.

Testy:

- `tests/test_integration_golden_dimensions.py`.

Planowany diagram:

- D-08: ścieżka pochodzenia atrybutu Golden Record.

## 18. REST API

Zakres:

- organizacja routerów,
- endpointy techniczne i biznesowe,
- parametry wejściowe,
- modele odpowiedzi,
- obsługa błędów HTTP,
- Swagger/OpenAPI,
- endpointy demonstracyjne niezwiązane bezpośrednio z pipeline'em.

Realizacja w kodzie:

- `app/main.py`,
- `app/api/routes.py`,
- `app/layers/router.py`,
- pliki `api.py` i `schemas.py` w warstwach.

Planowane tabele:

- katalog endpointów,
- kody odpowiedzi i znaczenie błędów.

Planowane przykłady:

- import pliku,
- uruchomienie stagingu,
- uruchomienie matchingu,
- budowa Golden Record.

## 19. Interfejs użytkownika

Zakres:

- zastosowana technologia,
- sposób połączenia z API,
- aktualna funkcja testu dostępności backendu,
- zakres niewykonanych widoków profilu Golden Record.

Realizacja w kodzie:

- `frontend/src/App.jsx`,
- `frontend/src/styles.css`,
- `frontend/package.json`.

Ocena:

- interfejs użytkownika jest zrealizowany częściowo i ma charakter technicznego demonstratora.

## 20. Apache Airflow

Zakres:

- rola orkiestratora,
- struktura DAG,
- kolejność zadań,
- parametry wejściowe,
- XCom,
- obsługa źródeł plikowych i relacyjnych,
- komunikacja z API,
- uruchamianie ręczne.

Realizacja w kodzie:

- `airflow/dags/goldenizacja_pipeline.py`,
- konfiguracja usługi `airflow` w `docker-compose.yml`.

Planowany diagram:

- wykorzystanie D-05 lub jego rozszerzonej wersji.

## 21. Uruchomienie lokalne i konfiguracja

Zakres:

- wymagania środowiskowe,
- konfiguracja `.env`,
- uruchomienie przez Docker Compose,
- inicjalizacja baz,
- porty usług,
- dostęp do Swaggera, Airflow i Neo4j,
- zatrzymanie i reset środowiska,
- diagnostyka podstawowych problemów.

Realizacja w kodzie:

- `README.md`,
- `.env` bez prezentowania wartości,
- `docker-compose.yml`,
- `Dockerfile`,
- `scripts/init_proposed_mssql_schema.sql`,
- `scripts/init_oracle_insurance_core.sql`.

Planowane tabele:

- zmienne środowiskowe,
- usługi i porty.

## 22. Wdrożenie OpenShift

Zakres:

- przeznaczenie manifestów,
- ConfigMap,
- Secrets,
- PVC,
- Deployment,
- Service,
- Route,
- sposób aplikowania zasobów,
- elementy wymagające konfiguracji dla konkretnego klastra,
- rozbieżności pomiędzy Docker Compose a aktualnym zestawem manifestów.

Realizacja w kodzie:

- `openshift/README.md`,
- `openshift/*.yaml`.

Ocena:

- przygotowano bazowy zestaw manifestów,
- wdrożenie na rzeczywistym klastrze wymaga konfiguracji środowiskowej i weryfikacji.

## 23. Testy i zapewnienie jakości

Zakres:

- testy jednostkowe,
- testy warstw i API,
- testy mapowania,
- testy preprocessingowe i walidacyjne,
- testy matchingu i Golden Record,
- testy jakości danych syntetycznych,
- testy idempotencji,
- sposób uruchamiania testów,
- wynik testów aktualny na moment finalizacji dokumentu.

Realizacja w kodzie:

- katalog `tests/`,
- `requirements.txt`.

Planowane zestawienia:

- plik testowy i sprawdzany obszar,
- wynik uruchomienia testów,
- znane luki testowe.

Ważne:

- liczba testów i wynik ich wykonania zostaną potwierdzone przed finalizacją,
- brak testów wydajnościowych zostanie jawnie wskazany.

## 24. Bezpieczeństwo i ochrona konfiguracji

Zakres:

- przechowywanie konfiguracji w zmiennych środowiskowych,
- pliki Secrets dla OpenShift,
- brak umieszczania haseł w dokumentacji,
- CORS,
- dostęp do baz i paneli administracyjnych,
- brak uwierzytelniania i autoryzacji w API jako ograniczenie.

Realizacja w kodzie:

- `app/core/config.py`,
- `docker-compose.yml`,
- `openshift/01-configmap.yaml`,
- `openshift/02-secrets.yaml`,
- `app/main.py`.

## 25. Ograniczenia wykonanej wersji

Zakres:

- brak mechanizmu ML/DL,
- brak kompletnej warstwy `analytics`,
- brak REST Out GET/PUSH dla Golden Record,
- brak interfejsu profilu 360 stopni,
- ograniczony frontend,
- Neo4j niewłączony do właściwego pipeline'u Golden Record,
- brak obsługi strumieni i zewnętrznych REST/SOAP jako wejścia,
- brak pełnego procesu manualnej weryfikacji przypadków `REVIEW`,
- brak uwierzytelniania API,
- brak testów wydajnościowych,
- ograniczenia `VARBINARY(MAX)` względem FILESTREAM,
- brak zachowania kolejnych historycznych wersji lineage.

Zasada:

- ograniczenia są opisane rzeczowo, bez deklarowania wykonania funkcji, których nie ma w kodzie.

## 26. Podsumowanie realizacji

Zakres:

- najważniejsze osiągnięte rezultaty,
- stopień realizacji celu projektu,
- wskazanie kompletnego rdzenia pipeline'u,
- rozróżnienie pomiędzy działającym rdzeniem a komponentami demonstracyjnymi,
- syntetyczne podsumowanie macierzy wymagań.

## 27. Słownik pojęć i skrótów

Planowane hasła:

- CRP,
- Golden Record,
- goldenizacja,
- matching,
- survivorship,
- lineage,
- staging,
- preprocessing,
- RAW,
- PARTY,
- PERSON,
- TERYT,
- DAG,
- ODBC,
- REST,
- SCD.

## 28. Załączniki

### 28.1. Pełna macierz wymagań

Rozszerzona wersja macierzy z rozdziału 5.

### 28.2. Katalog endpointów

Pełne zestawienie metod, ścieżek, parametrów i odpowiedzi.

### 28.3. Katalog tabel

Zestawienie tabel według schematów `meta`, `raw`, `stg` i `gold`.

### 28.4. Mapa dokumentacji do kodu

Planowany układ:

| Obszar | API | Service | Repository | Models | Testy |
|---|---|---|---|---|---|
| Ingestion | `app/layers/ingestion/api.py` | `app/layers/ingestion/service.py` | `app/layers/ingestion/repository.py` | `app/layers/ingestion/models.py` | `tests/test_relational_ingestion.py` |
| Staging | `app/layers/staging_validation/api.py` | `app/layers/staging_validation/service.py` | `app/layers/staging_validation/repository.py` | `app/layers/staging_validation/models.py` | `tests/test_staging_mapper.py` |
| Preprocessing | `app/layers/preprocessing/api.py` | `app/layers/preprocessing/service.py` | `app/layers/preprocessing/repository.py` | `app/layers/preprocessing/models.py` | `tests/test_preprocessing.py` |
| Validation | `app/layers/validation/api.py` | `app/layers/validation/service.py` | `app/layers/validation/repository.py` | `app/layers/validation/models.py` | `tests/test_validation.py`, `tests/test_teryt_validation.py` |
| Goldenizacja | `app/layers/integration_golden/api.py` | `app/layers/integration_golden/service.py` | `app/layers/integration_golden/repository.py` | `app/layers/integration_golden/models.py` | `tests/test_integration_golden_*.py` |

### 28.5. Struktura repozytorium

Opis najważniejszych katalogów i plików.

### 28.6. Materiały źródłowe

- dokument opiekuna,
- prezentacja zespołu,
- szerszy opis warstw,
- repozytorium GitLab.

---

## Rejestr planowanych diagramów

| Id | Diagram | Rozdział | Zakres |
|---|---|---|---|
| D-01 | Architektura komponentów | 7 | FastAPI, React, Airflow, MS SQL, Oracle, Neo4j i komunikacja |
| D-02 | Uproszczony model danych | 9 | Schematy `meta`, `raw`, `stg`, `gold` |
| D-03 | Model GOLD i lineage | 9 | Osoba, podmiot, adresy, identyfikatory, relacje i pochodzenie |
| D-04 | Przepływ danych | 10 | Przejście danych przez wszystkie warstwy |
| D-05 | DAG Airflow | 10 i 20 | Zadania oraz ich kolejność |
| D-06 | Sekwencja przetwarzania partii | 10 | Airflow, API, warstwy i bazy |
| D-07 | Wybór wartości Golden Record | 16 | Reguły survivorship |
| D-08 | Lineage atrybutu | 17 | Źródło, staging, Golden Record i rejestr zmian |

## Proponowany podział pracy

### Część I - kontekst i wymagania

- rozdziały 1-6.

### Część II - architektura i dane

- rozdziały 7-10,
- diagramy D-01, D-02, D-03 i D-04.

### Część III - realizacja pipeline'u

- rozdziały 11-17,
- diagramy D-06, D-07 i D-08.

### Część IV - interfejsy i eksploatacja

- rozdziały 18-24,
- diagram D-05.

### Część V - ocena i załączniki

- rozdziały 25-28,
- końcowa macierz wymagań,
- mapa dokumentacji do kodu.

## Elementy wymagające ustalenia

1. Dane na stronę tytułową.
2. Docelowa objętość dokumentu.
3. Poziom szczegółowości modelu danych w głównej treści.
4. Format diagramów roboczych.
5. Czy pełny katalog endpointów i tabel ma znaleźć się w Wordzie, czy tylko w załącznikach.
6. Docelowy adres repozytorium GitLab.
7. Czy w dokumentacji należy umieścić wyniki rzeczywistego przebiegu demonstracyjnego.
8. Zakres danych przykładowych, które można pokazać na zrzutach ekranu.
