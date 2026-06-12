# Wymagania

Wymagania dla platformy wynikają przede wszystkim z dokumentu „Projekt studencki - Platforma integracyjna CRP”, przekazanego przez opiekuna projektu. Dokument określa cel rozwiązania oraz główne bloki funkcjonalne, lecz nie definiuje szczegółowych kryteriów odbioru ani zamkniętej listy przypadków użycia. Materiały przygotowane przez zespół na początku prac rozwijają tę koncepcję o proponowane mechanizmy techniczne. Nie wszystkie opisane w nich rozwiązania zostały ostatecznie wykorzystane.

W poniższym zestawieniu wymagania pierwotne zostały uporządkowane i odniesione do wykonanej implementacji. Ocena dotyczy stanu kodu analizowanego podczas przygotowania dokumentacji. Funkcje obecne wyłącznie jako szkielet, demonstrator albo nieprzetestowana konfiguracja nie są traktowane jako pełna realizacja wymagania.

## Wymagania funkcjonalne

### Przyjmowanie danych z wielu źródeł

Platforma powinna przyjmować dane o osobach i podmiotach pochodzące z różnych systemów i zapisane w różnych formatach. Dokument wejściowy wymienia pliki wsadowe, relacyjne bazy danych, strumienie danych, interfejsy REST oraz zewnętrzne i wewnętrzne źródła referencyjne.

W wykonanym rozwiązaniu zakres wejścia obejmuje pliki CSV, JSON, XML i XLSX oraz dane relacyjne pobierane z demonstracyjnego systemu Oracle. Rejestrowane są źródła odpowiadające między innymi PESEL, CEIDG, KRS, REGON, VAT, GLEIF oraz wybranym rejestrom KNF. Nie wykonano konektorów wejściowych dla strumieni danych i zewnętrznych usług REST lub SOAP.

### Zachowanie danych surowych

Dane przyjęte przez platformę powinny być przechowywane w oryginalnej postaci, bez ingerencji wynikającej z późniejszych transformacji. Każdy import powinien posiadać informacje o źródle, czasie pobrania, rozmiarze i stanie przetwarzania.

Warstwa RAW zapisuje pełną zawartość wejścia jako dane binarne. Dodatkowo przechowywane są nazwa i typ pliku, jego rozmiar, skrót SHA-256, źródło oraz partia importu. Dane relacyjne są najpierw serializowane do dokumentu JSON, który staje się niezmiennym obrazem pobrania i jest przetwarzany dalej tak samo jak pozostałe dane RAW.

### Mapowanie do wspólnego modelu

Platforma powinna przekształcać dane o różnej strukturze do ujednoliconego modelu umożliwiającego wykonywanie wspólnych reguł walidacyjnych i integracyjnych.

Zaimplementowano dwa modele kanoniczne: `PERSON` dla osób oraz `PARTY` dla podmiotów. Mapowanie uwzględnia różnice w nazewnictwie kolumn, wielkości liter, strukturach zagnieżdżonych i formatach plików. Konfiguracja mapowania jest powiązana z systemem źródłowym i typem encji.

### Standaryzacja danych

Przed integracją dane powinny zostać oczyszczone i doprowadzone do porównywalnej postaci. Wymaganie obejmuje między innymi normalizację tekstu, dat, wartości logicznych, danych kontaktowych, identyfikatorów i adresów.

Preprocessing tworzy oddzielne rekordy przygotowane do matchingu. Normalizowane są między innymi nazwy, imiona i nazwiska, identyfikatory, numery telefonów, adresy e-mail, kody pocztowe, formy prawne i elementy adresu. Zastosowane reguły są zapisywane przy rekordzie preprocessingowym.

### Walidacja i kontrola jakości

Platforma powinna wykonywać reguły jakości właściwe dla danych źródłowych, znakować błędne rekordy oraz umożliwiać ich dalszą analizę bez zatrzymywania całego procesu.

Wyniki walidacji są zapisywane osobno dla każdej reguły i rekordu. Kontrole obejmują między innymi PESEL, NIP, REGON, KRS, LEI, numer dowodu osobistego, adres e-mail, nazwy osób, zakresy dat i zgodność danych wynikających z numeru PESEL. Błąd pojedynczego rekordu nie przerywa przetwarzania całej partii.

### Wzbogacanie danymi referencyjnymi

Wymagania zakładają wykorzystanie danych referencyjnych do kontroli lub uzupełniania danych źródłowych.

W wykonanej wersji dane TERYT są używane do sprawdzania występowania miejscowości i ulic. Mechanizm wpływa również na reguły wyboru adresu Golden Record. Nie wykonano szerszego mechanizmu automatycznego uzupełniania brakujących wartości na podstawie wielu źródeł referencyjnych.

### Identyfikacja odpowiadających sobie rekordów

Platforma powinna rozpoznawać rekordy dotyczące tej samej osoby lub tego samego podmiotu. Identyfikacja powinna wykorzystywać zarówno klucze silne, jak i podobieństwo atrybutów niebędących jednoznacznymi identyfikatorami.

Matching uwzględnia identyfikatory takie jak PESEL, NIP, REGON, KRS i LEI, a także dane opisowe, kontaktowe i adresowe. Pierwszy etap wykorzystuje podobieństwo Levenshteina, a drugi Jaro-Winklera. Reguły przypisują polom role i wagi, rozpoznają konflikty danych stabilnych oraz klasyfikują wynik zgodnie z progami decyzyjnymi.

### Grupowanie i budowa Golden Record

Rekordy uznane za reprezentacje tej samej encji powinny otrzymać wspólny klucz integracji i zostać wykorzystane do budowy wynikowej reprezentacji osoby lub podmiotu.

Kandydaci z decyzją `AUTO_MERGE` są grupowani, a rekordy bez połączeń tworzą grupy jednoelementowe. Na podstawie grup tworzone lub aktualizowane są osoby, podmioty, adresy i identyfikatory w schemacie `gold`. Grupy niespełniające minimalnych wymagań mogą zostać zapisane w rejestrze odrzuceń.

### Ranking źródeł i wybór wartości wynikowych

W przypadku konfliktu danych platforma powinna wybrać wartość zgodnie z jakością, istotnością i wiarygodnością źródła oraz aktualnością danych.

Reguły survivorship uwzględniają obecność wartości, status walidacji, potwierdzenie adresu w TERYT, priorytet źródła dla danego atrybutu, poziom zaufania oraz czas rozpoczęcia importu. Informacja o zastosowanym kryterium jest zapisywana w lineage.

### Audytowalność

Proces powinien umożliwiać ustalenie pochodzenia danych, przebiegu przetwarzania, podstaw decyzji integracyjnych oraz zmian Golden Record.

System zapisuje systemy źródłowe, partie importu, pliki RAW, logi kroków, wyniki walidacji, kandydatów matchingu i grupy encji. Lineage wskazuje pochodzenie aktualnych wartości Golden Record oraz regułę ich wyboru. `EntityChangeLog` rejestruje zmiany atrybutów osoby i podmiotu wraz ze starą i nową wartością.

### Orkiestracja procesu

Kolejne etapy powinny tworzyć powtarzalny proces możliwy do uruchomienia dla wybranego źródła i typu encji.

DAG Apache Airflow wykonuje pełną sekwencję od pobrania danych do utworzenia Golden Record. Obsługuje źródła plikowe i relacyjne oraz pozwala konfigurować typ encji, kontrolę DNS i progi matchingu.

### Udostępnianie danych

Założenia przewidują udostępnianie pełnych i dedykowanych widoków danych przez REST, a także przekazywanie aktualizacji do innych systemów.

Wykonane API udostępnia operacje sterujące etapami pipeline'u i ich modele odpowiedzi. Nie wykonano konsumenckich endpointów REST Out zwracających pełny profil Golden Record, dedykowanych widoków ani mechanizmu PUSH lub webhooków.

### Interfejs użytkownika

Platforma powinna zapewniać użytkownikowi dostęp do danych i wyników integracji.

Frontend React pozwala sprawdzić dostępność backendu przez endpoint `/health`. Nie zawiera widoku Golden Record, wyszukiwarki ani interfejsu ręcznej obsługi przypadków `REVIEW`, dlatego wymaganie jest zrealizowane jedynie w zakresie technicznego demonstratora.

### Mechanizm samouczący

Wymagania szczegółowe wskazują na zastosowanie nadzorowanych modeli ML lub DL do automatyzacji integracji danych.

W wykonanym rozwiązaniu nie zastosowano mechanizmu samouczącego. Matching jest deterministyczny i opiera się na jawnych regułach, wagach, progach oraz algorytmach podobieństwa tekstowego. Materiał zespołu opisujący Random Forest należy traktować jako koncepcję, a nie element implementacji.

### Grafowa reprezentacja relacji

Wymagania wskazują potrzebę rozważenia technologii grafowej dla złożonych relacji i widoku 360 stopni.

Neo4j został dodany do konfiguracji środowiska, a moduł demonstracyjny zapisuje do niego dokumenty. Baza grafowa nie została jednak wykorzystana ani przetestowana w głównym procesie goldenizacji i nie zawiera grafowej reprezentacji wynikowych relacji osób i podmiotów.

## Wymagania niefunkcjonalne

### Modularność

Kod powinien umożliwiać rozdzielenie odpowiedzialności poszczególnych etapów. Każda warstwa posiada własne API, serwis, repozytorium, modele oraz schematy odpowiedzi. Wspólny router łączy warstwy zgodnie z kolejnością przepływu danych.

### Powtarzalność i idempotencja

Ponowne wykonanie procesu nie powinno prowadzić do niekontrolowanego powielania danych. Kod blokuje ponowne załadowanie tego samego pliku do tego samego stagingu, zastępuje wyniki kandydatów matchingu dla danego zakresu, stabilnie tworzy grupy i ponownie wykorzystuje istniejące adresy, identyfikatory oraz relacje.

### Diagnostyka i obsługa błędów

Warstwy powinny zwracać jednoznaczne błędy wejścia i logować stan operacji. API rozróżnia błędy danych zwracane jako HTTP 400 od nieoczekiwanych awarii zwracanych jako HTTP 500. `ProcessLog` przechowuje statusy, liczniki i komunikaty błędów dla etapów procesu.

### Konfigurowalność

Parametry połączeń, hasła, CORS oraz ustawienia usług są pobierane ze zmiennych środowiskowych. Progi matchingu i część zachowania walidacji mogą być ustawiane podczas uruchamiania DAG.

### Przenośność środowiska

Podstawowe środowisko uruchomieniowe zostało przygotowane w Docker Compose. Repozytorium zawiera również manifesty OpenShift, ale nie zostały one przetestowane na docelowym klastrze. Nie można więc traktować wdrożenia OpenShift jako potwierdzonej właściwości wykonanej wersji.

### Trwałość i integralność danych

Dane bazowe są przechowywane w trwałych wolumenach. Model SQL Server stosuje klucze obce, ograniczenia unikalności, ograniczenia kontrolne i indeksy. Oryginalna zawartość RAW jest identyfikowana skrótem SHA-256.

### Bezpieczeństwo

Hasła i parametry połączeń są przekazywane przez zmienne środowiskowe, a dla OpenShift przygotowano zasoby Secrets. API nie implementuje jednak uwierzytelniania, autoryzacji ani ograniczeń dostępu do danych, dlatego wymaganie bezpieczeństwa jest spełnione jedynie na poziomie podstawowej separacji konfiguracji.

### Wydajność i skalowalność

Matching posiada limit maksymalnej liczby porównywanych par oraz wykorzystuje wyszukiwanie kandydatów ograniczające pełne porównanie zbioru, gdy repozytorium udostępnia taką możliwość. Model bazy zawiera indeksy dla pól używanych podczas integracji. Nie wykonano jednak testów wydajnościowych ani pomiarów dla dużych wolumenów, dlatego wydajność nie została formalnie potwierdzona.

### Testowalność

Logika biznesowa jest oddzielona od API i dostępu do danych, co umożliwia testowanie jej z repozytoriami zastępczymi. Testy obejmują import relacyjny, mapowanie, preprocessing, walidację, matching, survivorship, grupowanie, Golden Record, lineage, idempotencję i jakość danych syntetycznych.

## Macierz realizacji wymagań

| Id | Wymaganie | Stan realizacji | Realizacja i dowód w kodzie | Testy lub ograniczenia |
|---|---|---|---|---|
| F-01 | Import plików CSV, JSON, XML i XLSX | Zrealizowane | `SUPPORTED_FILE_TYPES`, `import_raw_file()` w `app/layers/ingestion/service.py`; parsery w `app/layers/staging_validation/service.py` | Parsowanie i mapowanie sprawdza `tests/test_staging_mapper.py` |
| F-02 | Import z relacyjnej bazy danych | Zrealizowane | `import_relational_source()`, `extract_relational_records()` i definicje zapytań Oracle w `app/layers/ingestion/service.py` | `tests/test_relational_ingestion.py` |
| F-03 | Import ze strumieni danych i zewnętrznych REST/SOAP | Niezrealizowane | Brak konektorów wejściowych tego typu | Wzmianki w materiałach i README warstwy nie stanowią implementacji |
| F-04 | Zachowanie oryginalnych danych RAW | Zrealizowane | `RawFile.File_Content`, `File_Hash`, `File_Size`; `persist_raw_content()` | Dane przechowywane jako `VARBINARY(MAX)`, nie FILESTREAM |
| F-05 | Rejestracja źródła i partii importu | Zrealizowane | `SourceSystem`, `ImportBatch`, `ProcessLog` w `app/layers/ingestion/models.py` | Logowanie kolejnych etapów jest rozproszone pomiędzy warstwy |
| F-06 | Mapowanie do wspólnego modelu osoby i podmiotu | Zrealizowane | `map_record_to_canonical()`, `PersonStaging`, `PartyStaging` | `tests/test_staging_mapper.py` |
| F-07 | Standaryzacja i preprocessing | Zrealizowane | `build_preprocessed_record()` oraz funkcje normalizacji w `app/layers/preprocessing/service.py` | `tests/test_preprocessing.py` |
| F-08 | Walidacja identyfikatorów i reguł biznesowych | Zrealizowane | `build_person_validation_results()`, `build_party_validation_results()` i walidatory w `app/layers/validation/service.py` | `tests/test_validation.py` |
| F-09 | Wzbogacanie lub weryfikacja danymi referencyjnymi | Zrealizowane z ograniczeniem | Ładowanie oraz walidacja miast i ulic TERYT w `app/layers/validation` | `tests/test_teryt_validation.py`; brak szerszego mechanizmu uzupełniania danych |
| F-10 | Matching po silnych identyfikatorach | Zrealizowane | Reguły pól i `score_match()` w `app/layers/integration_golden/service.py` | `tests/test_integration_golden_matching.py` |
| F-11 | Matching rozmyty | Zrealizowane | `find_match_candidates()` i `refine_match_candidates_with_jaro_winkler()` | Levenshtein i Jaro-Winkler; brak Jaccarda opisanego w koncepcji |
| F-12 | Scoring i klasyfikacja decyzji | Zrealizowane | `classify_match()`, `classify_jaro_winkler_match()`, `MatchDecision` | Progi są konfigurowalne w Airflow |
| F-13 | Grupowanie rekordów | Zrealizowane | `group_auto_merge_candidates()`, `build_entity_groups()`, `add_singleton_entity_groups()` | Testy grupowania i stabilności kluczy w `tests/test_integration_golden_matching.py` |
| F-14 | Budowa Golden Record osoby i podmiotu | Zrealizowane | `golden_load_dimensions()`, `create_or_update_golden_person()`, `create_or_update_golden_party()` | `tests/test_integration_golden_dimensions.py`, `tests/test_integration_golden_load.py` |
| F-15 | Ranking źródeł i reguły survivorship | Zrealizowane | `select_survivor_value()` oraz priorytety źródeł per atrybut | Testy wyboru wartości w `tests/test_integration_golden_matching.py` |
| F-16 | Rejestr przypadków, z których nie można utworzyć Golden Record | Zrealizowane | `GoldenRecordReject`, `record_golden_record_reject()` | `tests/test_integration_golden_load.py` |
| F-17 | Audytowalność pochodzenia Golden Record | Zrealizowane | Tabele `Golden*Lineage`, `write_dimension_lineage()`, lineage relacji adresowych | `tests/test_integration_golden_dimensions.py` |
| F-18 | Rejestr zmian Golden Record | Zrealizowane | `EntityChangeLog`, `record_dimension_changes()`, `record_entity_change()` | Obejmuje aktualizowane atrybuty `DimPerson` i `DimParty` |
| F-19 | Orkiestracja pełnego procesu | Zrealizowane | DAG `goldenizacja_pipeline` w `airflow/dags/goldenizacja_pipeline.py` | Nie wykonano automatycznego harmonogramu; DAG jest uruchamiany ręcznie |
| F-20 | REST API do sterowania pipeline'em | Zrealizowane | Endpointy warstw w `app/layers/*/api.py`, router w `app/layers/router.py` | Dokumentacja OpenAPI generowana przez FastAPI |
| F-21 | REST Out: pełne i dedykowane widoki Golden Record | Niezrealizowane | Warstwa `serving` zawiera jedynie szkielet i endpoint statusowy | Brak endpointów konsumenckich |
| F-22 | PUSH lub webhooki po zmianie danych | Niezrealizowane | Brak implementacji | Wymienione tylko w założeniach i README warstwy |
| F-23 | Interfejs użytkownika do danych | Częściowo zrealizowane | `frontend/src/App.jsx` sprawdza endpoint `/health` | Brak wyszukiwarki, profilu Golden Record i obsługi `REVIEW` |
| F-24 | Mechanizm samouczący ML/DL | Niezrealizowane | Brak bibliotek, modelu, danych uczących i procesu treningowego | Matching jest regułowy; Random Forest występuje wyłącznie w materiale koncepcyjnym |
| F-25 | Grafowa reprezentacja relacji i widok 360 stopni | Niezrealizowane w głównym systemie | Neo4j jest skonfigurowany, a `app/api/routes.py` zawiera demonstracyjny zapis dokumentów | Nieprzetestowane w pipeline'ie; brak grafu osób i podmiotów |
| F-26 | Warstwa analityczna | Częściowo zrealizowane | Istnieje model wymiarowy `gold`; moduł `app/layers/analytics` jest szkieletem | Brak raportów, metryk i projekcji analitycznych |
| N-01 | Architektura modułowa i warstwowa | Zrealizowane | Oddzielne katalogi warstw oraz podział `api/service/repository/models/schemas` | Struktura jest używana w głównym pipeline'ie |
| N-02 | Idempotencja wybranych operacji | Zrealizowane | Ochrona przed ponownym stagingiem, zastępowanie kandydatów, stabilne grupowanie i ponowne użycie wymiarów | Testy idempotencji w plikach `test_staging_mapper.py` i `test_integration_golden_*.py` |
| N-03 | Konfigurowalność środowiska | Zrealizowane | `app/core/config.py`, `.env`, parametry DAG, ConfigMap i Secrets | Wartości sekretów nie powinny być wersjonowane ani publikowane |
| N-04 | Lokalne środowisko kontenerowe | Zrealizowane | `docker-compose.yml`, obrazy aplikacji i trwałe wolumeny | Dotyczy środowiska developerskiego |
| N-05 | Wdrożenie OpenShift | Przygotowane, niezweryfikowane | Manifesty w katalogu `openshift/` | Nie zostały przetestowane na docelowym klastrze; zestaw nie odzwierciedla w pełni aktualnego Compose |
| N-06 | Bezpieczeństwo dostępu do API | Niezrealizowane | Konfiguracja i sekrety są oddzielone od kodu, ale brak mechanizmu użytkowników i uprawnień | Brak uwierzytelniania i autoryzacji |
| N-07 | Testy funkcjonalne | Zrealizowane w kodzie testów | Katalog `tests/` obejmuje główne reguły biznesowe | Wynik całego zestawu zostanie potwierdzony przed finalizacją dokumentacji |
| N-08 | Testy wydajnościowe | Niezrealizowane | Brak scenariuszy obciążeniowych i pomiarów | Istnieje jedynie limit bezpieczeństwa liczby par matchingu |
| N-09 | Diagnostyka i obsługa błędów | Zrealizowane | Wyjątki warstw, odpowiedzi HTTP 400/500, `ProcessLog` | Zakres logowania zależy od etapu procesu |

## Podsumowanie oceny

Najpełniej zrealizowana jest centralna część platformy: pobieranie plików i danych relacyjnych, przechowywanie RAW, mapowanie, preprocessing, walidacja, dwuetapowy matching, grupowanie, budowa Golden Record oraz audytowalność. Elementy te posiadają odpowiadające modele danych, endpointy API i testy.

Funkcje związane z końcowym udostępnianiem wiedzy są znacznie mniej rozwinięte. Warstwy analityczna i servingowa mają strukturę przygotowaną do rozbudowy, ale nie oferują widoków Golden Record ani API konsumenckiego. Frontend nie realizuje dostępu do danych biznesowych, a Neo4j nie jest częścią pipeline'u.

Nie wykonano również mechanizmu samouczącego, wejść strumieniowych, integracji z zewnętrznymi usługami REST lub SOAP, procesu manualnej obsługi decyzji `REVIEW`, zabezpieczeń API i testów wydajnościowych. Ograniczenia te nie wpływają na działanie wykonanego rdzenia integracyjnego, lecz oznaczają, że platforma nie realizuje pełnego zakresu rozwiązania docelowego opisanego w materiałach wejściowych.
