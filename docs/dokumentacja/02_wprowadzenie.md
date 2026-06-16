# 2. Wprowadzenie

Dane opisujące osoby i podmioty są wykorzystywane przez wiele systemów i procesów, lecz często występują w różnych strukturach, formatach i poziomach jakości. Ten sam podmiot może być zapisany pod kilkoma nazwami, a informacje o jego identyfikatorach, adresach lub danych kontaktowych mogą być rozproszone pomiędzy niezależnymi źródłami. Analogiczny problem dotyczy osób, dla których poszczególne systemy mogą przechowywać różne warianty imienia i nazwiska, adresu, dokumentów tożsamości lub danych kontaktowych.

Samo zgromadzenie takich danych w jednym miejscu nie rozwiązuje problemu ich niespójności. Konieczne jest zachowanie danych źródłowych, ujednolicenie ich struktury, kontrola poprawności, rozpoznanie rekordów odnoszących się do tej samej encji oraz wybór wartości, które powinny utworzyć jej wynikową reprezentację. Proces ten powinien być powtarzalny i audytowalny, tak aby możliwe było ustalenie źródła każdej istotnej informacji oraz przyczyny podjęcia decyzji o połączeniu rekordów.

W ramach projektu wykonano platformę integracji i goldenizacji danych podstawowych osób i podmiotów. Rozwiązanie przyjmuje dane z wielu źródeł, zapisuje ich oryginalną zawartość, mapuje je do wspólnego modelu, wykonuje preprocessing i walidację, a następnie przeprowadza matching oraz grupowanie rekordów. Ostatnim etapem jest utworzenie lub aktualizacja Golden Record, stanowiącego spójną reprezentację osoby albo podmiotu.

Platforma została zaprojektowana warstwowo. Poszczególne etapy przetwarzania są rozdzielone pomiędzy moduły pobierania danych, stagingu, preprocessingu, walidacji oraz integracji. Ułatwia to niezależne rozwijanie i testowanie reguł właściwych dla każdego etapu. Operacje warstw są dostępne przez interfejs REST aplikacji FastAPI, natomiast ich wykonanie w pełnym procesie koordynuje Apache Airflow. Podstawowym repozytorium danych procesowych i wynikowych jest Microsoft SQL Server.

Istotną cechą rozwiązania jest rozdzielenie dwóch typów encji. Model `PERSON` obejmuje dane osób, takie jak imiona, nazwiska, PESEL, dokumenty tożsamości, data urodzenia, dane kontaktowe i adresowe. Model `PARTY` służy do reprezentowania podmiotów i zawiera między innymi nazwę, formę prawną, identyfikatory NIP, REGON, KRS i LEI, dane rejestrowe oraz adresy. Rozdzielenie modeli pozwala stosować różne reguły walidacji, priorytety źródeł i kryteria dopasowania.

Goldenizacja jest w projekcie rozumiana jako proces składający się z trzech głównych działań. Pierwszym jest wyszukanie kandydatów do połączenia na podstawie identyfikatorów oraz podobieństwa pozostałych atrybutów. Drugim jest grupowanie rekordów uznanych za reprezentacje tej samej encji. Trzecim jest wybór wartości wynikowych, określany również jako survivorship. Wybór uwzględnia między innymi wynik walidacji, priorytet źródła dla danego pola, poziom zaufania do źródła oraz aktualność importu.

System zachowuje informacje niezbędne do prześledzenia procesu. Rejestrowane są systemy źródłowe, partie importu, pliki RAW, wyniki kolejnych kroków, reguły walidacyjne, kandydaci matchingu oraz grupy encji. Dla atrybutów zapisanych w warstwie GOLD przechowywane jest ich pochodzenie, zastosowana reguła wyboru oraz informacje o jakości i zaufaniu. Aktualizacje danych osoby i podmiotu są dodatkowo odnotowywane w rejestrze zmian.

Dokumentacja opisuje zarówno sposób działania platformy, jak i jej realizację techniczną. Przedstawia źródła danych, architekturę, model bazodanowy, kolejne etapy pipeline'u, algorytmy matchingu, reguły budowy Golden Record oraz mechanizmy audytowe. Uwzględnia również uruchomienie lokalne, interfejsy API, testy, nieprzetestowane manifesty OpenShift oraz pozostałe ograniczenia wykonanej wersji. Odniesienia do plików, klas, funkcji i testów umożliwiają powiązanie opisu z kodem przechowywanym w repozytorium.

## 2.1. Podstawowe pojęcia

**Golden Record** to wynikowa reprezentacja osoby lub podmiotu zbudowana z wartości wybranych spośród rekordów źródłowych należących do tej samej grupy.

**Goldenizacja** oznacza proces identyfikacji odpowiadających sobie rekordów, ich grupowania oraz budowy Golden Record.

**Matching** jest procesem oceny, czy dwa rekordy mogą opisywać tę samą osobę lub ten sam podmiot. W projekcie wykorzystywane są zarówno silne identyfikatory, jak i podobieństwo pozostałych pól.

**Survivorship** określa reguły wyboru wartości, która zostanie zapisana w Golden Record, gdy rekordy źródłowe zawierają różne warianty tego samego atrybutu.

**Lineage** opisuje pochodzenie danych. Pozwala powiązać atrybut Golden Record z systemem źródłowym, rekordem wejściowym, partią importu i regułą wyboru.

**Partia importu** jest jednostką organizującą pojedyncze pobranie danych ze wskazanego źródła. Jej identyfikator umożliwia powiązanie danych i logów powstających w kolejnych warstwach.

**Warstwa RAW** przechowuje oryginalną zawartość danych przyjętych przez platformę, zanim zostaną one przekształcone.

**Staging** jest warstwą pośrednią, w której dane źródłowe są mapowane do wspólnej struktury osoby lub podmiotu.

**Preprocessing** obejmuje standaryzację i normalizację wartości przed walidacją oraz matchingiem.

## 2.2. Odniesienie do implementacji

Główna aplikacja FastAPI jest konfigurowana w `app/main.py`, a routery warstw są łączone w `app/layers/router.py`. Logika procesu znajduje się w katalogach:

- `app/layers/ingestion`,
- `app/layers/staging_validation`,
- `app/layers/preprocessing`,
- `app/layers/validation`,
- `app/layers/integration_golden`.

Orkiestrację pełnego przebiegu realizuje DAG `goldenizacja_pipeline` zdefiniowany w `airflow/dags/goldenizacja_pipeline.py`. Modele danych są zapisane w plikach `models.py` poszczególnych warstw, a odpowiadający im skrypt Microsoft SQL Server znajduje się w `scripts/init_proposed_mssql_schema.sql`.
