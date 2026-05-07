# Status implementacji warstw RAW i staging

Dokument opisuje aktualny stan implementacji funkcji związanych z pobieraniem danych, zapisem RAW, stagingiem, walidacją oraz przygotowaniem danych pod dalszą goldenizację

## Podsumowanie

Aktualnie zaimplementowane są dwie główne części procesu:

- warstwa ingestion, czyli przyjęcie pliku przez API i zapis oryginalnej treści do RAW
- warstwa staging_validation, czyli mapowanie danych źródłowych do wspólnego modelu stagingowego, cleaning, splitting adresów, unifikacja typów i podstawowa kontrola duplikatów ładowania

Warstwy `integration_golden`, `analytics` i `serving` istnieją jako struktura katalogów i endpointy statusowe, ale ich pełna logika biznesowa nie jest jeszcze zaimplementowana

## Ingestion i RAW

### Obsługiwane wejścia plikowe

Endpoint:

```text
POST /layers/ingestion/raw-load
```

Obsługiwane formaty:

- `CSV`
- `JSON`
- `XML`
- `XLSX`

Upload pliku jest czytany jako bajty i zapisywany w tabeli RAW bez czyszczenia ani modyfikowania treści. Dzięki temu RAW zachowuje oryginalny plik wejściowy, a dalsze warstwy mogą go ponownie odczytać z bazy

Tabela RAW:

```text
raw.RawFile
```

Najważniejsze pola:

- `RawFile_ID`
- `ImportBatch_ID`
- `File_Name`
- `File_Type`
- `File_Size`
- `File_Hash`
- `File_Content`
- `Created_At`

`File_Content` jest zapisane jako `VARBINARY(MAX)` po stronie SQL Servera i jako `LargeBinary` po stronie SQLAlchemy. To zastępuje `FILESTREAM` w lokalnym środowisku kontenerowym

### Zachowanie oryginalnej treści

Zrobione:

- zapis bajtów pliku do RAW
- brak cleaningu przed zapisem RAW
- hash SHA-256 liczony z oryginalnej treści
- blokada duplikatu identycznego pliku przez unikalny `File_Hash`

Nie jest zrobione:

- nie ma `SqlFileStream`
- nie ma kopiowania bajt po bajcie
- plik jest czytany w całości przez FastAPI jako `await file.read()`

### API jako źródło danych

Nie jest jeszcze zrobione jako osobny mechanizm

Obecnie system przyjmuje pliki przez upload. Nie ma jeszcze klienta REST/SOAP, który pobiera odpowiedź z zewnętrznego API i zapisuje całe body odpowiedzi jako dokument RAW `.json` albo `.xml`

## Rejestracja i audytowalność

### Import batch

Każdy import dostaje wpis w:

```text
meta.ImportBatch
```

Najważniejsze pola:

- `ImportBatch_ID`
- `SourceSystem_ID`
- `Import_Status`
- `Import_Start_At`
- `Import_End_At`
- `Created_By`
- `Error_Message`

`ImportBatch_ID` pełni rolę technicznego identyfikatora przebiegu importu. W dokumentacji wymagań można go traktować jako odpowiednik `Load_ID`

### Process log

Każdy krok procesu jest logowany w:

```text
meta.ProcessLog
```

Najważniejsze pola:

- `ProcessLog_ID`
- `ImportBatch_ID`
- `RawFile_ID`
- `Staging_ID`
- `Step_Name`
- `Step_Status`
- `Started_At`
- `Ended_At`
- `Records_In`
- `Records_Out`
- `Error_Message`

Logowanie działa dla kroku RAW load oraz staging load

### Powiązanie RAW ze stagingiem

Tabele stagingowe mają pola:

- `ImportBatch_ID`
- `RawFile_ID`
- `Source_Record_ID`

Dzięki temu rekord stagingowy można powiązać z konkretnym importem, plikiem RAW i rekordem źródłowym

## Staging i walidacja

Endpoint:

```text
POST /layers/staging_validation/staging-load
```

Parametry:

- `raw_file_id`
- `entity_type`, czyli `PERSON` albo `PARTY`

Staging odczytuje plik z `raw.RawFile.File_Content`, parsuje go w Pythonie, mapuje kolumny przez `meta.ColumnMapping`, a następnie zapisuje wynik do:

- `stg.Person_Staging`
- `stg.Party_Staging`

### Transformacja danych

Zrobione funkcjonalnie:

- parsowanie `CSV`
- parsowanie `JSON`
- parsowanie `XML`
- parsowanie `XLSX`
- mapowanie kolumn źródłowych do wspólnego modelu kanonicznego
- obsługa kolumn płaskich oraz ścieżek zagnieżdżonych typu `firma.wlasciciel.imie`
- zapis rekordów do tabel stagingowych

Nie jest zrobione zgodnie z opisem technologicznym:

- nie ma procedur składowanych T-SQL do transformacji RAW na staging
- nie ma `OPENJSON`
- nie ma `.nodes()`
- dekompozycja dokumentów jest realizowana w Pythonie, nie w T-SQL

## Cleaning

Cleaning jest zaimplementowany centralnie przed zapisem do stagingu

Zakres:

- usuwanie białych znaków na początku i końcu tekstu
- usuwanie znaków niedrukowalnych
- cleaning działa rekurencyjnie dla słowników i list
- cleaning działa dla `PERSON` i `PARTY`

Przykład:

```text
"\x00  Dirty Company\t" -> "Dirty Company"
"\t SRC-1\x00 " -> "SRC-1"
```

Cleaning jest wykonywany po odczycie RAW i przed mapowaniem do stagingu oraz dodatkowo w `build_staging_record`, żeby bezpośrednie użycie funkcji nie ominęło sanityzacji

## Splitting adresów

Splitting adresów jest zaimplementowany regexami w warstwie stagingu

Obsługiwane pola wejściowe:

- `Street`
- `Postal_City`
- `City`

Obsługiwane przykłady:

```text
ulica Krotka 122/64 -> Street=Krotka, Building_Number=122, Apartment_Number=64
ul. Kosciuszki 174/39 -> Street=Kosciuszki, Building_Number=174, Apartment_Number=39
Baltycka 136/11, 66-157 Bydgoszcz -> Street=Baltycka, Building_Number=136, Apartment_Number=11, Postal_Code=66-157, City=Bydgoszcz
82-801 Krakow, ul Baltycka 152 -> Street=Baltycka, Building_Number=152, Postal_Code=82-801, City=Krakow
Rzeszow, ul Lakowa 38 m. 43 -> Street=Lakowa, Building_Number=38, Apartment_Number=43, City=Rzeszow
54-172 Rzeszow -> Postal_Code=54-172, City=Rzeszow, Street=NULL
```

Splitting działa dla `PERSON` i `PARTY`

## Unifikacja typów

### Daty

Zaimplementowana jest konwersja dat do typu `date` przed zapisem do stagingu

Dla `PERSON`:

- `Birth_Date`

Dla `PARTY`:

- `Establishment_Date`
- `Registration_Date`
- `Deregistration_Date`
- `Decision_Date`
- `Last_Update_Date`
- `Next_Renewal_Date`
- `Direct_Parent_Relationship_Start_Date`
- `Direct_Parent_Relationship_End_Date`
- `Ultimate_Parent_Relationship_Start_Date`
- `Ultimate_Parent_Relationship_End_Date`

Obsługiwane formaty wejściowe:

- `YYYY-MM-DD`
- ISO datetime, np. `2024-01-10T00:00:00Z`
- `YYYY/MM/DD`
- `DD.MM.YYYY`
- `DD-MM-YYYY`
- `DD/MM/YYYY`

W SQL Serverze kolumny dat są typu `DATE`, więc po stronie bazy wartości są ujednolicone do formatu daty

### Wartości logiczne

Zaimplementowane dla pola:

- `Has_Virtual_Accounts`
- `Sex`

Mapowanie:

- `1`, `true`, `t`, `yes`, `y`, `tak`, `prawda` -> `1`
- `0`, `false`, `f`, `no`, `n`, `nie`, `falsz`, `fałsz` -> `0`
- brak albo wartość nierozpoznana -> `NULL`

Mapowanie płci:

- `1`, `K`, `kobieta`, `female`, `f` -> `1`
- `0`, `M`, `mezczyzna`, `mężczyzna`, `male` -> `0`
- brak albo wartość nierozpoznana -> `NULL`

Po stronie modelu SQLAlchemy pole jest typu `Boolean`, a po stronie SQL Servera skrypt ustawia kolumnę jako `BIT`

## Mapowanie źródeł

System ma mapowania kolumn dla wielu źródeł w `meta.ColumnMapping`, zasilane przez:

```text
scripts/init_proposed_mssql_schema.sql
```

Obsługiwane źródła obejmują:

- `CEIDG`
- `KRS`
- `REGON`
- `VAT`
- `PESEL`
- `GLEIF`
- `GLEIF_L1`
- `GLEIF_L2`
- `KNF_AGENT`
- `KNF_PRACOWNIK_AGENTA`
- `KNF_FIRMY_INWESTYCYJNE`
- `KNF_PIENIADZ_ELEKTRONICZNY`

Mapowania obejmują dane identyfikacyjne, adresowe, rejestrowe, statusowe, relacyjne oraz wybrane pola kontaktowe

## Identyfikatory i JSON

### Identyfikatory podmiotów

Dla `PARTY` identyfikatory są składane do pola:

```text
Identifiers_JSON
```

Obsługiwane typy identyfikatorów:

- `NIP`
- `REGON`
- `KRS`
- `LEI`
- `UKNF`

### Konta bankowe VAT

Pole `Bank_Accounts_JSON` jest normalizowane do poprawnego JSON array

Przykład:

```text
111, 222 -> ["111", "222"]
```

### Relacje KRS

Szerokie kolumny KRS są rozpoznawane regexami i składane do JSON:

- `Related_Persons_JSON`
- `Related_Parties_JSON`

Obsługiwane role osób:

- `CzlonekZarzadu` -> `BOARD_MEMBER`
- `Prokurent` -> `PROXY`
- `WspolnikOsoba` -> `PERSON_SHAREHOLDER`
- `Likwidator` -> `LIQUIDATOR`
- `CzlonekRadyNadzorczej` -> `SUPERVISORY_BOARD_MEMBER`

Obsługiwane relacje podmiotów:

- `WspolnikPodmiot` -> `PARTY_SHAREHOLDER`

Dzięki temu szerokie kolumny KRS nie trafiają już jako fałszywe `unrecognized_columns`

## Kontrole jakości i walidacja procesu

### Raport mapowania

Odpowiedź ze staging-load zwraca:

- `records_in`
- `records_out`
- `missing_columns`
- `unrecognized_columns`
- status batcha
- status procesu

### Blokada podwójnego staging-load

Zaimplementowana jest blokada ponownego załadowania tego samego `raw_file_id` do tego samego typu stagingu

Jeśli rekordy już istnieją, API zwraca kontrolowany błąd zamiast dublować dane

### Blokada identycznego RAW

RAW load blokuje drugi upload identycznego pliku przez unikalny `File_Hash`

## Testy

Główne testy są w:

```text
tests/test_staging_mapper.py
```

Aktualnie testy obejmują:

- mapowanie kolumn do modelu kanonicznego
- obsługę nazw kolumn bez względu na wielkość liter
- mapowanie ścieżek zagnieżdżonych
- składanie `Identifiers_JSON`
- daty GLEIF i inne daty party
- boolean `Has_Virtual_Accounts`
- cleaning tekstu
- splitting adresów dla `PERSON` i `PARTY`
- pełne adresy w `Street`, `Postal_City` i `City`
- XML z atrybutem `name`
- blokadę podwójnego staging-load

Ostatnio uruchamiane komendy weryfikacyjne:

```bash
python3 -m unittest discover -s tests -p test_staging_mapper.py -v
python3 -m py_compile $(find app -name '*.py' -print)
```

## Najważniejsze braki

Do pełnej zgodności z opisem wymagań brakuje:

- `SqlFileStream` i strumieniowego kopiowania bajt po bajcie
- pobierania danych bezpośrednio z REST/SOAP API
- zapisu całego response payload z API jako RAW `.json` lub `.xml`
- transformacji stagingowej przez procedury T-SQL, `OPENJSON` i `.nodes()`
- pełnej warstwy `integration_golden`
- pełnej warstwy `analytics`
- pełnej warstwy `serving`

## Jak przetestować ręcznie

1. Załaduj plik do RAW:

```text
POST http://localhost:8000/layers/ingestion/raw-load
```

Form-data:

- `file`
- `source_system_code`
- `created_by`

2. Weź `raw_file_id` z odpowiedzi

3. Załaduj RAW do stagingu:

```text
POST http://localhost:8000/layers/staging_validation/staging-load
```

Form-data:

- `raw_file_id`
- `entity_type`, czyli `PERSON` albo `PARTY`

4. Sprawdź w DBeaver:

```text
goldenizacja -> Schemas -> raw -> RawFile
goldenizacja -> Schemas -> stg -> Person_Staging
goldenizacja -> Schemas -> stg -> Party_Staging
goldenizacja -> Schemas -> meta -> ImportBatch
goldenizacja -> Schemas -> meta -> ProcessLog
```
