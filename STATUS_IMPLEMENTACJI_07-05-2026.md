# Status implementacji procesu goldenizacji danych

## Cel dokumentu

Dokument przedstawia aktualny stan implementacji systemu odpowiedzialnego za przyjęcie danych źródłowych, zapis ich w warstwie RAW, przygotowanie wspólnego modelu stagingowego, preprocessing oraz walidację danych.

## Aktualny zakres procesu

Zaimplementowany przepływ obejmuje obecnie cztery etapy:

1. RAW - przyjęcie pliku źródłowego i zapis oryginalnej treści
2. Staging - mapowanie danych źródłowych do wspólnego modelu tabelarycznego
3. Preprocessing - przygotowanie wartości pochodnych do porównywania i matchingu
4. Validation - kontrola jakości i oznaczanie błędnych rekordów

Warstwy integracji do golden recordów, analityki i serwowania danych mają przygotowaną strukturę projektową, ale nie są jeszcze pełnym końcowym etapem procesu biznesowego.

## Podsumowanie statusu

| Obszar | Status | Uwagi |
| --- | --- | --- |
| Upload plików CSV, JSON, XML, XLSX | Zrobione | Pliki są przyjmowane przez API |
| Zapis oryginalnego pliku w RAW | Zrobione | Treść pliku jest zapisywana binarnie bez modyfikacji |
| Rejestracja importu | Zrobione | Każdy import ma batch, źródło, status i znaczniki czasu |
| Logowanie kroków procesu | Zrobione | Logowane są RAW_LOAD, STAGING_LOAD, STANDARDIZATION i VALIDATION |
| Mapowanie do stagingu | Zrobione | Obsługa osób i podmiotów z wielu źródeł |
| Zachowanie rekordu źródłowego | Zrobione | Staging zapisuje Raw_Record_JSON |
| Raport brakujących i nierozpoznanych kolumn | Zrobione | Wynik staging-load zwraca diagnostykę mapowania |
| Minimalne czyszczenie stagingu | Zrobione | Trimming i usuwanie znaków niedrukowalnych |
| Unifikacja dat i wartości logicznych | Zrobione | Daty jako DATE, wartości logiczne jako BIT |
| Blokada duplikatu pliku RAW | Zrobione | Kontrola przez hash pliku |
| Blokada ponownego staging-load | Zrobione | Ten sam plik nie jest ładowany drugi raz do tego samego stagingu |
| Osobny preprocessing | Zrobione | Dane pochodne są zapisywane w tabelach preprocessed |
| Splitting adresów | Zrobione | Staging pozostaje bezstratny, split jest wartością pochodną |
| Normalizacja nazw i identyfikatorów | Zrobione | UPPER CASE, usuwanie polskich znaków, normalizacja identyfikatorów |
| Normalizacja telefonu i emaila | Zrobione | Telefon do formatu porównawczego, email do lowercase |
| Walidacja PESEL, NIP, REGON | Zrobione | Walidacja sum kontrolnych z użyciem python-stdnum i fallbacków |
| Walidacja LEI, KRS i dowodu osobistego | Zrobione | LEI checksum, KRS format, dowód osobisty checksum |
| Walidacja emaila | Zrobione | Składnia emaila, opcjonalnie DNS/deliverability |
| Oznaczanie błędów jakości | Zrobione | Wyniki zapisywane do stg.Validation_Result |

## Architektura warstw

Aktualna architektura rozdziela odpowiedzialności między warstwami:

```text
RAW -> STAGING -> PREPROCESSING -> VALIDATION -> work in progress
```

Takie rozdzielenie jest istotne, ponieważ każda warstwa ma inne zadanie:

- RAW przechowuje oryginalne wejście
- Staging przechowuje dane po mapowaniu do wspólnego modelu
- Preprocessing tworzy wartości techniczne do porównywania
- Validation sprawdza poprawność formalną danych i zapisuje wyniki reguł

## Warstwa RAW

Warstwa RAW odpowiada za przyjęcie danych źródłowych i zachowanie ich oryginalnej treści.

Obsługiwane formaty:

- CSV
- JSON
- XML
- XLSX

Dla każdego pliku zapisywane są:

- nazwa pliku
- typ pliku
- rozmiar
- hash SHA-256
- oryginalna zawartość binarna
- powiązanie z import batch
- czas utworzenia

Hash pliku pozwala wykryć ponowne wgranie identycznej treści.


## Rejestracja importu i audytowalność

Każde ładowanie danych tworzy import batch. Pełni on rolę technicznego identyfikatora przebiegu importu.

Rejestrowane są:

- źródło danych
- status importu
- czas rozpoczęcia i zakończenia
- użytkownik lub proces uruchamiający
- komunikat błędu, jeśli wystąpił

Każdy etap procesu zapisuje wpis w `meta.ProcessLog`.

Aktualnie logowane kroki:

- RAW_LOAD
- STAGING_LOAD
- STANDARDIZATION
- VALIDATION

Rekordy w kolejnych warstwach zachowują powiązanie z:

- ImportBatch_ID
- RawFile_ID
- Source_Record_ID
- Staging_ID, gdy dane przechodzą do preprocessingu i walidacji

Dzięki temu możliwe jest prześledzenie pochodzenia danych od wyniku walidacji aż do oryginalnego pliku.

## Warstwa Staging

Warstwa stagingowa odpowiada za przekształcenie różnych formatów źródłowych do wspólnego modelu tabelarycznego.

Obsługiwane typy encji:

- PERSON - osoba fizyczna
- PARTY - podmiot lub organizacja

Staging wykonuje:

- odczyt pliku z RAW
- parsowanie CSV, JSON, XML i XLSX
- zastosowanie mapowania kolumn
- zapis do `stg.Person_Staging` albo `stg.Party_Staging`
- zapis `Raw_Record_JSON`
- zapis identyfikatorów podmiotu w `Identifiers_JSON`
- raportowanie brakujących i nierozpoznanych kolumn
- zapis liczników Records_In i Records_Out

Staging wykonuje tylko minimalne czyszczenie:

- usuwa białe znaki z początku i końca wartości
- usuwa znaki niedrukowalne

Staging nie wykonuje splitowania adresów - staging ma zachować dane po mapowaniu, a nie tworzyć interpretacje adresów. Split adresu jest wykonywany dopiero w preprocessingu.

## Unifikacja typów w stagingu

W stagingu ujednolicane są typy, które muszą być poprawnie zapisane w bazie:

- daty są konwertowane do typu DATE
- wartości logiczne są mapowane do BIT
- płeć jest mapowana logicznie: `1` dla kobiet, `0` dla mężczyzn

Przykładowe pola dat:

- Birth_Date
- Registration_Date
- Deregistration_Date
- Decision_Date
- Last_Update_Date
- Next_Renewal_Date
- daty relacji GLEIF

Przykładowe wartości logiczne:

```text
tak, true, 1 -> 1
nie, false, 0 -> 0
brak lub nierozpoznane -> NULL
```

## Mapowanie źródeł danych

Przygotowano mapowania dla wielu źródeł rejestrowych i testowych:

- PESEL
- CEIDG
- KRS
- REGON
- VAT
- GLEIF
- rejestry KNF

Mapowania obejmują dane:

- osobowe
- identyfikacyjne
- adresowe
- kontaktowe
- rejestrowe
- statusowe
- relacyjne

Dla KRS obsługiwane są szerokie kolumny opisujące role i relacje, między innymi członków zarządu, prokurentów, wspólników, likwidatorów i członków rady nadzorczej. Takie dane nie są traktowane jako nierozpoznane kolumny, tylko są składane do struktur JSON do dalszego przetwarzania.

## Warstwa Preprocessing

Preprocessing został wydzielony jako osobna warstwa po stagingu.

Celem tej warstwy jest przygotowanie danych do porównywania, walidacji jakości i późniejszego matchingu.

Wyniki zapisywane są do:

- `stg.Person_Preprocessed`
- `stg.Party_Preprocessed`

Preprocessing tworzy wartości pochodne, ale nie zastępuje stagingu.

Wykonywane operacje:

- normalizacja tekstu do UPPER CASE
- usuwanie polskich znaków przy użyciu `text-unidecode`
- fallback przez `unicodedata`, jeśli biblioteka nie jest dostępna
- normalizacja PESEL, NIP, REGON, KRS i LEI
- normalizacja telefonu do formatu porównawczego
- normalizacja emaila
- normalizacja strony www
- regexowy split adresu

Przykład:

```text
"Łódź sp. z o.o." -> "LODZ SP. Z O.O."
"502 693 570" -> "+48502693570"
"ul. Krótka 12/3, 00-001 Warszawa" -> ulica, budynek, lokal, kod, miasto
```

Zakres pól preprocessed jest węższy niż staging. Tabele preprocessed nie kopiują wszystkich danych źródłowych, tylko przechowują wybrane wartości techniczne, które wymagają walidacji.

## Walidacja danych i kontrola jakości

Walidacja została zaimplementowana jako osobna warstwa po preprocessingu.

Wyniki zapisywane są do:

- `stg.Validation_Result`

Walidacja nie przerywa procesu przy błędnych danych. Każda reguła zapisuje wynik:

- Status = PASS albo ERROR
- Severity = INFO dla poprawnej reguły
- Severity = ERROR dla błędu
- Message = OK albo konkretny kod błędu

Przykładowe kody błędów:

- ERR_CHECKSUM_PESEL
- ERR_CHECKSUM_NIP
- ERR_CHECKSUM_REGON
- ERR_CHECKSUM_LEI
- ERR_FORMAT_KRS
- ERR_CHECKSUM_ID_CARD
- ERR_EMAIL_INVALID
- ERR_FIRST_NAME_NORMALIZED_TYPE

Zaimplementowane reguły walidacyjne:

| Reguła | Zakres | Źródło danych |
| --- | --- | --- |
| PESEL checksum | osoba | preprocessing |
| NIP checksum | podmiot | preprocessing |
| REGON checksum | podmiot | preprocessing |
| LEI checksum | podmiot | preprocessing |
| KRS format | podmiot | preprocessing |
| Dowód osobisty checksum | osoba | staging |
| Email syntax | osoba i podmiot | preprocessing |
| Email deliverability/DNS | osoba i podmiot | opcjonalnie |
| Imię i nazwisko bez cyfr | osoba | preprocessing |
| Nazwa podmiotu niepusta | podmiot | staging |

Walidacja PESEL, NIP, REGON i LEI korzysta z biblioteki `python-stdnum`, a dodatkowo posiada fallbacki matematyczne. Walidacja emaila korzysta z `email-validator`.

Opcjonalne sprawdzanie domeny emaila może być włączone parametrem `check_email_dns=true`.

<!-- ## Geokodowanie

Geokodowanie nie jest obecnie częścią implementacji.

Jest to świadoma decyzja projektowa. Geokodowanie przez zewnętrzne źródła, np. OpenStreetMap, jest wzbogacaniem danych i zależy od dostępności zewnętrznego API, limitów zapytań i jakości odpowiedzi.

W obecnym zakresie zaimplementowano regexowy split adresu w preprocessingu. Geokodowanie może zostać dodane później jako osobny, opcjonalny etap wzbogacania danych. -->

## Testowanie

Dodano testy jednostkowe dla stagingu, preprocessingu i walidacji.

Testy obejmują:

- mapowanie kolumn
- obsługę pól zagnieżdżonych
- zapis identyfikatorów
- zapis Raw_Record_JSON
- cleaning danych
- zachowanie adresów w stagingu bez splitowania
- split adresów w preprocessingu
- normalizację tekstu, telefonu i emaila
- normalizację dat i wartości logicznych
- blokadę ponownego staging-load
- walidację PESEL, NIP, REGON, LEI
- walidację KRS i dowodu osobistego
- walidację emaila
- oznaczanie błędów bez przerywania procesu

Aktualnie uruchamiany zestaw testów:

```text
python3 -m unittest tests.test_preprocessing tests.test_staging_mapper tests.test_validation -v
```

Wynik:

```text
29 tests OK
```


## Wnioski

Zrealizowana część systemu obejmuje przepływ od przyjęcia pliku źródłowego do walidacji danych po preprocessingu. System zachowuje oryginał danych, rejestruje przebieg importu, mapuje dane do wspólnego modelu, przygotowuje wartości porównawcze i zapisuje wyniki walidacji bez przerywania procesu przy błędnych rekordach.

Najważniejszym kolejnym krokiem jest wykorzystanie danych stagingowych, preprocessingowych i wyników walidacji do właściwego matchingu oraz budowy golden recordów.
