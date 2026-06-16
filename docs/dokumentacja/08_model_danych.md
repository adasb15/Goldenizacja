# 8. Model danych

Model danych platformy został podzielony zgodnie z kolejnymi etapami przetwarzania. Centralnym repozytorium jest Microsoft SQL Server, w którym zastosowano cztery schematy: `meta`, `raw`, `stg` i `gold`. Podział ogranicza mieszanie danych źródłowych, technicznych informacji o procesie, rekordów roboczych oraz wynikowych encji Golden Record.

Pełna definicja fizyczna bazy znajduje się w `scripts/init_proposed_mssql_schema.sql`. Modele SQLAlchemy odwzorowują tabele wykorzystywane bezpośrednio przez aplikację i znajdują się w plikach `models.py` poszczególnych warstw.

## 8.1. Organizacja schematów

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

## 8.2. Schemat META

Schemat `meta` przechowuje słownik źródeł, partie importu, mapowania kolumn i logi procesu. `SourceSystem.Trust_Level` jest wykorzystywany podczas survivorship, natomiast `ImportBatch_ID` przechodzi przez kolejne warstwy i łączy wyniki z konkretnym importem.

| Tabela | Klucz główny | Najważniejsze kolumny | Relacje i ograniczenia |
|---|---|---|---|
| `meta.SourceSystem` | `SourceSystem_ID INT` | `SourceSystem_Code NVARCHAR(50)`, `SourceSystem_Name NVARCHAR(255)`, `Trust_Level TINYINT`, `Created_At DATETIME2(0)` | unikalny kod źródła; `Trust_Level` w zakresie 0-100 |
| `meta.ImportBatch` | `ImportBatch_ID BIGINT` | `SourceSystem_ID`, `Import_Status`, `Import_Start_At`, `Import_End_At`, `Created_By`, `Error_Message` | FK do `SourceSystem`; status ograniczony do zdefiniowanego zbioru |
| `meta.ColumnMapping` | `ColumnMapping_ID INT` | `SourceSystem_ID`, `Entity_Type`, `Source_Column_Name`, `Canonical_Column_Name` | FK do `SourceSystem`; unikalna kombinacja źródła, encji i kolumny wejściowej |
| `meta.ProcessLog` | `ProcessLog_ID BIGINT` | `ImportBatch_ID`, `RawFile_ID`, `Staging_ID`, `Step_Name`, `Step_Status`, liczniki i czasy | FK do `ImportBatch` i `RawFile`; kontrolowane nazwy i statusy kroków |

Dozwolone statusy partii to `NEW`, `PROCESSING`, `RAW_LOADED`, `STAGING_LOADED`, `COMPLETED` i `FAILED`. `ProcessLog` rozróżnia kroki procesu oraz statusy `STARTED`, `SUCCESS` i `FAILED`, zapisując także liczniki i komunikaty błędów.

## 8.3. Schemat RAW

Schemat `raw` zawiera tabelę `RawFile` przechowującą plik albo snapshot JSON importu relacyjnego. Zawartość jest zapisana jako `VARBINARY(MAX)`, a unikalny SHA-256 służy do wykrywania identycznych danych wejściowych.

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

`ImportBatch_ID` wskazuje partię importu i posiada indeks. Szczegóły pobierania, kontroli duplikatów oraz wyboru `VARBINARY(MAX)` opisano w rozdziale 10.

## 8.4. Schemat STG

Schemat `stg` obejmuje dane kanoniczne, dane po normalizacji, wyniki kontroli jakości oraz struktury pomocnicze matchingu i grupowania.

### Dane stagingowe

`stg.Person_Staging` i `stg.Party_Staging` przechowują dane po parsowaniu i mapowaniu. Obie tabele zachowują `ImportBatch_ID`, `RawFile_ID`, `Source_Record_ID` i kopię rekordu źródłowego w JSON.

#### Person_Staging

| Grupa kolumn | Kolumny | Znaczenie |
|---|---|---|
| klucze i pochodzenie | `Staging_ID`, `ImportBatch_ID`, `RawFile_ID`, `Source_Record_ID` | identyfikacja rekordu i źródła |
| dokumenty i identyfikatory | `PESEL`, `Serial_Number_ID_Card`, `Serial_Number_Passport` | identyfikatory osoby w postaci otrzymanej po mapowaniu |
| dane osobowe | `First_Name`, `Second_Name`, `Last_Name`, `Family_Name`, `Birth_Date`, `Place_Of_Birth`, `Sex`, `Citizenship` | kanoniczny zestaw danych osoby |
| kontakt | `Phone_Number`, `Email_Address` | dane kontaktowe |
| adres | `Street`, `Building_Number`, `Apartment_Number`, `City`, `Postal_City`, `Postal_Code`, `District`, `Province`, `Country` | adres zapisany jeszcze przy rekordzie stagingowym |
| audyt mapowania | `Raw_Record_JSON`, `Created_At` | kopia rekordu wejściowego i czas zapisu |

`Raw_Record_JSON` podlega kontroli poprawności JSON. Kolumny biznesowe są opcjonalne, ponieważ rekordy niekompletne są oceniane dopiero podczas walidacji.

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

Tabele preprocessingowe przechowują wartości znormalizowane bez nadpisywania stagingu. `Preprocessing_Rules_JSON` opisuje zastosowane przekształcenia.

| Tabela | Klucz główny | Powiązanie ze stagingiem | Główne grupy danych |
|---|---|---|---|
| `stg.Person_Preprocessed` | `Preprocessed_ID` | `Staging_ID` FK do `Person_Staging`, relacja unikalna 1:1 | identyfikatory, pełna nazwa osoby, kontakt i adres po normalizacji |
| `stg.Party_Preprocessed` | `Preprocessed_ID` | `Staging_ID` FK do `Party_Staging`, relacja unikalna 1:1 | nazwa, identyfikatory, rejestry, kontakt, adres i relacje po normalizacji |

Bezpośrednie klucze do partii i RAW upraszczają filtrowanie przebiegu. Wybrane pola znormalizowane są objęte indeksami odpowiadającymi ścieżkom wyszukiwania kandydatów, na przykład kombinacja `PESEL_Normalized` i `Full_Name_Normalized`.

### Walidacja

`stg.Validation_Result` zapisuje osobny wynik każdej reguły i pola, dzięki czemu jeden rekord może mieć wiele ocen jakości.

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

Kandydaci Levenshteina i Jaro-Winklera zachowują porównywaną parę, wynik, decyzję i uzasadniające ją pola. Zaakceptowane powiązania tworzą grupy encji, a grupy niespełniające warunków materializacji mogą zostać zapisane w rejestrze odrzuceń.

| Tabela | Klucz i najważniejsze relacje | Integralność |
|---|---|---|
| `Match_Candidate_Levenshtein` | para `Left_Preprocessed_ID` i `Right_Preprocessed_ID`; opcjonalne powiązanie z `RawFile_ID` | wynik 0-1; typ `PERSON`/`PARTY`; lewy identyfikator mniejszy od prawego; unikalna para w pliku |
| `Match_Candidate_JaroWinkler` | FK `Levenshtein_Candidate_ID` do pierwszego etapu; ta sama para rekordów | oba wyniki 0-1; kontrolowane decyzje; poprawne pola JSON |
| `Entity_Group` | `Entity_Group_ID`; unikalne `Entity_Type` i `Group_Key` | typ `PERSON` albo `PARTY` |
| `Entity_Group_Member` | FK złożony do grupy; FK do odpowiedniej tabeli preprocessingowej | jeden rekord preprocessingowy może należeć tylko do jednej grupy danego typu |
| `Golden_Record_Reject` | opcjonalny FK złożony do grupy oraz FK do `RawFile` | status `OPEN`, `RESOLVED` albo `IGNORED`; poprawność trzech pól JSON |

Pola JSON zachowują podstawę decyzji `AUTO_MERGE`, `REVIEW` albo `CANDIDATE`. `Group_Key` jest stabilnym skrótem członków, a złożone klucze chronią przed połączeniem różnych typów encji.

## 8.5. Schemat GOLD

Model GOLD zatwierdzony w `docs/dokumentacja/diagramy/Goldenizacja - model 22.04.pdf` został odwzorowany w skrypcie SQL razem z kluczami, ograniczeniami, indeksami i słownikami.

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

Główne wymiary przechowują uzgodnione profile osób i podmiotów oraz współdzielone adresy. Adres jest łączony z encją tabelą relacyjną, a nie osadzony bezpośrednio w profilu.

#### DimPerson

| Grupa | Kolumny | Uwagi |
|---|---|---|
| klucz | `Person_ID BIGINT` | klucz techniczny |
| identyfikatory | `PESEL`, `Serial_Number_ID_Card`, `Serial_Number_Passport` | wartości opcjonalne; dla każdej niepustej wartości utworzono unikalny indeks |
| dane osobowe | `First_Name`, `Second_Name`, `Last_Name`, `Family_Name` | wartości wybrane zgodnie z regułami survivorship |
| urodzenie i cechy | `Birth_Date`, `Place_Of_Birth`, `Sex`, `Citizenship` | dane profilu osoby |
| kontakt | `Phone_Number`, `Email_Address` | indeksy nieunikalne, ponieważ dane kontaktowe mogą być współdzielone |
| audyt techniczny | `Created_At`, `Updated_At` | czas utworzenia i ostatniej aktualizacji |

Aktualizacja `DimPerson` nie tworzy nowej wersji wiersza; zmiany są zapisywane w `EntityChangeLog`.

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

Nazwy słownikowe są unikalne, a wartości początkowe są ładowane przez skrypt inicjalizacyjny.

### Identyfikatory i adresy

`FactlessPartyIdentities` przechowuje wiele identyfikatorów podmiotu, m.in. NIP, REGON, KRS i LEI. `FactlessPersonAddress` i `FactlessPartyAddress` przypisują współdzielony adres do encji wraz z typem i okresem obowiązywania.

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

Repozytorium zapobiega ponownemu tworzeniu identycznego aktywnego powiązania. Jeżeli dla osoby lub podmiotu zostanie wybrany inny adres tego samego typu, dotychczas aktywne powiązanie otrzymuje `Valid_To`, a nowe `Valid_From`. Datą graniczną jest dzień rozpoczęcia importu rekordu, z którego wybrano adres, a przy braku tej informacji dzień wykonania goldenizacji. Dzięki temu model zachowuje kolejność obowiązywania adresów bez tworzenia kolejnych wersji głównego wymiaru osoby lub podmiotu. Indeksy po właścicielu i adresie wspierają przechodzenie relacji w obu kierunkach.

### Pozostałe relacje modelu GOLD

Model fizyczny zawiera również wpisy rejestrowe, relacje podmiotów i role osób. Aktualna materializacja zasila profile osób i podmiotów, adresy oraz identyfikatory; wymienione niżej relacje nie są jeszcze zapisywane przez serwis goldenizacji.

| Tabela | Klucze obce | Dane dodatkowe | Kontrola integralności |
|---|---|---|---|
| `FactlessPartyRegisterEntry` | `Party_ID`, `Register_ID`, `RegisterStatus_ID` | `Registration_Date`, `Deregistration_Date` | data wykreślenia nie może poprzedzać rejestracji |
| `FactlessPartyRelationship` | `Parent_Party_ID`, `Child_Party_ID`, `RelationshipType_ID` | `Valid_From`, `Valid_To` | brak relacji podmiotu z samym sobą; poprawny zakres dat |
| `FactlessPersonPartyRole` | `Person_ID`, `Party_ID`, `RoleType_ID` | `Valid_From`, `Valid_To` | poprawny zakres dat |

Odpowiadające im tabele lineage są obecne w modelu fizycznym, ale pozostają poza aktualną ścieżką automatycznego zapisu.

## 8.6. Audyt zmian i lineage

`EntityChangeLog` rejestruje zmianę wartości, natomiast tabele `Golden*Lineage` wskazują pochodzenie aktualnie wybranego atrybutu. Osobne lineage istnieje dla adresów, identyfikatorów i relacji przewidzianych w modelu.

| Kolumna | Typ | Znaczenie |
|---|---|---|
| `Change_ID` | `BIGINT` | klucz wpisu historii |
| `Entity_Type` | `NVARCHAR(20)` | `PERSON`, `PARTY`, `ADDRESS` albo `PARTY_IDENTITY` |
| `DimPerson_ID`, `DimParty_ID`, `DimAddress_ID`, `PartyIdentity_ID` | `BIGINT` | dokładnie jedno wskazanie zmienionej encji |
| `Attribute_Name` | `NVARCHAR(100)` | nazwa zmienionego pola |
| `Old_Value`, `New_Value` | `NVARCHAR(4000)` | wartości przed i po zmianie |
| `Change_Date` | `DATETIME2(0)` | czas zarejestrowania zmiany |
| `ImportBatch_ID` | `BIGINT` | partia, która spowodowała zmianę |

Ograniczenie `CK_EntityChangeLog_Entity_Ref` wymaga wskazania dokładnie jednego identyfikatora zgodnego z `Entity_Type`.

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

`Trust_Score` i `Quality_Score` muszą mieścić się w zakresie 0-1. Indeksy wspierają odczyt po encji, atrybucie, źródle i partii.

W aktualnej implementacji zapis lineage jest wykonywany metodami `upsert_dimension_lineage()` i `upsert_address_link_lineage()` z `app/layers/integration_golden/repository.py`. Dla danego atrybutu wymiaru utrzymywane jest aktualne wskazanie wybranego źródła, a zmiany wartości biznesowej są niezależnie rejestrowane w `EntityChangeLog`.

## 8.7. Relacje między schematami

Ścieżka pochodzenia prowadzi od `SourceSystem` przez `ImportBatch`, `RawFile`, staging i preprocessing do grup encji oraz wymiarów GOLD. Lineage zachowuje źródło, rekord i partię wybranej wartości, a `EntityChangeLog` wiąże zmianę wymiaru z importem.

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

## 8.8. Integralność i inicjalizacja

Skrypt SQL definiuje klucze, ograniczenia, indeksy, słowniki oraz konfigurację źródeł i mapowań.

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

Indeksy odpowiadają głównym ścieżkom dostępu: filtrowaniu przebiegu, wyszukiwaniu kandydatów i wymiarów oraz odczytowi historii i lineage.

## 8.9. Odniesienie do implementacji

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
