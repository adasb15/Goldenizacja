# Źródła danych i zakres informacyjny

Platforma została przygotowana do integracji danych o osobach i podmiotach pochodzących z wielu źródeł. W repozytorium znajdują się zestawy plikowe odwzorowujące struktury wybranych rejestrów publicznych i branżowych oraz demonstracyjny system relacyjny Oracle. Dane służą do sprawdzania mapowania, walidacji, matchingu, grupowania i budowy Golden Record.

Wszystkie dane plikowe używane w projekcie są syntetyczne. Nazwy zbiorów i układ kolumn nawiązują do rzeczywistych rejestrów, jednak rekordy nie stanowią kopii danych produkcyjnych ani oficjalnych eksportów. Pozwala to wykonywać testy integracji bez przetwarzania rzeczywistych danych osobowych i biznesowych. Syntetyczny charakter ma również baza Oracle utworzona na potrzeby demonstracji importu relacyjnego.

## Systemy źródłowe

Kod warstwy ingestion rozpoznaje jedenaście systemów źródłowych. Dziesięć z nich odpowiada zestawom plikowym, natomiast `INSURANCE_CORE` jest relacyjnym źródłem demonstracyjnym.

| Kod źródła | Zakres danych | Typ encji | Najważniejsze informacje |
|---|---|---|---|
| `PESEL` | dane osób | `PERSON` | PESEL, imiona, nazwiska, data i miejsce urodzenia, płeć, obywatelstwo, dokumenty tożsamości, adresy i dane kontaktowe |
| `CEIDG` | działalność gospodarcza i właściciel | `PARTY`, `PERSON` | nazwa firmy, NIP, REGON, dane działalności, adresy, kontakt oraz dane właściciela |
| `KRS` | podmioty rejestrowe i ich relacje | `PARTY`, `PERSON` | KRS, NIP, REGON, nazwa, forma prawna, status, adres, osoby reprezentujące, wspólnicy i okresy relacji |
| `REGON` | dane podmiotów | `PARTY` | REGON, NIP, KRS, nazwa, forma prawna, forma własności, adres, PKD i data powstania |
| `VAT` | dane podatników VAT | `PARTY` | nazwa, NIP, REGON, KRS, status VAT, adresy, rachunki bankowe i daty rejestracyjne |
| `GLEIF` | dane podmiotów posiadających LEI | `PARTY` | LEI, nazwa prawna, forma prawna, jurysdykcja, adres, status rejestracji oraz informacje o podmiocie dominującym |
| `KNF_AGENT` | pośrednicy ubezpieczeniowi | `PARTY`, `PERSON` | numer agenta, firma, NIP, KRS, zakład ubezpieczeń, typ agenta, adres oraz dane osoby |
| `KNF_PRACOWNIK_AGENTA` | pracownicy agentów i dane agentów | `PARTY`, `PERSON` | numer pracownika, dane osoby, PESEL, dane agenta, NIP, KRS i okres wpisu |
| `KNF_FIRMY_INWESTYCYJNE` | firmy inwestycyjne i członkowie zarządu | `PARTY`, `PERSON` | nazwa, KRS, NIP, REGON, adres, zakres czynności, decyzja oraz dane członka zarządu |
| `KNF_PIENIADZ_ELEKTRONICZNY` | dostawcy i wydawcy pieniądza elektronicznego | `PARTY` | numer UKNF, nazwa, typ podmiotu, status, daty, KRS, NIP i adres |
| `INSURANCE_CORE` | demonstracyjny system ubezpieczeniowy Oracle | `PARTY`, `PERSON` | dane klientów, identyfikatory, adresy, kontakty, rachunki, umowy, role osób i relacje pomiędzy klientami |

Lista dozwolonych kodów znajduje się w stałej `SUPPORTED_SOURCE_SYSTEMS` w `app/layers/ingestion/service.py`. Kod źródła jest zapisywany w tabeli `meta.SourceSystem` i wiąże późniejsze dane z poziomem zaufania, mapowaniem kolumn oraz regułami survivorship.

## Zbiory plikowe

Katalog `data` zawiera dziesięć logicznych zestawów danych w czterech formatach:

- CSV,
- JSON,
- XML,
- XLSX.

Każdy zestaw zawiera po 200 rekordów w każdym formacie, czyli łącznie 800 rekordów na logiczne źródło. Manifest `data/manifest.json` opisuje liczebność plików. Dla dziesięciu źródeł daje to łącznie 8000 syntetycznych rekordów plikowych, przy czym rekordy w poszczególnych formatach stanowią różne dane, a nie cztery identyczne kopie tego samego zbioru.

Pliki CSV są kodowane w UTF-8 z BOM. W plikach XML nazwy pól są zapisywane w atrybutach `name`, co pozwala bezpiecznie obsługiwać nazwy zawierające spacje i polskie znaki. Pliki XLSX mają prostą strukturę tabelaryczną. Dokumenty JSON mogą zawierać pojedynczy obiekt albo listę obiektów.

Warstwa RAW sprawdza rozszerzenie oraz podstawową poprawność zawartości. Pełne parsowanie następuje dopiero podczas ładowania do stagingu. Wszystkie cztery formaty są ostatecznie przekształcane do listy rekordów słownikowych, dzięki czemu późniejsze mapowanie nie zależy od formatu wejściowego.

Obsługa formatów jest realizowana przez:

- `SUPPORTED_FILE_TYPES` i `import_raw_file()` w `app/layers/ingestion/service.py`,
- `parse_raw_file_records()` w `app/layers/staging_validation/service.py`,
- `parse_xlsx_records()` i `parse_xml_records()` w tym samym module.

## Modele PERSON i PARTY

Źródła są mapowane do jednego albo dwóch typów encji. `PERSON` reprezentuje osobę fizyczną, natomiast `PARTY` reprezentuje podmiot, organizację albo działalność gospodarczą.

Model `PERSON` obejmuje w szczególności:

- PESEL,
- numer dowodu osobistego i paszportu,
- pierwsze i drugie imię,
- nazwisko i nazwisko rodowe,
- datę i miejsce urodzenia,
- płeć i obywatelstwo,
- telefon i adres e-mail,
- elementy adresu.

Model `PARTY` obejmuje w szczególności:

- nazwę i nazwę skróconą,
- formę prawną,
- kraj rejestracji i datę powstania,
- identyfikatory NIP, REGON, KRS i LEI,
- dane rejestrowe i statusy,
- zakres działalności,
- telefon, adres e-mail i stronę internetową,
- rachunki bankowe,
- elementy adresu,
- informacje o osobach i podmiotach powiązanych.

CEIDG, KRS, rejestr agentów, rejestr pracowników agentów i rejestr firm inwestycyjnych zawierają informacje dotyczące obu modeli. Przykładowo rekord CEIDG opisuje działalność jako `PARTY`, a dane właściciela jako `PERSON`. Rekord KRS może zawierać główny podmiot oraz osoby reprezentujące i inne podmioty pozostające z nim w relacji.

Rozdzielenie encji następuje na etapie stagingu. Dla jednego pliku można wykonać osobne ładowanie do `Person_Staging` i `Party_Staging`, jeżeli dla danego źródła istnieją mapowania obu typów.

## Mapowanie kolumn

Każde źródło może używać innego nazewnictwa i struktury danych. Mapowania są przechowywane w tabeli `meta.ColumnMapping` i wiążą:

- system źródłowy,
- typ encji,
- nazwę kolumny źródłowej,
- nazwę pola kanonicznego.

Przykładowo pole `firma.wlasciciel.pesel` z CEIDG jest mapowane na `PESEL` encji `PERSON`, a pole `firma.nip` na identyfikator encji `PARTY`. W źródle Oracle pola `TAX_REF`, `STAT_REG_REF` i `COURT_REF` są przekształcane odpowiednio do identyfikatorów NIP, REGON i KRS.

Mapowanie nie ogranicza się do prostego przypisania jednej kolumny. `app/layers/staging_validation/mapper.py`:

- wyszukuje wartości bez rozróżniania wielkości liter,
- obsługuje zagnieżdżone ścieżki dokumentów,
- ujednolica nazwy identyfikatorów,
- składa wiele kolumn do `Identifiers_JSON`,
- zachowuje pierwszą niepustą wartość przy powtarzających się polach,
- zapisuje oryginalny rekord w `Raw_Record_JSON`.

Szczególną obsługę posiada KRS. Szerokie zestawy kolumn opisujące członków zarządu, prokurentów, wspólników i inne powiązania są grupowane do struktur JSON. Struktura plików przewiduje do dziesięciu slotów dla danego rodzaju relacji, natomiast generator danych wypełnia maksymalnie cztery i pozostawia pozostałe puste. Dzięki temu dane relacyjne nie muszą być przechowywane jako duża liczba osobnych kolumn stagingowych.

Definicje systemów źródłowych i mapowań znajdują się w `scripts/init_proposed_mssql_schema.sql`. Samo automatyczne utworzenie tabel przez SQLAlchemy nie wypełnia `ColumnMapping`, dlatego do działania mapowania na przygotowanej bazie wymagane jest wykonanie skryptu inicjalizacyjnego.

## Demonstracyjne źródło Oracle

Oracle Insurance Core symuluje relacyjny system dziedzinowy. Struktura jest tworzona przez `scripts/init_oracle_insurance_core.sql` i obejmuje między innymi:

- klientów,
- jednostki organizacyjne,
- identyfikatory klientów,
- adresy,
- historię kontaktów,
- rachunki płatnicze,
- umowy i strony umów,
- przypisania agentów,
- relacje pomiędzy klientami.

Warstwa ingestion wykonuje przygotowane zapytania dla encji `PARTY` i `PERSON`. Wynik zapytania jest wzbogacany o role osób i relacje pomiędzy podmiotami, a następnie serializowany do JSON. Taki snapshot zostaje zapisany w `raw.RawFile` i przechodzi przez ten sam pipeline co dane dostarczone w plikach.

Ogólna nazwa zapytania `insurance_core_export` jest rozwijana do właściwego zapytania zależnie od wybranego typu encji. Implementacja znajduje się w:

- `RELATIONAL_QUERY_DEFINITIONS`,
- `resolve_relational_query_definition()`,
- `extract_relational_records()`,
- `import_relational_source()`

w pliku `app/layers/ingestion/service.py`.

Poprawność importu i tworzenia snapshotów sprawdzają testy w `tests/test_relational_ingestion.py`.

## Dane referencyjne TERYT

Pliki `SIMC.csv` i `ULIC.csv` są wykorzystywane przez warstwę validation do sprawdzania miejscowości oraz ulic. Dane są ładowane do katalogu dostępnego dla API, a następnie przetwarzane do indeksów używanych podczas walidacji.

Walidacja TERYT tworzy między innymi wyniki reguł:

- `ADDR_TERYT_CITY_EXISTS`,
- `ADDR_TERYT_STREET_EXISTS`.

Wynik weryfikacji adresu jest wykorzystywany nie tylko jako informacja o jakości. Podczas wyboru wartości Golden Record adres potwierdzony w TERYT może otrzymać pierwszeństwo przed innym wariantem.

Obsługę danych TERYT realizują:

- endpoint `POST /layers/validation/teryt-load`,
- funkcje `load_teryt_index()`, `validate_teryt_city_exists()` i `validate_teryt_street_exists()` w `app/layers/validation/service.py`,
- zadanie `teryt_load` w DAG Airflow.

Testy znajdują się w `tests/test_teryt_validation.py`.

## Automatyczne rozpoznawanie źródła w Airflow

DAG może automatycznie wyznaczyć kod źródła na podstawie nazwy pliku. Słownik `SOURCE_SYSTEM_BY_FILE_STEM` mapuje nazwę bazową, na przykład `pesel` albo `regon`, na kod systemu źródłowego.

Airflow określa również typ encji:

- GLEIF, rejestr pieniądza elektronicznego, PESEL, REGON i VAT mają jeden domyślny typ encji,
- CEIDG, KRS, rejestr agentów, rejestr pracowników agentów i rejestr firm inwestycyjnych są przetwarzane zarówno jako `PARTY`, jak i `PERSON`,
- źródło relacyjne może zwrócić oba typy encji,
- użytkownik może nadpisać automatyczny wybór parametrem DAG.

Automatyczne rozpoznawanie wymaga zachowania znanej nazwy pliku. Dla innej nazwy należy jawnie podać `source_system_code`. Podobnie nieznany lub niestandardowy układ kolumn wymaga dodania odpowiednich rekordów do `meta.ColumnMapping`.

## Dane syntetyczne

Zbiory syntetyczne zostały przygotowane tak, aby umożliwiały sprawdzanie zarówno poprawnych przypadków, jak i kontrolowanych anomalii. Zawierają między innymi:

- literówki w nazwach i nazwiskach,
- niepełne adresy,
- błędne lub brakujące identyfikatory,
- warianty tego samego rekordu występujące w różnych źródłach,
- osoby i podmioty powiązane,
- daty obowiązywania relacji,
- różnice danych kontaktowych.

Adresy bazowe są budowane z kuratorowanej listy kombinacji województwa, powiatu, gminy, miejscowości, ulicy i kodu pocztowego. Generator celowo wprowadza niewielki odsetek anomalii, aby walidacja i matching nie były sprawdzane wyłącznie na danych idealnych.

Regenerację danych wykonuje skrypt:

```text
scripts/refine_synthetic_data.js
```

Jakość wygenerowanych zbiorów jest kontrolowana w `tests/test_synthetic_data_quality.py`. Testy sprawdzają między innymi brak nieuzasadnionego współdzielenia dokumentów tożsamości, spójność identyfikatorów podmiotów, chronologię dat oraz zgodność części danych osobowych.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| Lista źródeł i formatów | `app/layers/ingestion/service.py` |
| Import plikowy i relacyjny | `app/layers/ingestion/api.py`, `app/layers/ingestion/service.py` |
| Automatyczny wybór źródła i encji | `airflow/dags/goldenizacja_pipeline.py` |
| Model mapowań | `app/layers/staging_validation/models.py` |
| Logika mapowania | `app/layers/staging_validation/mapper.py` |
| Definicje mapowań źródeł | `scripts/init_proposed_mssql_schema.sql` |
| Dane plikowe | `data/csv`, `data/json`, `data/xml`, `data/xlsx` |
| Manifest liczebności | `data/manifest.json` |
| Generator danych syntetycznych | `scripts/refine_synthetic_data.js` |
| Demonstracyjna baza Oracle | `scripts/init_oracle_insurance_core.sql` |
| Dane referencyjne TERYT | `data/teryt` |
| Testy importu relacyjnego | `tests/test_relational_ingestion.py` |
| Testy mapowania | `tests/test_staging_mapper.py` |
| Testy danych syntetycznych | `tests/test_synthetic_data_quality.py` |
| Testy TERYT | `tests/test_teryt_validation.py` |
