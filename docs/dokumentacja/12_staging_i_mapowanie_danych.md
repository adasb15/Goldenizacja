# Staging i mapowanie danych

Warstwa staging przekształca materiał zapisany w RAW do wspólnej struktury osoby albo podmiotu. Na tym etapie dane są parsowane, przypisywane do kolumn kanonicznych i zapisywane w `stg.Person_Staging` lub `stg.Party_Staging`. Oryginalny materiał RAW nie jest modyfikowany.

Staging nie wykonuje pełnej standaryzacji ani oceny jakości biznesowej. Zachowuje wartości możliwie blisko postaci źródłowej, wykonując jedynie sanitację tekstu, konwersję typów wymaganych przez model SQL oraz składanie wybranych struktur do JSON. Właściwa normalizacja danych odbywa się w warstwie preprocessing.

## Interfejs API

Ładowanie stagingu udostępnia endpoint:

```text
POST /layers/staging_validation/staging-load
```

Wywołanie wymaga:

| Parametr | Znaczenie |
|---|---|
| `raw_file_id` | identyfikator materiału zapisanego w `raw.RawFile` |
| `entity_type` | docelowy model `PERSON` albo `PARTY` |

Odpowiedź `StagingLoadResponse` zawiera identyfikatory partii i RAW, typ encji, liczbę rekordów wejściowych i zapisanych, statusy procesu oraz zestawienia brakujących i nierozpoznanych kolumn.

## Przebieg ładowania

Funkcja `load_raw_file_to_staging()` wykonuje następujące operacje:

1. normalizuje typ encji;
2. pobiera `RawFile` i powiązaną partię importu;
3. sprawdza, czy ten sam materiał nie został już załadowany do wskazanej tabeli stagingowej;
4. ustawia partię na `PROCESSING` i tworzy log `STAGING_LOAD`;
5. parsuje zawartość RAW;
6. pobiera mapowania kolumn dla systemu źródłowego i typu encji;
7. buduje rekordy kanoniczne;
8. uzupełnia klucze techniczne, kopię rekordu źródłowego i podstawowe typy danych;
9. zapisuje rekordy do właściwej tabeli;
10. kończy log statusem `SUCCESS` i ustawia partię na `STAGING_LOADED`.

Przy plikach zawierających dane obu typów ten sam `RawFile_ID` może zostać załadowany osobno do `Person_Staging` i `Party_Staging`. Kontrola ponownego wykonania jest prowadzona niezależnie dla każdej tabeli.

## Parsowanie materiału RAW

Parser jest wybierany na podstawie `RawFile.File_Type`.

| Format | Sposób odczytu |
|---|---|
| CSV | `csv.DictReader`, kodowanie UTF-8 z obsługą BOM, pierwszy wiersz jako nagłówek |
| JSON | obiekt jako jeden rekord albo lista obiektów |
| XML | elementy `<record>` zawierające pola `<field name="...">` albo bezpośrednie elementy potomne |
| XLSX | aktywny arkusz otwierany przez `openpyxl` w trybie `read_only`; pierwszy niepusty wiersz jako nagłówek |

Każdy rekord jest reprezentowany jako słownik nazw kolumn i wartości. JSON może zachować struktury zagnieżdżone, natomiast CSV i XLSX dostarczają strukturę płaską. XML bez elementów `<record>` oraz tablica JSON zawierająca wartości inne niż obiekty są odrzucane.

## Mapowania kolumn

Mapowania znajdują się w `meta.ColumnMapping` i są wybierane według:

- `SourceSystem_ID`,
- `Entity_Type`,
- `Source_Column_Name`.

Kolumna `Canonical_Column_Name` wskazuje pole modelu `PERSON` lub `PARTY`. Mapowania dla źródeł projektu są inicjalizowane przez `scripts/init_proposed_mssql_schema.sql`. Brak jakiegokolwiek mapowania dla danej kombinacji źródła i encji powoduje przerwanie stagingu.

Przykładowe mapowania:

| Źródło | Kolumna źródłowa | Typ encji | Kolumna kanoniczna |
|---|---|---|---|
| PESEL | `Imie` | `PERSON` | `First_Name` |
| PESEL | `DataUrodzenia` | `PERSON` | `Birth_Date` |
| CEIDG | `firma.wlasciciel.nazwisko` | `PERSON` | `Last_Name` |
| CEIDG | `firma.nazwa` | `PARTY` | `Name` |
| KRS | `numerKRS` | `PARTY` | `Identifiers_JSON` |
| GLEIF | `LegalName` | `PARTY` | `Name` |
| VAT | `accountNumbers` | `PARTY` | `Bank_Accounts_JSON` |
| INSURANCE_CORE | `PARTY_LABEL` | `PARTY` | `Name` |
| INSURANCE_CORE | `NATIONAL_REF` | `PERSON` | `PESEL` |

Nazwy kolumn są porównywane bez uwzględnienia wielkości liter. Notacja kropkowa obsługuje zarówno zagnieżdżone obiekty, na przykład `firma.wlasciciel.imie`, jak i płaskie nagłówki CSV zawierające kropki.

Jeżeli kilka kolumn źródłowych prowadzi do tego samego pola kanonicznego, wybierana jest pierwsza niepusta wartość według kolejności mapowań pobranych z bazy.

## Raport mapowania

Dla każdego rekordu mapper ustala:

- kolumny zdefiniowane w mapowaniu, których nie było w rekordzie źródłowym;
- kolumny obecne w źródle, które nie zostały rozpoznane przez mapowanie.

Odpowiedź API agreguje te informacje jako słowniki `missing_columns` i `unrecognized_columns`, w których wartością jest liczba rekordów dotkniętych danym problemem. Brak pojedynczej mapowanej kolumny nie zatrzymuje ładowania. Pole docelowe pozostaje puste, a brak jest raportowany.

Kolumny użyte jako techniczny identyfikator rekordu oraz rozpoznane szerokie pola relacji KRS nie są wykazywane jako nierozpoznane. Raport służy do wykrywania zmian struktury źródła, ale nie zastępuje późniejszej walidacji wartości.

## Budowa rekordu stagingowego

Każdy zapisany rekord otrzymuje:

- `ImportBatch_ID`,
- `RawFile_ID`,
- `Source_Record_ID`,
- pola kanoniczne właściwe dla typu encji,
- `Raw_Record_JSON`,
- techniczny czas utworzenia.

`Raw_Record_JSON` jest kopią pojedynczego rekordu po usunięciu niedrukowalnych znaków z wartości tekstowych. Pozwala odnieść dane kanoniczne do struktury wejściowej bez ponownego parsowania całego materiału RAW.

### Identyfikator rekordu źródłowego

`Source_Record_ID` jest wybierany w kolejności:

1. wartość przypisana przez mapowanie do `Source_Record_ID`;
2. jedna z rozpoznawanych kolumn źródłowych, m.in. `id`, `firma.id`, `numerKRS`, `PESEL` albo `LEI`;
3. numer rekordu w przetwarzanym materiale.

Ostatni wariant zapewnia techniczne wskazanie rekordu, ale nie jest stabilnym identyfikatorem biznesowym po zmianie kolejności danych wejściowych.

## Model PERSON

`Person_Staging` przechowuje identyfikatory osoby, imiona i nazwiska, dane urodzenia, płeć, obywatelstwo, kontakt oraz elementy adresu.

Podczas budowy rekordu:

- `Birth_Date` jest konwertowane do typu `DATE`;
- `Sex` jest mapowane do wartości `BIT`, gdzie rozpoznawane oznaczenia kobiety dają `true`, a mężczyzny `false`;
- niepoprawna lub nierozpoznana wartość daty albo płci jest zapisywana jako `NULL`.

Dla szerokich danych KRS mapper wybiera jedną spójną grupę osoby powiązanej, zamiast łączyć imię, nazwisko i PESEL pochodzące z różnych ról lub slotów.

## Model PARTY

`Party_Staging` obejmuje profil podmiotu, identyfikatory, adres, dane rejestrowe, kontakt, rachunki bankowe oraz informacje o osobach i podmiotach powiązanych.

Wybrane wartości są przygotowywane do zapisu:

- daty rejestrowe i daty relacji są konwertowane do `DATE`;
- `Has_Virtual_Accounts` jest konwertowane do `BIT`;
- rachunki bankowe są zapisywane jako tablica JSON;
- identyfikatory pochodzące z wielu kolumn są łączone w `Identifiers_JSON`.

Rozpoznawane klucze identyfikatorów obejmują m.in. NIP, REGON, KRS, LEI i numer UKNF. Dzięki temu źródła używające różnych nazw, takich jak `nip`, `TAX_REF` lub `Numer NIP`, tworzą wspólną strukturę JSON.

Szerokie kolumny KRS opisujące członków zarządu, prokurentów, wspólników, likwidatorów i członków rady nadzorczej są grupowane do `Related_Persons_JSON`. Dane wspólników będących podmiotami trafiają do `Related_Parties_JSON`. Struktury zachowują rolę lub rodzaj relacji, numer slotu, dane identyfikacyjne oraz dostępny okres obowiązywania.

## Zakres konwersji

Staging wykonuje wyłącznie konwersje potrzebne do utworzenia spójnego rekordu technicznego. Nie rozdziela złożonych linii adresowych na ulicę, numer budynku, kod i miejscowość. Jeżeli źródło przekazuje cały adres w jednym polu, wartość pozostaje w kolumnie wskazanej przez mapowanie.

Nie są również wykonywane:

- normalizacja wielkości liter i znaków diakrytycznych;
- standaryzacja numerów telefonów i adresów e-mail;
- kontrola sum identyfikatorów;
- walidacja danych z TERYT;
- ocena jakości rekordów.

Operacje te należą do kolejnych warstw procesu.

## Statusy, błędy i powtarzalność

Ponowne załadowanie tego samego `RawFile_ID` do tej samej tabeli stagingowej jest blokowane. Taki przypadek nie ustawia wcześniej poprawnej partii na `FAILED`.

HTTP 400 jest zwracany m.in. przy:

- braku materiału RAW lub partii;
- braku mapowań kolumn;
- nieobsługiwanym albo uszkodzonym formacie;
- ponownej próbie załadowania tego samego zakresu.

Pozostałe wyjątki kończą log `STAGING_LOAD` i partię statusem `FAILED`, o ile zostały już utworzone. Niepoprawny `entity_type` nie jest obecnie przechwytywany przez listę kontrolowanych wyjątków endpointu i może zostać zwrócony jako HTTP 500.

Repozytorium zatwierdza osobno zmianę statusu partii, utworzenie logu, zapis rekordów i zakończenie procesu. Operacja nie jest jedną transakcją obejmującą cały staging.

## Ograniczenia

Aktualna implementacja:

- odczytuje całe rekordy źródłowe do pamięci przed mapowaniem;
- wymaga mapowań zdefiniowanych w bazie;
- nie udostępnia administracyjnego API do zarządzania mapowaniami;
- zapisuje nierozpoznane daty i wartości logiczne jako `NULL` bez osobnego błędu;
- nie aktualizuje istniejącego stagingu, lecz blokuje ponowne ładowanie;
- zachowuje tylko jeden rekord `PERSON` z szerokiego rekordu KRS, mimo że może on zawierać wiele osób powiązanych.

Pełne listy kolumn tabel stagingowych i ich ograniczenia opisano w rozdziale 9.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| endpoint stagingu | `app/layers/staging_validation/api.py` |
| przebieg ładowania i konwersje typów | `app/layers/staging_validation/service.py` |
| mapowanie do modelu kanonicznego | `app/layers/staging_validation/mapper.py` |
| operacje bazodanowe | `app/layers/staging_validation/repository.py` |
| modele `ColumnMapping`, `Person_Staging`, `Party_Staging` | `app/layers/staging_validation/models.py` |
| definicje tabel i mapowania źródeł | `scripts/init_proposed_mssql_schema.sql` |
| testy mapowania | `tests/test_staging_mapper.py` |

