# Pobieranie i składowanie danych RAW

Warstwa RAW stanowi pierwszy trwały etap przetwarzania danych. Jej zadaniem jest przyjęcie danych ze źródła, wykonanie podstawowej kontroli technicznej oraz zachowanie zawartości, na której będą pracowały kolejne warstwy. Dane nie są na tym etapie mapowane do modelu osoby ani podmiotu, normalizowane lub oceniane pod względem jakości biznesowej.

Platforma obsługuje dwa sposoby pozyskania danych:

- przesłanie pliku do API,
- wykonanie przygotowanego zapytania do demonstracyjnego źródła relacyjnego Oracle.

Niezależnie od sposobu pozyskania wynikiem jest rekord `raw.RawFile` powiązany z systemem źródłowym, partią importu i logiem `RAW_LOAD`. Warstwa sprawdza wejście, oblicza SHA-256 i zachowuje zawartość. Mapowanie do modeli `PERSON` i `PARTY`, normalizacja oraz walidacja odbywają się później.

## Interfejs API

| Metoda i endpoint | Przeznaczenie |
|---|---|
| `GET /layers/ingestion/relational-queries` | pobranie listy udostępnionych importów relacyjnych |
| `POST /layers/ingestion/raw-load` | przesłanie pliku do warstwy RAW |
| `POST /layers/ingestion/relational-load` | wykonanie przygotowanego importu z Oracle |

Oba endpointy importowe zwracają `RawLoadResponse`.

| Pole | Znaczenie |
|---|---|
| `import_batch_id`, `raw_file_id` | identyfikatory partii i materiału RAW |
| `file_name`, `file_type`, `file_size` | podstawowe metadane zapisanej zawartości |
| `file_hash` | skrót SHA-256 |
| `records_in` | wstępny licznik rekordów |
| `import_status` | status partii, po sukcesie `RAW_LOADED` |

`raw_file_id` jest podstawowym identyfikatorem przekazywanym do stagingu i dalszych etapów.

## Import plików

Endpoint przyjmuje plik, `source_system_code` oraz opcjonalne `created_by`. `UploadFile` jest odczytywany do postaci bajtowej i przekazywany do `import_raw_file()`.

### Obsługiwane formaty

Dozwolone rozszerzenia są określone w stałej `SUPPORTED_FILE_TYPES`.

| Format | Kontrola wykonywana podczas RAW load | Sposób ustalenia `records_in` |
|---|---|---|
| CSV | odczyt jako UTF-8 z opcjonalnym BOM | liczba wierszy pomniejszona o wiersz nagłówka |
| JSON | dekodowanie UTF-8 i sprawdzenie, czy korzeniem jest obiekt albo lista | `1` dla obiektu albo długość listy |
| XML | parsowanie dokumentu XML | liczba elementów bezpośrednio pod elementem głównym |
| XLSX | otwarcie skoroszytu i sprawdzenie obecności niepustych wierszy | liczba niepustych wierszy pomniejszona o nagłówek |

Rozszerzenie jest sprawdzane przed utworzeniem partii, a `File_Type` zapisywany wielkimi literami. Kontrola ma charakter techniczny: nie sprawdza wymaganych kolumn ani zgodności z modelem kanonicznym. Plik zapisany w RAW może więc zostać później odrzucony w stagingu.

`records_in` jest licznikiem technicznym. Dla CSV i XLSX zakłada jeden wiersz nagłówka, dla XML liczy elementy pierwszego poziomu, a dla JSON elementy listy lub pojedynczy obiekt. Nie potwierdza, że rekordy zostaną poprawnie zmapowane.

### Sprawdzanie systemu źródłowego

`source_system_code` jest normalizowany do wielkich liter i musi występować w `SUPPORTED_SOURCE_SYSTEMS`. Pełny katalog źródeł opisano w rozdziale 6. Brakujący wpis `meta.SourceSystem` jest tworzony automatycznie, z pustym poziomem zaufania.

## Import ze źródła relacyjnego

Endpoint przyjmuje `source_system_code`, `query_name`, opcjonalny `entity_type` i `created_by`. Nie pozwala przekazać dowolnego SQL: zapytanie musi występować w `RELATIONAL_QUERY_DEFINITIONS` i być zgodne z systemem źródłowym oraz typem encji.

### Definicje zapytań

Endpoint `GET /relational-queries` zwraca publiczną nazwę `insurance_core_export` z typem `AUTO`. Podczas uruchomienia jest ona rozwijana według `entity_type` do jednej z dwóch definicji wewnętrznych:

| Nazwa wewnętrzna | Typ encji | Nazwa snapshotu |
|---|---|---|
| `insurance_core_party_export` | `PARTY` | `insurance_core_party_export.json` |
| `insurance_core_person_export` | `PERSON` | `insurance_core_person_export.json` |

Ogólna nazwa wymaga podania `PERSON` albo `PARTY`. W DAG-u Airflow przy automatycznym wyborze obu typów wykonywane są dwa osobne wywołania, dlatego powstają dwie partie i dwa materiały RAW.

Definicja jest odrzucana, jeżeli nazwa jest nieznana, brakuje wymaganego typu encji albo zapytanie nie odpowiada wskazanemu typowi lub źródłu.

Wybór z zamkniętej listy zapobiega wykonaniu przez endpoint dowolnego SQL przekazanego przez klienta. Nie zastępuje jednak ograniczeń uprawnień konta Oracle, które powinno mieć wyłącznie dostęp potrzebny do odczytu danych objętych eksportem.

### Połączenie z Oracle

Połączenie korzysta z `ORACLE_ODBC_CONNECTION_STRING` i PyODBC albo, gdy ciągu nie podano, ze sterownika `oracledb` w trybie thin. Nazwy kolumn pochodzą z `cursor.description`, a wiersze są zamieniane na słowniki.

Eksport `PARTY` wykonuje zapytanie główne oraz zapytania pobierające role osób i relacje między podmiotami. Dane dodatkowe są dołączane do odpowiedniego rekordu klienta w polach `RELATED_PERSONS_JSON` i `RELATED_PARTIES_JSON`.

Eksport `PERSON` zwraca osoby z przypisań agentów oraz osoby zapisane jako klienci systemu demonstracyjnego. Wyniki są odczytywane do pamięci, a połączenie jest zamykane również po wystąpieniu błędu.

### Utworzenie snapshotu

Wynik importu relacyjnego jest serializowany do dokumentu JSON:

```text
lista rekordów Oracle
  -> serializacja JSON w UTF-8
  -> obliczenie SHA-256
  -> zapis jako raw.RawFile
```

Serializacja zachowuje znaki narodowe, a wartości nieobsługiwane bezpośrednio przez JSON, na przykład daty, konwertuje do tekstu. Snapshot jest dalej przetwarzany jak plik JSON, dzięki czemu staging pracuje na stanie danych pobranym dla konkretnej partii.

## Wspólny zapis materiału RAW

Import plikowy i relacyjny kończą się wywołaniem `persist_raw_content()`, które tworzy metadane, oblicza skrót i zapisuje log.

### Kolejność operacji

1. Repozytorium pobiera albo tworzy `meta.SourceSystem`.
2. Tworzona jest partia ze statusem `NEW`.
3. Status partii zmienia się na `PROCESSING`.
4. Powstaje log `RAW_LOAD` ze statusem `STARTED`.
5. Dla pełnej zawartości obliczany jest SHA-256.
6. Powstaje rekord `raw.RawFile`.
7. Log otrzymuje status `SUCCESS`, `RawFile_ID` oraz liczniki.
8. Partia otrzymuje status `RAW_LOADED` i czas zakończenia.

Partia jest tworzona przed próbą zapisu materiału RAW. Dzięki temu błąd zapisu może zostać przypisany do konkretnego `ImportBatch_ID`.

## Struktura RawFile

`raw.RawFile` przechowuje zawartość wejściową oraz metadane potrzebne do jej identyfikacji.

| Kolumna | Typ fizyczny | Znaczenie |
|---|---|---|
| `RawFile_ID` | `BIGINT IDENTITY` | identyfikator materiału RAW |
| `ImportBatch_ID` | `BIGINT` | partia importu |
| `File_Name` | `NVARCHAR(260)` | nazwa pliku albo snapshotu |
| `File_Type` | `NVARCHAR(30)` | format zawartości |
| `File_Size` | `BIGINT` | liczba bajtów |
| `File_Hash` | `CHAR(64)` | SHA-256 zapisany szesnastkowo |
| `File_Content` | `VARBINARY(MAX)` | zawartość wejściowa |
| `Created_At` | `DATETIME2(0)` | czas zapisu |

`ImportBatch_ID` jest kluczem obcym do `meta.ImportBatch` i posiada indeks. Rozmiar nie może być ujemny. `File_Hash` ma ograniczenie unikalności.

Model SQLAlchemy odwzorowuje `File_Content` typem `LargeBinary`. Chociaż definicja fizyczna dopuszcza wartość `NULL`, ścieżki importu wymagają niepustej zawartości i przekazują do repozytorium wartość typu `bytes`.

Krok jest rejestrowany w `meta.ProcessLog`. Po sukcesie log zawiera `RawFile_ID`, status `SUCCESS` i wstępne liczniki rekordów; po błędzie status `FAILED` i komunikat. Szczegółowy model metadanych i statusów opisano w rozdziałach 9 i 10.

## Kontrola duplikatów

Skrót jest obliczany dla pełnej zawartości bajtowej:

```text
SHA-256(File_Content) -> 64 znaki szesnastkowe
```

Ograniczenie `UQ_RawFile_File_Hash` zapewnia unikalność w całej tabeli, niezależnie od nazwy, źródła, typu encji i daty. Identyczne bajty przesłane pod inną nazwą również są duplikatem. Zasada obejmuje także snapshoty relacyjne.

Porównanie jest wykonywane na poziomie bajtów, a nie znaczenia danych. Dwa dokumenty JSON zawierające te same wartości, ale różniące się kolejnością pól lub formatowaniem, otrzymają inne skróty i mogą zostać zapisane osobno. Analogicznie zmiana kodowania, separatorów końca linii lub BOM zmienia SHA-256 pliku.

W przypadku snapshotu Oracle stabilność skrótu zależy również od kolejności rekordów zwróconych przez zapytanie i sposobu serializacji wartości. Mechanizm wykrywa zatem identyczny obraz wejścia, a nie biznesową równoważność dwóch zbiorów.

Konflikt ograniczenia unikalności jest przechwytywany jako `IntegrityError`. Serwis wycofuje bieżącą transakcję, kończy log i partię statusem `FAILED`, zapisuje komunikat `File with this hash already exists.` i zgłasza kontrolowany błąd zawartości. Endpoint zwraca wtedy HTTP 400 bez identyfikatora istniejącego materiału RAW.

Globalny zakres unikalności oznacza, że system nie przechowuje dwóch osobnych rekordów RAW dla identycznej zawartości pochodzącej z różnych deklarowanych źródeł.

## Obsługa błędów

HTTP 400 jest zwracany dla rozpoznanych problemów wejścia i konfiguracji:

- nieobsługiwanego formatu lub kodu źródła;
- pustej zawartości, nieprawidłowego XLSX albo nieobsługiwanej struktury korzenia JSON;
- błędnej nazwy lub kombinacji parametrów zapytania relacyjnego;
- duplikatu zawartości.

Pozostałe wyjątki zwracają HTTP 500 z oznaczeniem etapu. Błąd składni JSON lub XML oraz błąd dekodowania tekstu nie są obecnie zamieniane na `InvalidFileContentError`, dlatego również trafiają do tej kategorii.

Po błędzie, który wystąpił już po utworzeniu partii, serwis próbuje:

- wycofać niezakończoną transakcję;
- zakończyć rozpoczęty log statusem `FAILED`;
- ustawić partię na `FAILED`;
- zapisać treść wyjątku.

Repozytorium zatwierdza osobno utworzenie źródła, partii, logu i materiału RAW. Nie jest to jedna transakcja obejmująca cały krok. Pozwala to zachować metadane błędu, ale diagnostyka powinna uwzględniać zarówno `ImportBatch`, jak i `ProcessLog`.

## Uzasadnienie użycia VARBINARY(MAX)

Pierwotna koncepcja przewidywała SQL Server FILESTREAM. W wykonanej implementacji zastosowano `VARBINARY(MAX)` mapowany jako `LargeBinary`, ponieważ w czasie realizacji możliwe było uruchomienie i zweryfikowanie tego wariantu bez dodatkowej konfiguracji magazynu FILESTREAM, ścieżek systemowych i uprawnień. Decyzja nie wynika z założenia, że środowisko docelowe nie obsługuje FILESTREAM.

Przyjęte rozwiązanie zachowuje pełną zawartość bajtową, umożliwia kontrolę SHA-256 i wiąże materiał z partią oraz logami w SQL Serverze. Nie zapewnia natomiast strumieniowego dostępu ani korzyści FILESTREAM przy obsłudze dużych obiektów.

Aplikacja odczytuje cały plik do pamięci i przekazuje wartość `bytes` do SQLAlchemy. Wariant został zweryfikowany dla danych projektu, ale nie wykonano pomiarów dla bardzo dużych plików ani wielu równoległych importów.

## Bezpieczeństwo i integralność

Parametry połączeń są pobierane z konfiguracji środowiska. Ponieważ `File_Content` może zawierać dane osobowe i biznesowe, dostęp do schematu `raw` i kopii zapasowych powinien być ograniczony. Integralność wspierają klucze obce, unikalny hash, kontrola rozmiaru i logi procesu. SHA-256 wykrywa identyczną zawartość, ale nie potwierdza jej autentyczności.

## Ograniczenia

W obecnej implementacji:

- cały przesyłany plik jest odczytywany do pamięci przed zapisem;
- snapshot relacyjny również jest tworzony w pamięci jako pełna lista i dokument JSON;
- nie skonfigurowano limitu rozmiaru pliku na poziomie endpointu;
- nie zastosowano skanowania antywirusowego przesyłanych plików;
- unikalność skrótu obowiązuje globalnie, a nie w ramach źródła;
- nie ma endpointu zwracającego istniejący `RawFile_ID` po wykryciu duplikatu;
- lista importów relacyjnych jest zdefiniowana w kodzie, a nie konfigurowana administracyjnie;
- `records_in` jest licznikiem technicznym i nie zastępuje wyniku stagingu;
- błędy składni JSON i XML mogą zostać sklasyfikowane jako HTTP 500.

## Realizacja w kodzie

| Obszar | Plik lub element |
|---|---|
| endpointy importu | `app/layers/ingestion/api.py` |
| kontrola i zapis plików | `_get_file_type()`, `_validate_and_count_records()`, `import_raw_file()`, `persist_raw_content()` |
| import Oracle | `RELATIONAL_QUERY_DEFINITIONS`, `resolve_relational_query_definition()`, `extract_relational_records()` |
| operacje bazodanowe | `app/layers/ingestion/repository.py` |
| modele ORM | `app/layers/ingestion/models.py` |
| fizyczny schemat SQL Server | `scripts/init_proposed_mssql_schema.sql` |

`tests/test_relational_ingestion.py` sprawdza pobieranie danych Oracle, dołączanie relacji, serializację snapshotu oraz wybór wariantu `PERSON` lub `PARTY`. Testy nie obejmują pełnej integracji endpointu plikowego z rzeczywistym SQL Serverem ani wydajności `VARBINARY(MAX)`.
