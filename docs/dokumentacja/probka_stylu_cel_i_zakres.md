# Cel i zakres projektu

Projekt dotyczy budowy platformy integrującej podstawowe dane o osobach i podmiotach pochodzące z wielu niezależnych źródeł. Punktem wyjścia były wymagania opisujące rozwiązanie pełniące funkcję centralnego repozytorium, w którym dane źródłowe są przyjmowane, standaryzowane, walidowane, łączone i udostępniane w postaci możliwie spójnych rekordów referencyjnych. Istotnym elementem takiego rozwiązania jest goldenizacja, czyli identyfikowanie rekordów odnoszących się do tej samej osoby lub tego samego podmiotu, a następnie wybór najbardziej wiarygodnych wartości poszczególnych atrybutów.

Wykonana platforma realizuje podstawowy proces przetwarzania od przyjęcia danych do utworzenia Golden Record. Dane mogą być dostarczane w plikach CSV, JSON, XML i XLSX. Zaimplementowano również pobieranie danych z demonstracyjnego systemu relacyjnego Oracle przez połączenie ODBC. Obsługiwane źródła obejmują między innymi dane odpowiadające rejestrom PESEL, CEIDG, KRS, REGON, VAT i GLEIF oraz wybranym rejestrom KNF. Na potrzeby sprawdzania reguł jakości i matchingu przygotowano także zestawy danych syntetycznych.

Proces został podzielony na niezależne warstwy. Warstwa pobierania rejestruje źródło i partię importu, sprawdza podstawową poprawność wejścia oraz zapisuje oryginalną zawartość. Następnie dane są mapowane do wspólnego modelu osoby lub podmiotu, normalizowane i poddawane walidacji. Kolejne etapy wyznaczają kandydatów do połączenia, grupują rekordy oraz budują wynikowe encje w warstwie GOLD. Wybór wartości Golden Record uwzględnia wynik walidacji, priorytet źródła dla danego atrybutu, poziom zaufania do źródła oraz aktualność partii importu.

Jednym z głównych założeń projektu jest audytowalność przetwarzania. System przechowuje informacje o partiach importu, źródłach, wykonanych krokach i wynikach walidacji. Dla atrybutów Golden Record zapisywane są również informacje o rekordzie źródłowym, zastosowanej regule wyboru, poziomie zaufania i ocenie jakości. Zmiany wartości danych osoby i podmiotu są rejestrowane wraz z poprzednią i nową wartością oraz datą zmiany. Pozwala to ustalić zarówno sposób powstania aktualnego rekordu, jak i przebieg późniejszych aktualizacji.

Orkiestrację procesu zapewnia Apache Airflow. DAG `goldenizacja_pipeline` wykonuje kolejno import RAW, załadowanie danych do stagingu, preprocessing, załadowanie danych referencyjnych TERYT, walidację, dwa etapy matchingu, grupowanie oraz budowę Golden Record. Poszczególne operacje są udostępnione również przez interfejs REST aplikacji FastAPI. Dane procesowe i wynikowe są składowane w Microsoft SQL Server.

Zakres wykonanej platformy nie obejmuje wszystkich elementów wymienionych w pierwotnej koncepcji. Matching jest realizowany przez jawne reguły, wagi oraz algorytmy podobieństwa tekstowego, bez modelu ML lub DL. Warstwy analityczna i udostępniania stanowią przygotowany szkielet, ale nie udostępniają jeszcze kompletnego profilu 360 stopni ani mechanizmu powiadomień PUSH. Frontend React służy obecnie do technicznego sprawdzenia połączenia z API. Neo4j jest dostępny w środowisku uruchomieniowym i wykorzystywany przez moduł demonstracyjny, lecz nie został włączony do głównego procesu budowy Golden Record.

Tak określony zakres pozwolił skoncentrować realizację na najważniejszej części zadania: powtarzalnym i audytowalnym przetwarzaniu danych heterogenicznych, kontroli ich jakości, identyfikacji odpowiadających sobie rekordów oraz budowie wspólnej reprezentacji osoby lub podmiotu.

## Odniesienie do implementacji

Podział warstw aplikacji jest zdefiniowany w `app/layers/router.py`. Implementacja procesu znajduje się przede wszystkim w modułach:

- `app/layers/ingestion`,
- `app/layers/staging_validation`,
- `app/layers/preprocessing`,
- `app/layers/validation`,
- `app/layers/integration_golden`.

Przebieg procesu Airflow znajduje się w `airflow/dags/goldenizacja_pipeline.py`. Modele bazodanowe są rozdzielone pomiędzy pliki `models.py` poszczególnych warstw, natomiast pełny skrypt tworzący strukturę Microsoft SQL Server znajduje się w `scripts/init_proposed_mssql_schema.sql`. Środowisko lokalne jest definiowane przez `docker-compose.yml`.

Zgodność najważniejszych mechanizmów z założonym działaniem jest sprawdzana między innymi przez:

- `tests/test_relational_ingestion.py`,
- `tests/test_staging_mapper.py`,
- `tests/test_preprocessing.py`,
- `tests/test_validation.py`,
- `tests/test_teryt_validation.py`,
- `tests/test_integration_golden_matching.py`,
- `tests/test_integration_golden_dimensions.py`,
- `tests/test_integration_golden_load.py`.
