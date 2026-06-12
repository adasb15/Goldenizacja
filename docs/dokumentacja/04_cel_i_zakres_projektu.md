# Cel i zakres projektu

## Cel projektu

Celem projektu było wykonanie autonomicznej platformy integracji danych podstawowych osób i podmiotów. Rozwiązanie miało umożliwiać przyjmowanie danych z różnych źródeł, zachowanie ich oryginalnej postaci, kontrolę jakości, integrację rekordów oraz udostępnienie spójnej reprezentacji danych. Założenia przekazane przez opiekuna wskazywały na potrzebę budowy rozwiązania odpowiadającego koncepcji centralnego repozytorium osób i podmiotów, w którym możliwe jest prześledzenie pochodzenia danych oraz procesu prowadzącego do utworzenia Golden Record.

Projekt obejmował analizę wymagań, zaprojektowanie architektury warstwowej, implementację modułów przetwarzania, przygotowanie środowiska uruchomieniowego oraz testowanie rozwiązania. Szczególny nacisk położono na centralną część procesu: przejście od danych heterogenicznych do ujednoliconych, zwalidowanych i pogrupowanych rekordów osoby lub podmiotu.

## Zakres funkcjonalny wykonanej platformy

Platforma przyjmuje pliki CSV, JSON, XML i XLSX oraz dane pobierane z demonstracyjnego systemu relacyjnego Oracle przez ODBC. Każdy import jest przypisywany do systemu źródłowego i partii importu. Oryginalna zawartość wejścia jest przechowywana w warstwie RAW wraz z nazwą, typem, rozmiarem i skrótem SHA-256.

W kolejnej warstwie dane są parsowane i mapowane do wspólnego modelu `PERSON` albo `PARTY`. Mapowanie uwzględnia różnice pomiędzy nazwami i strukturą pól w poszczególnych źródłach, w tym zagnieżdżone dokumenty JSON i XML. System zachowuje również reprezentację rekordu źródłowego, dzięki czemu przekształcenia można powiązać z danymi wejściowymi.

Preprocessing przygotowuje dane do dalszego wykorzystania przez normalizację tekstu, dat, wartości logicznych, numerów telefonów, adresów e-mail, identyfikatorów i elementów adresu. Następnie wykonywane są reguły walidacyjne właściwe dla osób i podmiotów. Obejmują one między innymi kontrolę polskich identyfikatorów, zależności pomiędzy numerem PESEL a datą urodzenia i płcią, poprawność nazw, zakresy dat oraz składnię adresu e-mail. Dla danych adresowych wykorzystywane są pliki referencyjne TERYT.

Po przygotowaniu i walidacji danych uruchamiany jest matching. Pierwszy etap wykorzystuje algorytm Levenshteina i zestaw reguł oceniających zgodność identyfikatorów oraz pozostałych atrybutów. Drugi etap ponownie ocenia kandydatów za pomocą algorytmu Jaro-Winklera. Wyniki są klasyfikowane według zdefiniowanych progów i mogą prowadzić do automatycznego połączenia albo oznaczenia przypadku do weryfikacji.

Rekordy zakwalifikowane do automatycznego połączenia są grupowane. Na podstawie grup budowane są wymiary osób, podmiotów i adresów oraz powiązane identyfikatory i relacje. Wartości Golden Record są wybierane przez reguły survivorship. System preferuje dane, które przeszły walidację, a następnie uwzględnia priorytet źródła określony osobno dla poszczególnych atrybutów, poziom zaufania i aktualność partii importu.

Cały podstawowy proces może być wykonany przez DAG Apache Airflow. Airflow wywołuje odpowiednie operacje aplikacji FastAPI w kolejności od importu RAW do budowy Golden Record. Parametry DAG pozwalają wybrać źródło plikowe lub relacyjne, typ encji oraz progi wykorzystywane podczas matchingu.

## Audytowalność procesu

Audytowalność została potraktowana jako wymaganie przekrojowe. Informacje o przetwarzaniu są przechowywane w kilku powiązanych obszarach modelu danych. `SourceSystem` identyfikuje źródło oraz jego poziom zaufania, `ImportBatch` opisuje pojedynczy import, a `ProcessLog` rejestruje kolejne etapy, ich statusy, liczniki rekordów i błędy.

Wyniki walidacji są zapisywane osobno dla każdej wykonanej reguły. Kandydaci matchingu zawierają wynik podobieństwa, decyzję, silne pola zgodne i pola konfliktowe. Grupy encji wskazują rekordy preprocessingowe użyte do budowy Golden Record.

Dla wartości zapisanych w warstwie GOLD utrzymywane jest lineage. Obejmuje ono system i rekord źródłowy, partię importu, zastosowaną regułę wyboru, poziom zaufania, ocenę jakości oraz status walidacji. Gdy istniejąca osoba lub podmiot zostaje zaktualizowany, zmienione atrybuty są zapisywane w `EntityChangeLog` wraz ze starą i nową wartością oraz czasem zmiany.

Mechanizm pozwala zatem ustalić, na podstawie jakich danych powstał aktualny Golden Record i jak później zmieniały się jego podstawowe atrybuty. Lineage przedstawia pochodzenie wartości aktualnie zapisanych w warstwie GOLD, natomiast `EntityChangeLog` rejestruje kolejne zmiany wartości. Razem mechanizmy te zapewniają audytowalność sposobu utworzenia i aktualizowania Golden Record.

## Zakres techniczny

Backend został wykonany w Pythonie z użyciem FastAPI i SQLAlchemy. Microsoft SQL Server przechowuje dane procesowe, stagingowe i wynikowe. Oracle pełni rolę demonstracyjnego źródła relacyjnego, a Apache Airflow orkiestruje pipeline. W repozytorium znajdują się również frontend React, konfiguracja Neo4j, środowisko Docker Compose oraz manifesty przeznaczone do wdrożenia na OpenShift. Neo4j nie został wykorzystany w głównym procesie goldenizacji ani zweryfikowany jako repozytorium relacji wynikowych. Manifesty OpenShift nie zostały przetestowane na docelowym klastrze, dlatego stanowią przygotowaną podstawę wdrożenia, a nie potwierdzone środowisko uruchomieniowe systemu.

Środowisko lokalne obejmuje usługi API, frontend, Airflow, Microsoft SQL Server, Oracle i Neo4j. Bazy posiadają trwałe wolumeny, a kod aplikacji oraz DAG są montowane do odpowiednich kontenerów. FastAPI automatycznie udostępnia dokumentację OpenAPI i interfejs Swagger.

W pierwotnym opisie technicznym zakładano przechowywanie danych RAW z użyciem SQL Server FILESTREAM. W wykonanym środowisku SQL Server działa w kontenerze Linux, dlatego zawartość wejściowa jest przechowywana w kolumnie `VARBINARY(MAX)`, mapowanej przez SQLAlchemy jako `LargeBinary`. Zachowuje to podstawowe wymaganie przechowywania niezmodyfikowanej treści binarnej, przy czym nie zapewnia strumieniowego dostępu charakterystycznego dla FILESTREAM.

## Elementy poza wykonanym zakresem

Wykonana wersja nie realizuje wszystkich funkcji opisanych w pierwotnej koncepcji platformy. Mechanizm integracji nie wykorzystuje modelu ML lub DL. Matching jest oparty na jawnych regułach, wagach, progach i deterministycznych algorytmach podobieństwa tekstowego.

Warstwy `analytics` i `serving` posiadają strukturę modułów i endpointy statusowe, lecz nie zawierają kompletnej logiki raportowej ani konsumenckich widoków Golden Record. Nie wykonano REST Out z wyszukiwaniem profili i mechanizmem PUSH lub webhooków. Frontend React pełni funkcję technicznego demonstratora połączenia z API i nie prezentuje profilu osoby lub podmiotu.

Neo4j został uwzględniony w konfiguracji środowiska, a w repozytorium znajduje się demonstracyjny zapis dokumentów do bazy grafowej. Rozwiązanie to nie zostało jednak przetestowane jako część głównego procesu goldenizacji ani wykorzystane do budowy grafowej reprezentacji relacji wynikowych. Nie zaimplementowano również konektorów wejściowych dla strumieni danych oraz zewnętrznych usług REST lub SOAP.

Przypadki sklasyfikowane jako `REVIEW` są zapisywane przez mechanizm matchingu, ale nie istnieje osobny interfejs operatora umożliwiający ręczne zatwierdzanie i odrzucanie połączeń. API nie posiada też mechanizmu uwierzytelniania i autoryzacji. Ograniczenia te są uwzględnione w ocenie realizacji wymagań i nie są przedstawiane jako funkcje wykonane.

## Odniesienie do implementacji

Poszczególne części zakresu są realizowane w następujących modułach:

| Obszar | Główna lokalizacja |
|---|---|
| Pobieranie i RAW | `app/layers/ingestion` |
| Staging i mapowanie | `app/layers/staging_validation` |
| Preprocessing | `app/layers/preprocessing` |
| Walidacja i TERYT | `app/layers/validation` |
| Matching, grupowanie i Golden Record | `app/layers/integration_golden` |
| Orkiestracja | `airflow/dags/goldenizacja_pipeline.py` |
| Model SQL Server | `scripts/init_proposed_mssql_schema.sql` |
| Źródło demonstracyjne Oracle | `scripts/init_oracle_insurance_core.sql` |
| Środowisko lokalne | `docker-compose.yml` |
| Zasoby OpenShift | `openshift/` |
| Frontend | `frontend/src/App.jsx` |

Najważniejsze zachowania procesu są sprawdzane przez testy znajdujące się w katalogu `tests`. Obejmują one import relacyjny, mapowanie stagingowe, preprocessing, walidację, jakość danych syntetycznych, matching, grupowanie, budowę wymiarów GOLD, lineage i zapis odrzuconych grup.
