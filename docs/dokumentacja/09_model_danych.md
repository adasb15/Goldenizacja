# Model danych

Model danych platformy został podzielony zgodnie z kolejnymi etapami przetwarzania. Centralnym repozytorium jest Microsoft SQL Server, w którym zastosowano cztery schematy: `meta`, `raw`, `stg` i `gold`. Podział ogranicza mieszanie danych źródłowych, technicznych informacji o procesie, rekordów roboczych oraz wynikowych encji Golden Record.

Pełna definicja fizyczna bazy znajduje się w `scripts/init_proposed_mssql_schema.sql`. Modele SQLAlchemy odwzorowują tabele wykorzystywane bezpośrednio przez aplikację i znajdują się w plikach `models.py` poszczególnych warstw.

## Organizacja schematów

| Schemat | Przeznaczenie | Przykładowe dane |
|---|---|---|
| `meta` | zarządzanie źródłami i przebiegiem procesu | systemy źródłowe, partie importu, mapowania kolumn, logi |
| `raw` | zachowanie danych w postaci otrzymanej ze źródła | treść pliku lub snapshot wyniku zapytania relacyjnego |
| `stg` | przygotowanie danych do integracji | rekordy kanoniczne, wartości znormalizowane, wyniki walidacji, kandydaci matchingu |
| `gold` | przechowywanie uzgodnionych danych wynikowych | osoby, podmioty, adresy, identyfikatory, relacje i lineage |

Identyfikatory `ImportBatch_ID` i `RawFile_ID` łączą kolejne warstwy procesu. Umożliwiają wskazanie partii importu oraz materiału źródłowego, z którego pochodzi dany rekord roboczy lub wynik walidacji. W warstwie GOLD pochodzenie jest dodatkowo rejestrowane na poziomie wybranych atrybutów i relacji.

### Konwencje modelu

W modelu zastosowano następujące konwencje:

- nazwa klucza głównego składa się z nazwy obiektu i przyrostka `_ID`;
- klucze techniczne są generowane przez SQL Server za pomocą `IDENTITY(1,1)`;
- klucze główne tabel procesowych i biznesowych mają przeważnie typ `BIGINT`;
- identyfikatory niewielkich słowników mają typ `INT`;
- daty zdarzeń technicznych są zapisywane jako `DATETIME2(0)` i domyślnie ustawiane przez `SYSUTCDATETIME()`;
- dane tekstowe są przechowywane w typach `NVARCHAR`, aby zachować znaki narodowe;
- zmienne struktury pochodzące ze źródeł są przechowywane w polach `NVARCHAR(MAX)` z ograniczeniem `ISJSON`;
- kolumny `Valid_From` i `Valid_To` określają okres obowiązywania relacji biznesowej, a nie czas technicznego zapisu rekordu;
- nazwy tabel faktów bezmiarowych rozpoczynają się od `Factless`, ponieważ rejestrują wystąpienie relacji, a nie wartość miary.

SQLAlchemy używa odpowiadających typów przenośnych, między innymi `BigInteger`, `Unicode`, `UnicodeText`, `Date`, `DateTime`, `Boolean` i `Numeric`. Szczegółowe ograniczenia i indeksy są definiowane w skrypcie SQL, dlatego skrypt pozostaje nadrzędnym źródłem fizycznej definicji bazy.

## Schemat META

Schemat `meta` przechowuje informacje techniczne niezbędne do kontrolowania importu i odtworzenia przebiegu procesu.

### SourceSystem

Tabela `meta.SourceSystem` jest słownikiem systemów źródłowych. Każde źródło posiada kod, nazwę i opcjonalny poziom zaufania. Identyfikator `SourceSystem_ID` jest wykorzystywany przez partie importu, mapowania kolumn oraz tabele lineage.

Poziom zaufania stanowi jeden z elementów oceny wartości podczas budowy Golden Record. Pozwala preferować dane pochodzące ze źródeł uznanych za bardziej wiarygodne.

### ImportBatch

Tabela `meta.ImportBatch` reprezentuje pojedynczy przebieg importu. Przechowuje między innymi:

- system źródłowy,
- status importu,
- czas rozpoczęcia i zakończenia,
- użytkownika lub proces inicjujący,
- komunikat błędu.

Partia importu jest tworzona przed zapisaniem danych RAW. Jej identyfikator przechodzi następnie przez staging, preprocessing, walidację i lineage.

### ColumnMapping

Tabela `meta.ColumnMapping` definiuje mapowanie nazw pól źródłowych na kolumny modelu kanonicznego osoby albo podmiotu. Dzięki temu różne formaty wejściowe mogą być przetwarzane przez wspólne tabele stagingowe i tę samą logikę dalszych warstw.

Mapowania są inicjalizowane przez skrypt SQL. Model ORM znajduje się w `app/layers/staging_validation/models.py`, natomiast ich użycie podczas ładowania stagingu jest zaimplementowane w `app/layers/staging_validation/mapper.py`.

### ProcessLog

Tabela `meta.ProcessLog` rejestruje wykonanie etapów procesu. Zawiera nazwę i status kroku, czas rozpoczęcia i zakończenia, liczbę rekordów wejściowych i wynikowych oraz ewentualny komunikat błędu.

Powiązanie z `ImportBatch_ID` i opcjonalnie `RawFile_ID` umożliwia analizę konkretnego przebiegu bez łączenia logów wyłącznie na podstawie czasu wykonania.

### Szczegółowe zestawienie tabel META

| Tabela | Klucz główny | Najważniejsze kolumny | Relacje i ograniczenia |
|---|---|---|---|
| `meta.SourceSystem` | `SourceSystem_ID INT` | `SourceSystem_Code NVARCHAR(50)`, `SourceSystem_Name NVARCHAR(255)`, `Trust_Level TINYINT`, `Created_At DATETIME2(0)` | unikalny kod źródła; `Trust_Level` w zakresie 0-100 |
| `meta.ImportBatch` | `ImportBatch_ID BIGINT` | `SourceSystem_ID`, `Import_Status`, `Import_Start_At`, `Import_End_At`, `Created_By`, `Error_Message` | FK do `SourceSystem`; status ograniczony do zdefiniowanego zbioru |
| `meta.ColumnMapping` | `ColumnMapping_ID INT` | `SourceSystem_ID`, `Entity_Type`, `Source_Column_Name`, `Canonical_Column_Name` | FK do `SourceSystem`; unikalna kombinacja źródła, encji i kolumny wejściowej |
| `meta.ProcessLog` | `ProcessLog_ID BIGINT` | `ImportBatch_ID`, `RawFile_ID`, `Staging_ID`, `Step_Name`, `Step_Status`, liczniki i czasy | FK do `ImportBatch` i `RawFile`; kontrolowane nazwy i statusy kroków |

Dozwolone statusy `ImportBatch` to `NEW`, `PROCESSING`, `RAW_LOADED`, `STAGING_LOADED`, `COMPLETED` i `FAILED`. Model umożliwia zatem odróżnienie błędu całej partii od niepowodzenia pojedynczego kroku zapisanego w `ProcessLog`.

`ProcessLog.Step_Name` przyjmuje wartości `RAW_LOAD`, `STAGING_LOAD`, `STANDARDIZATION`, `VALIDATION` i `GOLDEN_LOAD`, natomiast `Step_Status` przyjmuje `STARTED`, `SUCCESS` lub `FAILED`. Kolumny `Records_In` i `Records_Out` pozwalają porównać liczebność danych przed i po danym etapie.

Indeksy schematu META wspierają wyszukiwanie mapowań dla systemu i typu encji, odczyt logów partii oraz filtrowanie logów według kroku i statusu.

## Schemat RAW

Warstwa RAW składa się z tabeli `raw.RawFile`. Przechowuje ona:

- nazwę i typ materiału wejściowego,
- rozmiar,
- skrót SHA-256,
- binarną zawartość,
- identyfikator partii importu,
- datę utworzenia wpisu.

Zawartość jest zapisywana w kolumnie `VARBINARY(MAX)`, mapowanej w SQLAlchemy jako `LargeBinary`. Dotyczy to zarówno plików przesłanych do systemu, jak i wyniku zapytania do źródła relacyjnego, który przed zapisem jest serializowany do JSON.

Unikalny skrót pliku pozwala wykryć ponowną próbę zapisania tej samej zawartości. Zachowanie danych RAW umożliwia ponowne wykonanie dalszych etapów bez ponownego pobierania danych ze źródła.

### Struktura RawFile

| Kolumna | Typ SQL | Wymagalność | Znaczenie |
|---|---|---:|---|
| `RawFile_ID` | `BIGINT IDENTITY` | tak | techniczny klucz materiału RAW |
| `ImportBatch_ID` | `BIGINT` | tak | partia, w ramach której pobrano dane |
| `File_Name` | `NVARCHAR(260)` | tak | nazwa pliku albo techniczna nazwa snapshotu |
| `File_Type` | `NVARCHAR(30)` | tak | format zapisanej zawartości |
| `File_Size` | `BIGINT` | tak | rozmiar zawartości w bajtach; wartość nieujemna |
| `File_Hash` | `CHAR(64)` | tak | skrót SHA-256 używany do kontroli duplikatów |
| `File_Content` | `VARBINARY(MAX)` | nie | oryginalna zawartość pliku lub zserializowany wynik zapytania |
| `Created_At` | `DATETIME2(0)` | tak | techniczny czas zapisu |

`RawFile.ImportBatch_ID` wskazuje `meta.ImportBatch`. Na tej kolumnie utworzono indeks, natomiast `File_Hash` posiada ograniczenie unikalności. Model nie wymaga przechowywania pliku w zewnętrznym systemie plików, ponieważ zawartość jest częścią rekordu RAW.

## Schemat STG

Schemat `stg` obejmuje dane kanoniczne, dane po normalizacji, wyniki kontroli jakości oraz struktury pomocnicze matchingu i grupowania.

### Dane stagingowe

Tabele `stg.Person_Staging` i `stg.Party_Staging` przechowują rekordy po sparsowaniu materiału RAW i zastosowaniu mapowania kolumn.

`Person_Staging` zawiera podstawowe dane identyfikacyjne i kontaktowe osoby oraz jej adres. `Party_Staging` przechowuje dane podmiotu, jego identyfikatory, adres, informacje rejestrowe, dane kontaktowe oraz dostępne informacje o podmiotach i osobach powiązanych.

Obie tabele zachowują:

- `ImportBatch_ID`,
- `RawFile_ID`,
- `Source_Record_ID`,
- kopię rekordu źródłowego w polu JSON.

Pozwala to powiązać rekord kanoniczny z miejscem jego pochodzenia nawet wtedy, gdy nazwy i formaty pól zostały już ujednolicone.

#### Person_Staging

| Grupa kolumn | Kolumny | Znaczenie |
|---|---|---|
| klucze i pochodzenie | `Staging_ID`, `ImportBatch_ID`, `RawFile_ID`, `Source_Record_ID` | identyfikacja rekordu i źródła |
| dokumenty i identyfikatory | `PESEL`, `Serial_Number_ID_Card`, `Serial_Number_Passport` | identyfikatory osoby w postaci otrzymanej po mapowaniu |
| dane osobowe | `First_Name`, `Second_Name`, `Last_Name`, `Family_Name`, `Birth_Date`, `Place_Of_Birth`, `Sex`, `Citizenship` | kanoniczny zestaw danych osoby |
| kontakt | `Phone_Number`, `Email_Address` | dane kontaktowe |
| adres | `Street`, `Building_Number`, `Apartment_Number`, `City`, `Postal_City`, `Postal_Code`, `District`, `Province`, `Country` | adres zapisany jeszcze przy rekordzie stagingowym |
| audyt mapowania | `Raw_Record_JSON`, `Created_At` | kopia rekordu wejściowego i czas zapisu |

Kluczami obcymi są `ImportBatch_ID` oraz `RawFile_ID`. `Raw_Record_JSON` podlega kontroli poprawności JSON. Kolumny biznesowe są opcjonalne, ponieważ warstwa stagingowa przyjmuje także rekordy niekompletne, które zostaną ocenione dopiero podczas walidacji.

#### Party_Staging

| Grupa kolumn | Przykładowe kolumny | Znaczenie |
|---|---|---|
| klucze i pochodzenie | `Staging_ID`, `ImportBatch_ID`, `RawFile_ID`, `Source_Record_ID` | identyfikacja rekordu i źródła |
| dane podmiotu | `Name`, `Short_Name`, `Legal_Entity_Type`, `Registration_Country`, `Establishment_Date` | podstawowe dane opisowe |
| identyfikatory | `Identifiers_JSON`, `Register_Number`, `Decision_Number` | identyfikatory pochodzące z różnych rejestrów |
| adres | pola od `Street` do `Country` | adres podmiotu |
| informacje rejestrowe | `Register_Status`, `Registration_Date`, `Deregistration_Date`, `Decision_Date` | status i daty dotyczące wpisu |
| informacje działalności | `Bank_Accounts_JSON`, `Has_Virtual_Accounts`, `Business_Scope`, `Ownership_Form`, `Municipality` | dane właściwe wybranym źródłom publicznym |
| kontakt i kontekst branżowy | `Phone_Number`, `Email_Address`, `Website`, `Agent_Type`, `Insurance_Company` | dane kontaktowe i dodatkowe |
| relacje | `Related_Persons_JSON`, `Related_Parties_JSON`, pola rodzica bezpośredniego i ostatecznego | osoby i podmioty powiązane |
| dane GLEIF | `Registration_Status`, `Last_Update_Date`, `Next_Renewal_Date`, `Managing_LOU`, pola validation authority | informacje o rejestracji LEI |
| audyt mapowania | `Raw_Record_JSON`, `Created_At` | kopia rekordu wejściowego i czas zapisu |

Pola `Identifiers_JSON`, `Bank_Accounts_JSON`, `Related_Persons_JSON`, `Related_Parties_JSON` i `Raw_Record_JSON` posiadają ograniczenia sprawdzające poprawność JSON. Rozbudowana struktura `Party_Staging` wynika z różnorodności źródeł podmiotowych. Nie wszystkie kolumny muszą być wypełnione dla każdego źródła.

### Dane po preprocessingu

Tabele `stg.Person_Preprocessed` i `stg.Party_Preprocessed` przechowują wartości przygotowane do walidacji i porównywania. Dane oryginalne ze stagingu nie są nadpisywane.

Wartości znormalizowane obejmują między innymi:

- imiona i nazwiska,
- nazwy i formy prawne podmiotów,
- numery PESEL, NIP, REGON, KRS i LEI,
- numery telefonów i adresy e-mail,
- elementy adresu,
- informacje rejestrowe,
- dane o relacjach podmiotów.

Pole `Preprocessing_Rules_JSON` umożliwia zapis informacji o zastosowanych przekształceniach. Każdy rekord preprocessingowy wskazuje odpowiadający mu rekord stagingowy, partię importu i materiał RAW.

#### Struktury preprocessingowe

| Tabela | Klucz główny | Powiązanie ze stagingiem | Główne grupy danych |
|---|---|---|---|
| `stg.Person_Preprocessed` | `Preprocessed_ID` | `Staging_ID` FK do `Person_Staging`, relacja unikalna 1:1 | identyfikatory, pełna nazwa osoby, kontakt i adres po normalizacji |
| `stg.Party_Preprocessed` | `Preprocessed_ID` | `Staging_ID` FK do `Party_Staging`, relacja unikalna 1:1 | nazwa, identyfikatory, rejestry, kontakt, adres i relacje po normalizacji |

Obie tabele posiadają także bezpośrednie klucze obce do `meta.ImportBatch` i `raw.RawFile`. Powtórzenie identyfikatorów procesu jest zamierzone: upraszcza filtrowanie rekordów konkretnego przebiegu bez konieczności każdorazowego łączenia przez tabelę stagingową.

Nazwy pól przekształconych mają przyrostek `_Normalized`. Wyjątkiem są wartości, których typ nie wymaga normalizacji tekstowej, na przykład daty i pola logiczne. Pola `Full_Name_Normalized` i `Full_Address_Normalized` są wartościami pomocniczymi używanymi w porównywaniu rekordów.

Na tabelach preprocessingowych utworzono indeksy odpowiadające regułom wyszukiwania kandydatów. Dla osób obejmują one między innymi PESEL, dokumenty tożsamości, e-mail, telefon oraz kombinacje daty urodzenia z nazwiskiem lub miejscem urodzenia. Dla podmiotów indeksowane są NIP, REGON, KRS, LEI, nazwa z lokalizacją, dane kontaktowe oraz numery rejestrowe.

### Walidacja

Tabela `stg.Validation_Result` zapisuje wynik pojedynczej reguły dla wskazanego rekordu i pola. Rozróżnia poziom wykonania reguły, ważność wyniku oraz status `PASS`, `WARNING` albo `ERROR`.

Taki układ pozwala przechować wiele wyników walidacji dla jednego rekordu bez dodawania osobnej kolumny dla każdej reguły jakości.

#### Struktura Validation_Result

| Kolumna lub grupa | Znaczenie |
|---|---|
| `Validation_ID` | klucz pojedynczego wyniku reguły |
| `ImportBatch_ID`, `RawFile_ID` | identyfikacja przebiegu i materiału wejściowego |
| `Entity_Type` | typ encji: `PERSON` albo `PARTY` |
| `Staging_ID`, `Preprocessed_ID` | wskazanie kontrolowanego rekordu |
| `Validation_Level` | etap kontroli: `STAGING` albo `PREPROCESSING` |
| `Rule_Code`, `Field_Name` | kod reguły i pole, którego dotyczy |
| `Severity` | poziom `INFO`, `WARNING` albo `ERROR` |
| `Status` | wynik `PASS`, `WARNING` albo `ERROR` |
| `Message`, `Checked_Value` | opis wyniku i sprawdzona wartość |

Tabela posiada klucze obce do partii importu i materiału RAW. `Staging_ID` oraz `Preprocessed_ID` są identyfikatorami polimorficznymi zależnymi od `Entity_Type`, dlatego nie wskazują jedną stałą tabelę kluczem obcym.

### Matching i grupowanie

Pierwszy etap matchingu zapisuje pary kandydatów w `stg.Match_Candidate_Levenshtein`. Drugi etap zapisuje wynik ponownej oceny w `stg.Match_Candidate_JaroWinkler`.

Tabele przechowują:

- identyfikatory porównywanych rekordów,
- wynik podobieństwa,
- decyzję,
- pola stanowiące podstawę dopasowania,
- wykryte konflikty.

Po zaakceptowaniu powiązań rekordy są organizowane w `stg.Entity_Group` i `stg.Entity_Group_Member`. Grupa reprezentuje zestaw rekordów źródłowych opisujących tę samą osobę albo ten sam podmiot.

Jeżeli grupa nie zawiera wartości wymaganych do utworzenia Golden Record, informacja jest zapisywana w `stg.Golden_Record_Reject`. Rekord odrzucony pozostaje dostępny wraz z przyczyną, wartościami kandydującymi i listą członków grupy.

### Szczegółowe zestawienie tabel technicznych STG

| Tabela | Klucz i najważniejsze relacje | Integralność |
|---|---|---|
| `Match_Candidate_Levenshtein` | para `Left_Preprocessed_ID` i `Right_Preprocessed_ID`; opcjonalne powiązanie z `RawFile_ID` | wynik 0-1; typ `PERSON`/`PARTY`; lewy identyfikator mniejszy od prawego; unikalna para w pliku |
| `Match_Candidate_JaroWinkler` | FK `Levenshtein_Candidate_ID` do pierwszego etapu; ta sama para rekordów | oba wyniki 0-1; kontrolowane decyzje; poprawne pola JSON |
| `Entity_Group` | `Entity_Group_ID`; unikalne `Entity_Type` i `Group_Key` | typ `PERSON` albo `PARTY` |
| `Entity_Group_Member` | FK złożony do grupy; FK do odpowiedniej tabeli preprocessingowej | jeden rekord preprocessingowy może należeć tylko do jednej grupy danego typu |
| `Golden_Record_Reject` | opcjonalny FK złożony do grupy oraz FK do `RawFile` | status `OPEN`, `RESOLVED` albo `IGNORED`; poprawność trzech pól JSON |

Pola `Strong_Match_Fields_JSON`, `Conflict_Fields_JSON` i `Text_Match_Fields_JSON` zachowują uzasadnienie wyniku porównania. Decyzja może przyjąć wartość `AUTO_MERGE`, `REVIEW` albo `CANDIDATE`.

`Entity_Group.Group_Key` jest stabilnym skrótem obliczonym z uporządkowanego zbioru identyfikatorów członków. Powiązanie grupy z typem encji jest zabezpieczone złożonym kluczem obcym, dzięki czemu członek typu `PERSON` nie może zostać przypisany do grupy `PARTY`.

## Schemat GOLD

Model obszaru GOLD został zatwierdzony w dokumencie `docs/dokumentacja/diagramy/Goldenizacja - model 22.04.pdf`. Obejmuje wymiary osób, podmiotów, adresów i słowników oraz tabele faktów bezmiarowych opisujące identyfikatory i relacje.

Pełny model z diagramu został odwzorowany w skrypcie `scripts/init_proposed_mssql_schema.sql`. Skrypt tworzy klucze główne i obce, ograniczenia integralności, indeksy oraz początkowe wartości słownikowe.

### Zestawienie struktur GOLD

| Grupa | Tabele | Rola |
|---|---|---|
| główne wymiary | `DimPerson`, `DimParty`, `DimAddress` | uzgodnione dane osób, podmiotów i adresów |
| słowniki | `DimAddressType`, `DimIdentityType`, `DimPartyRelationshipType`, `DimRegister`, `DimRegisterStatus`, `DimRoleType` | kontrolowane typy relacji i identyfikatorów |
| fakty bezmiarowe | `FactlessPartyIdentities`, `FactlessPersonAddress`, `FactlessPartyAddress`, `FactlessPartyRegisterEntry`, `FactlessPartyRelationship`, `FactlessPersonPartyRole` | relacje pomiędzy wymiarami |
| audyt zmian | `EntityChangeLog` | historia zmian wartości encji GOLD |
| lineage atrybutów | `GoldenPersonLineage`, `GoldenPartyLineage`, `GoldenAddressLineage`, `GoldenPartyIdentityLineage` | pochodzenie wybranej wartości |
| lineage relacji | `PersonAddressLineage`, `PartyAddressLineage`, `PersonPartyRoleLineage`, `PartyRegisterEntryLineage`, `PartyRelationshipLineage` | pochodzenie utworzonego powiązania |

### Główne wymiary

`gold.DimPerson` przechowuje uzgodniony profil osoby, obejmujący dane identyfikacyjne, datę i miejsce urodzenia, obywatelstwo oraz dane kontaktowe.

`gold.DimParty` przechowuje profil podmiotu: nazwę, nazwę skróconą, formę prawną, kraj rejestracji i datę utworzenia.

`gold.DimAddress` stanowi współdzielony wymiar adresowy. Adres nie jest trwale osadzony w wymiarze osoby lub podmiotu, lecz łączony z nimi za pomocą tabel relacyjnych. Ogranicza to powielanie tej samej struktury adresowej i pozwala przypisać typ adresu.

Wymiary słownikowe obejmują:

- `gold.DimAddressType`,
- `gold.DimIdentityType`,
- `gold.DimPartyRelationshipType`,
- `gold.DimRegister`,
- `gold.DimRegisterStatus`,
- `gold.DimRoleType`.

#### DimPerson

| Grupa | Kolumny | Uwagi |
|---|---|---|
| klucz | `Person_ID BIGINT` | klucz techniczny |
| identyfikatory | `PESEL`, `Serial_Number_ID_Card`, `Serial_Number_Passport` | wartości opcjonalne; dla każdej niepustej wartości utworzono unikalny indeks |
| dane osobowe | `First_Name`, `Second_Name`, `Last_Name`, `Family_Name` | wartości wybrane zgodnie z regułami survivorship |
| urodzenie i cechy | `Birth_Date`, `Place_Of_Birth`, `Sex`, `Citizenship` | dane profilu osoby |
| kontakt | `Phone_Number`, `Email_Address` | indeksy nieunikalne, ponieważ dane kontaktowe mogą być współdzielone |
| audyt techniczny | `Created_At`, `Updated_At` | czas utworzenia i ostatniej aktualizacji |

`DimPerson` jest wyszukiwany przede wszystkim po identyfikatorach o wysokiej sile identyfikacyjnej. Aktualizacja wymiaru nie tworzy nowej wersji wiersza; zmienione wartości są zapisywane w `EntityChangeLog`.

#### DimParty

| Kolumna | Typ SQL | Znaczenie |
|---|---|---|
| `Party_ID` | `BIGINT IDENTITY` | klucz podmiotu |
| `Name` | `NVARCHAR(255) NOT NULL` | uzgodniona pełna nazwa |
| `Short_Name` | `NVARCHAR(255)` | nazwa skrócona |
| `Legal_Entity_Type` | `NVARCHAR(100)` | forma prawna |
| `Registration_Country` | `NVARCHAR(50)` | kraj rejestracji |
| `Establishment_Date` | `DATE` | data utworzenia podmiotu |
| `Created_At`, `Updated_At` | `DATETIME2(0)` | czasy techniczne |

Identyfikatory podmiotu nie są kolumnami `DimParty`. Są przechowywane w `FactlessPartyIdentities`, co pozwala przypisać wiele identyfikatorów różnych typów do jednego wymiaru.

#### DimAddress

| Grupa | Kolumny |
|---|---|
| klucz | `Address_ID` |
| ulica i lokal | `Street`, `Building_Number`, `Apartment_Number` |
| miejscowość | `City`, `Postal_City`, `Postal_Code` |
| podział administracyjny | `District`, `Province`, `Country` |
| audyt techniczny | `Created_At` |

Repozytorium wyszukuje istniejący adres po zestawie pól adresowych. Jeżeli nie znajdzie zgodnego wiersza, tworzy nowy wymiar, a następnie zapisuje powiązanie z osobą lub podmiotem.

#### Wymiary słownikowe

| Tabela | Klucz | Wartość opisowa | Przykładowe wartości inicjalne |
|---|---|---|---|
| `DimAddressType` | `AddressType_ID` | `AddressType_Name` | `REGISTERED`, `CORRESPONDENCE`, `RESIDENCE`, `BUSINESS` |
| `DimIdentityType` | `IdentityType_ID` | `IdentityType_Name` | `PESEL`, `NIP`, `REGON`, `KRS`, `LEI`, `ID_CARD`, `PASSPORT` |
| `DimPartyRelationshipType` | `RelationshipType_ID` | `Relationship_Name` | `DIRECT_PARENT`, `ULTIMATE_PARENT`, `SHAREHOLDER`, `RELATED_PARTY` |
| `DimRegister` | `Register_ID` | `Register_Name` | wartości zależne od rejestrów zasilających |
| `DimRegisterStatus` | `RegisterStatus_ID` | `Status_Name` | `ACTIVE`, `INACTIVE`, `SUSPENDED`, `DEREGISTERED`, `UNKNOWN` |
| `DimRoleType` | `RoleType_ID` | `Role_Name` | `OWNER`, `BOARD_MEMBER`, `PROXY`, `AGENT`, `EMPLOYEE` |

Nazwy w słownikach są unikalne. Skrypt inicjalizacyjny zasila słowniki typów adresu, identyfikatora, statusu, roli i relacji. `DimRegister` jest przygotowany do przechowywania nazw rejestrów właściwych dla podłączonych źródeł.

### Identyfikatory i adresy

Tabela `gold.FactlessPartyIdentities` łączy podmiot z typem i wartością identyfikatora. Umożliwia przechowanie wielu identyfikatorów jednego podmiotu bez rozszerzania `DimParty` o kolejne kolumny. W obecnej materializacji wykorzystywane są między innymi NIP, REGON, KRS i LEI.

Tabele `gold.FactlessPersonAddress` i `gold.FactlessPartyAddress` przypisują adres odpowiednio do osoby i podmiotu. Poza kluczami encji przechowują typ adresu oraz opcjonalny okres obowiązywania relacji.

Powyższe struktury są odwzorowane w modelach SQLAlchemy i obsługiwane przez repozytorium `app/layers/integration_golden/repository.py`.

#### FactlessPartyIdentities

| Kolumna | Znaczenie |
|---|---|
| `PartyIdentity_ID` | klucz techniczny przypisania |
| `Party_ID` | FK do `DimParty` |
| `IdentityType_ID` | FK do `DimIdentityType` |
| `Identity_Value` | wartość identyfikatora |
| `Is_Valid` | informacja o wyniku kontroli identyfikatora |
| `Match_Confidence` | ocena dopasowania w zakresie 0-1 |
| `Valid_From`, `Valid_To` | opcjonalny okres obowiązywania |

Kombinacja `IdentityType_ID` i `Identity_Value` jest unikalna. Oznacza to, że ten sam identyfikator określonego typu nie może zostać przypisany do dwóch podmiotów. Ograniczenie dat wymaga, aby `Valid_To` nie poprzedzało `Valid_From`.

#### Relacje adresowe

`FactlessPersonAddress` i `FactlessPartyAddress` mają analogiczną budowę:

| Element | Osoba | Podmiot |
|---|---|---|
| klucz relacji | `PersonAddress_ID` | `PartyAddress_ID` |
| właściciel relacji | `Person_ID` FK do `DimPerson` | `Party_ID` FK do `DimParty` |
| adres | `Address_ID` FK do `DimAddress` | `Address_ID` FK do `DimAddress` |
| typ | `AddressType_ID` FK do `DimAddressType` | `AddressType_ID` FK do `DimAddressType` |
| okres | `Valid_From`, `Valid_To` | `Valid_From`, `Valid_To` |

Repozytorium zapobiega ponownemu tworzeniu identycznego aktywnego powiązania. Indeksy po właścicielu i adresie wspierają przechodzenie relacji w obu kierunkach.

### Pozostałe relacje modelu GOLD

Zatwierdzony model przewiduje również:

- `gold.FactlessPartyRegisterEntry` dla wpisów podmiotu w rejestrach,
- `gold.FactlessPartyRelationship` dla relacji pomiędzy podmiotami,
- `gold.FactlessPersonPartyRole` dla ról osoby w podmiocie.

Tabele oraz wymagane słowniki i tabele lineage są zdefiniowane w skrypcie SQL i stanowią część modelu fizycznego. Aktualny proces automatycznej materializacji koncentruje się na profilach osób i podmiotów, ich adresach oraz identyfikatorach. Informacje rejestrowe i relacyjne są przyjmowane i normalizowane w warstwie STG, natomiast nie są jeszcze zapisywane przez serwis goldenizacji do wymienionych tabel GOLD.

Rozróżnienie to nie zmienia zatwierdzonej struktury modelu. Określa jedynie zakres tabel zasilanych przez aktualną implementację procesu.

#### Struktura przygotowanych relacji

| Tabela | Klucze obce | Dane dodatkowe | Kontrola integralności |
|---|---|---|---|
| `FactlessPartyRegisterEntry` | `Party_ID`, `Register_ID`, `RegisterStatus_ID` | `Registration_Date`, `Deregistration_Date` | data wykreślenia nie może poprzedzać rejestracji |
| `FactlessPartyRelationship` | `Parent_Party_ID`, `Child_Party_ID`, `RelationshipType_ID` | `Valid_From`, `Valid_To` | brak relacji podmiotu z samym sobą; poprawny zakres dat |
| `FactlessPersonPartyRole` | `Person_ID`, `Party_ID`, `RoleType_ID` | `Valid_From`, `Valid_To` | poprawny zakres dat |

Ich odpowiedniki lineage posiadają klucz do rekordu relacji, źródło, rekord źródłowy, partię importu, regułę wyboru, oceny jakości i czas zapisu. Dzięki temu model jest przygotowany do zachowania pochodzenia także dla relacji innych niż adresowe.

## Audyt zmian i lineage

Tabela `gold.EntityChangeLog` rejestruje zmiany wartości w encjach GOLD. Wpis zawiera:

- typ i identyfikator encji,
- nazwę zmienionego atrybutu,
- poprzednią wartość,
- nową wartość,
- czas zmiany,
- partię importu.

Rejestr jest przeznaczony do analizy sposobu powstawania i zmian rekordów Golden Record. Dla aktualizowanych wymiarów osoby i podmiotu pozwala ustalić, które wartości uległy zmianie w kolejnych przebiegach.

Tabele lineage atrybutów to:

- `gold.GoldenPersonLineage`,
- `gold.GoldenPartyLineage`,
- `gold.GoldenAddressLineage`,
- `gold.GoldenPartyIdentityLineage`.

Każdy wpis wskazuje encję lub identyfikator, nazwę atrybutu, system i rekord źródłowy, partię importu, regułę wyboru, poziom zaufania, ocenę jakości i wynik walidacji.

Dla relacji adresowych zastosowano:

- `gold.PersonAddressLineage`,
- `gold.PartyAddressLineage`.

Pełny model zawiera ponadto analogiczne tabele dla ról, wpisów rejestrowych i relacji podmiotów. Są one przygotowane w skrypcie SQL razem z odpowiadającymi im tabelami faktów bezmiarowych.

### Struktura EntityChangeLog

| Kolumna | Typ | Znaczenie |
|---|---|---|
| `Change_ID` | `BIGINT` | klucz wpisu historii |
| `Entity_Type` | `NVARCHAR(20)` | `PERSON`, `PARTY`, `ADDRESS` albo `PARTY_IDENTITY` |
| `DimPerson_ID`, `DimParty_ID`, `DimAddress_ID`, `PartyIdentity_ID` | `BIGINT` | dokładnie jedno wskazanie zmienionej encji |
| `Attribute_Name` | `NVARCHAR(100)` | nazwa zmienionego pola |
| `Old_Value`, `New_Value` | `NVARCHAR(4000)` | wartości przed i po zmianie |
| `Change_Date` | `DATETIME2(0)` | czas zarejestrowania zmiany |
| `ImportBatch_ID` | `BIGINT` | partia, która spowodowała zmianę |

Ograniczenie `CK_EntityChangeLog_Entity_Ref` zapewnia zgodność `Entity_Type` z odpowiednią kolumną identyfikatora. Przykładowo wpis typu `PERSON` musi wskazywać `DimPerson_ID`, a pozostałe identyfikatory encji muszą pozostać puste.

### Wspólna struktura lineage

Tabele lineage atrybutów mają wspólny zestaw pól:

| Pole | Znaczenie |
|---|---|
| identyfikator lineage | klucz techniczny wpisu |
| identyfikator encji | osoba, podmiot, adres lub identyfikator podmiotu |
| `Attribute_Name` | atrybut, którego pochodzenie opisuje wpis |
| `SourceSystem_ID` | system, z którego wybrano wartość |
| `Source_Record_ID` | identyfikator rekordu w źródle |
| `ImportBatch_ID` | przebieg, podczas którego wybrano wartość |
| `Selection_Rule` | reguła zastosowana podczas survivorship |
| `Trust_Score` | znormalizowany poziom zaufania do źródła |
| `Quality_Score` | ocena jakości wynikająca z walidacji |
| `Validation_Status` | status walidacji wybranej wartości |
| `Recorded_At` | czas zapisania informacji o pochodzeniu |

`Trust_Score` i `Quality_Score` mają typ `DECIMAL(5,4)` i, jeżeli są podane, muszą mieścić się w zakresie 0-1. Indeksy umożliwiają wyszukiwanie lineage po encji i atrybucie oraz po systemie źródłowym, partii importu i czasie zapisu.

W aktualnej implementacji zapis lineage jest wykonywany metodami `upsert_dimension_lineage()` i `upsert_address_link_lineage()` z `app/layers/integration_golden/repository.py`. Dla danego atrybutu wymiaru utrzymywane jest aktualne wskazanie wybranego źródła, a zmiany wartości biznesowej są niezależnie rejestrowane w `EntityChangeLog`.

## Relacje między schematami

Najważniejsza ścieżka kluczy wygląda następująco:

1. `meta.SourceSystem.SourceSystem_ID` wskazuje źródło danych.
2. `meta.ImportBatch.SourceSystem_ID` przypisuje partię do źródła.
3. `raw.RawFile.ImportBatch_ID` przypisuje materiał RAW do partii.
4. tabele stagingowe wskazują jednocześnie `ImportBatch_ID` i `RawFile_ID`;
5. tabele preprocessingowe wskazują rekord stagingowy, partię i plik RAW;
6. wyniki walidacji wskazują rekord stagingowy lub preprocessingowy;
7. grupy encji łączą rekordy preprocessingowe opisujące tę samą encję;
8. serwis tworzy albo aktualizuje wymiary i relacje GOLD;
9. lineage zapisuje źródło, rekord źródłowy i partię dla wybranych wartości;
10. `EntityChangeLog` wiąże zmianę wymiaru z partią, która ją wywołała.

Model nie tworzy bezpośredniego klucza obcego z wymiaru GOLD do pojedynczego rekordu stagingowego. Jest to celowe, ponieważ jeden Golden Record może powstać z wielu rekordów i źródeł. Powiązanie wieloźródłowe jest reprezentowane przez tabele lineage.

### Główne kardynalności

| Relacja | Kardynalność |
|---|---|
| `SourceSystem` - `ImportBatch` | 1:N |
| `ImportBatch` - `RawFile` | 1:N |
| `RawFile` - rekordy stagingowe | 1:N |
| rekord stagingowy - rekord preprocessingowy | 1:0..1 |
| `Entity_Group` - `Entity_Group_Member` | 1:N |
| `DimParty` - `FactlessPartyIdentities` | 1:N |
| `DimPerson` - `FactlessPersonAddress` | 1:N |
| `DimParty` - `FactlessPartyAddress` | 1:N |
| `DimAddress` - relacje adresowe | 1:N |
| wymiar GOLD - wpisy lineage | 1:N według atrybutów |
| wymiar GOLD - `EntityChangeLog` | 1:N |

## Integralność i inicjalizacja

Skrypt SQL definiuje:

- klucze główne i obce,
- ograniczenia unikalności,
- kontrolę zakresów dat,
- kontrolę wartości ocen w przedziale od 0 do 1,
- indeksy wspierające wyszukiwanie identyfikatorów i lineage,
- wartości początkowe słowników,
- konfigurację źródeł i mapowań kolumn.

Podczas uruchamiania FastAPI funkcja `init_db()` wykonuje `Base.metadata.create_all()`. Mechanizm tworzy tabele zarejestrowane w modelach ORM, ale nie zastępuje pełnego skryptu inicjalizacyjnego. Przygotowanie kompletnej struktury, zgodnej z zatwierdzonym modelem GOLD, wymaga uruchomienia `scripts/init_proposed_mssql_schema.sql` zgodnie z instrukcją zawartą w `README.md`.

### Najważniejsze ograniczenia i indeksy

| Obszar | Zastosowane zabezpieczenie |
|---|---|
| systemy źródłowe | unikalny `SourceSystem_Code`, kontrola zakresu `Trust_Level` |
| mapowania | unikalna kolumna źródłowa w obrębie systemu i typu encji |
| RAW | unikalny SHA-256, nieujemny rozmiar pliku |
| staging | kontrola poprawności pól JSON |
| preprocessing | relacja 1:1 ze stagingiem, indeksy na polach matchingu |
| kandydaci | unikalna uporządkowana para rekordów, wyniki w zakresie 0-1 |
| grupy | unikalny klucz grupy i jednoznaczne przypisanie członka |
| osoba GOLD | unikalne niepuste PESEL i numery dokumentów |
| identyfikatory podmiotu | unikalna para typu i wartości identyfikatora |
| relacje okresowe | data końcowa nie wcześniejsza niż początkowa |
| lineage | wyniki zaufania i jakości w zakresie 0-1 |
| historia zmian | zgodność typu encji z dokładnie jednym identyfikatorem |

Indeksy nie są jedynie optymalizacją ogólną. Odzwierciedlają główne ścieżki dostępu aplikacji: filtrowanie po partii i pliku RAW, wyszukiwanie kandydatów po identyfikatorach i danych opisowych, odnajdywanie istniejącego wymiaru oraz odczyt historii i lineage.

## Odniesienie do implementacji

| Obszar | Lokalizacja |
|---|---|
| Zatwierdzony model GOLD | `docs/dokumentacja/diagramy/Goldenizacja - model 22.04.pdf` |
| Pełna definicja SQL Servera | `scripts/init_proposed_mssql_schema.sql` |
| Klasa bazowa ORM | `app/models/base.py` |
| META i RAW | `app/layers/ingestion/models.py` |
| Mapowania i staging | `app/layers/staging_validation/models.py` |
| Preprocessing | `app/layers/preprocessing/models.py` |
| Wyniki walidacji | `app/layers/validation/models.py` |
| Matching, grupy i GOLD | `app/layers/integration_golden/models.py` |
| Operacje na GOLD | `app/layers/integration_golden/repository.py` |
| Budowa Golden Record | `app/layers/integration_golden/service.py` |
| Inicjalizacja ORM | `app/db/init_db.py` |

### Powiązanie tabel z klasami ORM

| Tabela lub grupa | Klasa/model | Repozytorium korzystające z modelu |
|---|---|---|
| `meta.SourceSystem` | `SourceSystem` | `app/layers/ingestion/repository.py` |
| `meta.ImportBatch` | `ImportBatch` | ingestion, staging i goldenizacja |
| `meta.ColumnMapping` | `ColumnMapping` | `app/layers/staging_validation/repository.py` |
| `meta.ProcessLog` | `ProcessLog` | repozytoria kolejnych etapów |
| `raw.RawFile` | `RawFile` | ingestion i staging |
| staging osoby i podmiotu | `PersonStaging`, `PartyStaging` | `app/layers/staging_validation/repository.py` |
| preprocessing osoby i podmiotu | `PersonPreprocessed`, `PartyPreprocessed` | preprocessing, validation i integration_golden |
| wyniki walidacji | `ValidationResult` | `app/layers/validation/repository.py` |
| kandydaci i grupy | `MatchCandidateRecord`, `JaroWinklerCandidateRecord`, `EntityGroupRecord`, `EntityGroupMemberRecord` | `app/layers/integration_golden/repository.py` |
| główne wymiary GOLD | `DimPerson`, `DimParty`, `DimAddress` | `app/layers/integration_golden/repository.py` |
| identyfikatory i adresy | `FactlessPartyIdentities`, `FactlessPersonAddress`, `FactlessPartyAddress` | `app/layers/integration_golden/repository.py` |
| historia i aktywne lineage | `EntityChangeLog` oraz klasy `*Lineage` | `app/layers/integration_golden/repository.py` |
| rejestry, role i relacje podmiotów | definicje fizyczne w skrypcie SQL | obecnie poza automatycznym zapisem serwisu |
