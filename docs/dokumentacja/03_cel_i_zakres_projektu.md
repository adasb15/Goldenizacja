# 3. Cel i zakres projektu

## 3.1. Cel projektu

Celem projektu było wykonanie autonomicznej platformy integracji danych podstawowych osób i podmiotów. Rozwiązanie miało umożliwiać przyjmowanie danych z różnych źródeł, zachowanie ich oryginalnej postaci, kontrolę jakości, integrację rekordów oraz udostępnienie spójnej reprezentacji danych. Założenia przekazane przez opiekuna wskazywały na potrzebę budowy rozwiązania odpowiadającego koncepcji centralnego repozytorium osób i podmiotów, w którym możliwe jest prześledzenie pochodzenia danych oraz procesu prowadzącego do utworzenia Golden Record.

Projekt obejmował analizę wymagań, zaprojektowanie architektury warstwowej, implementację modułów przetwarzania, przygotowanie środowiska uruchomieniowego oraz testowanie rozwiązania. Szczególny nacisk położono na centralną część procesu: przejście od danych heterogenicznych do ujednoliconych, zwalidowanych i pogrupowanych rekordów osoby lub podmiotu.

## 3.2. Zakres funkcjonalny wykonanej platformy

Platforma przyjmuje pliki CSV, JSON, XML i XLSX oraz dane z demonstracyjnego źródła Oracle. Każdy import jest przypisywany do systemu źródłowego i partii, a zawartość wejściowa jest zachowywana w warstwie RAW wraz z metadanymi i skrótem SHA-256.

Dane są następnie mapowane do modeli `PERSON` albo `PARTY`, normalizowane i poddawane regułom jakości, w tym kontroli identyfikatorów i adresów z użyciem TERYT. Po walidacji system wykonuje dwuetapowy matching, grupuje rekordy zakwalifikowane do połączenia oraz tworzy lub aktualizuje osoby, podmioty, adresy i identyfikatory w warstwie GOLD.

Wartości Golden Record są wybierane według reguł survivorship uwzględniających jakość, priorytet i poziom zaufania źródła oraz aktualność partii. Pełny proces może zostać uruchomiony przez DAG Apache Airflow, który wywołuje operacje aplikacji FastAPI od importu RAW do materializacji danych GOLD.

Warstwa `serving` udostępnia przez REST listy i szczegóły Golden Record, wyszukiwanie osób po PESEL oraz podmiotów po identyfikatorach lub nazwie. Pozwala także odczytywać lineage, historię zmian, wyniki walidacji, kandydatów matchingu i liczniki etapów procesu.

## 3.3. Audytowalność procesu

System rejestruje źródła, partie importu, przebieg etapów, wyniki walidacji, kandydatów matchingu i grupy encji. Dla aktualnych wartości GOLD utrzymywane jest lineage wskazujące ich źródło, partię oraz regułę wyboru.

Zmiany atrybutów istniejących osób i podmiotów są zapisywane w `EntityChangeLog` wraz ze starą i nową wartością. Pozwala to ustalić, na podstawie jakich danych powstał aktualny Golden Record oraz jak zmieniał się w kolejnych importach.

## 3.4. Zakres techniczny

Backend wykonano w Pythonie z użyciem FastAPI i SQLAlchemy. Microsoft SQL Server przechowuje dane procesowe i wynikowe, Oracle jest demonstracyjnym źródłem relacyjnym, a Apache Airflow orkiestruje pipeline. Środowisko lokalne jest uruchamiane przez Docker Compose i obejmuje również frontend React oraz demonstracyjną konfigurację Neo4j.

Repozytorium zawiera manifesty OpenShift, ale nie zostały one zweryfikowane na docelowym klastrze. Neo4j również nie jest częścią przetestowanego procesu goldenizacji. Elementy te należy traktować jako przygotowaną konfigurację, a nie potwierdzoną ścieżkę działania systemu.

Pierwotna koncepcja przewidywała SQL Server FILESTREAM. W wykonanej wersji zastosowano `VARBINARY(MAX)` mapowany jako `LargeBinary`. W ograniczonym czasie projektu wybrano wariant możliwy do uruchomienia i zweryfikowania bez dodatkowej konfiguracji FILESTREAM. Decyzja nie wynika z założenia, że środowisko docelowe nie obsługuje tego mechanizmu.

## 3.5. Elementy poza wykonanym zakresem

Matching nie wykorzystuje ML ani DL, lecz jawne reguły, wagi, progi i deterministyczne miary podobieństwa. Nie wykonano także konektorów strumieniowych oraz wejść z zewnętrznych usług REST lub SOAP.

Warstwa `analytics` pozostaje szkieletem i nie udostępnia raportów ani metryk. Warstwa `serving` realizuje odczyt danych, ale nie zawiera mechanizmu PUSH ani webhooków. Frontend korzysta już z odczytowych endpointów servingowych dla listy Golden Record, szczegółów osoby i podmiotu, lineage, historii zmian, walidacji oraz matchingu, ale nadal nie obsługuje ręcznych decyzji integracyjnych ani operacji zapisu. Neo4j nie przechowuje relacji wynikowych głównego procesu.

Brakuje również interfejsu operatora do ręcznej obsługi decyzji `REVIEW` oraz uwierzytelniania i autoryzacji API. Szczegółowa ocena realizacji tych elementów znajduje się w macierzy wymagań.

## 3.6. Odniesienie do implementacji

Poszczególne części zakresu są realizowane w następujących modułach:

| Obszar | Główna lokalizacja |
|---|---|
| Pobieranie i RAW | `app/layers/ingestion` |
| Staging i mapowanie | `app/layers/staging_validation` |
| Preprocessing | `app/layers/preprocessing` |
| Walidacja i TERYT | `app/layers/validation` |
| Matching, grupowanie i Golden Record | `app/layers/integration_golden` |
| Udostępnianie danych | `app/layers/serving` |
| Orkiestracja | `airflow/dags/goldenizacja_pipeline.py` |
| Model SQL Server | `scripts/init_proposed_mssql_schema.sql` |
| Źródło demonstracyjne Oracle | `scripts/init_oracle_insurance_core.sql` |
| Środowisko lokalne | `docker-compose.yml` |
| Zasoby OpenShift | `openshift/` |
| Frontend | `frontend/src/App.jsx` |

Testy w katalogu `tests` obejmują główne etapy procesu, reguły integracji, budowę GOLD i audytowalność.
