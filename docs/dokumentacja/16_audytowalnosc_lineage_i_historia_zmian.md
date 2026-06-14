# 16. Audytowalność, lineage i historia zmian

System przechowuje informacje pozwalające odtworzyć, z jakiego źródła pochodzą aktualne wartości Golden Record, kiedy wykonano poszczególne kroki procesu oraz jakie atrybuty osób i podmiotów uległy zmianie przy kolejnych aktualizacjach. Mechanizm ten nie jest jednak pełnym wersjonowaniem całego stanu encji w czasie. Obejmuje trzy uzupełniające się obszary:

1. logi technicznego przebiegu procesu,
2. lineage aktualnie wybranych wartości i relacji,
3. rejestr zmian atrybutów wymiarów.

## 16.1. Logi przebiegu procesu

Podstawowym technicznym śladem wykonania jest tabela `meta.ProcessLog`. Rekord logu jest tworzony dla wybranych etapów i zawiera:

- `ImportBatch_ID`,
- opcjonalny `RawFile_ID`,
- nazwę kroku,
- status,
- czas rozpoczęcia i zakończenia,
- liczbę rekordów wejściowych i wyjściowych,
- komunikat błędu.

W modelu danych dozwolone są kroki takie jak:

- `RAW_LOAD`,
- `STAGING_LOAD`,
- `STANDARDIZATION`,
- `VALIDATION`,
- `GOLDEN_LOAD`.

Statusy techniczne obejmują:

- `STARTED`,
- `SUCCESS`,
- `FAILED`.

Log procesu służy do odpowiedzi na pytania:

- czy krok został uruchomiony,
- czy zakończył się poprawnie,
- ile rekordów albo grup objął,
- jaki błąd zatrzymał etap.

Nie jest to jednak dziennik wszystkich decyzji biznesowych podejmowanych podczas matchingu i survivorship. Na przykład matching i grupowanie nie zapisują osobnych wpisów `ProcessLog` dla każdej pary lub każdej decyzji.

## 16.2. Logowanie etapu GOLD

Warstwa `integration_golden` tworzy wpis `ProcessLog` dla kroku `GOLDEN_LOAD`, jeżeli wywołanie odbywa się w kontekście konkretnego `RawFile_ID`.

Przebieg jest następujący:

1. pobranie `ImportBatch_ID` powiązanego z `RawFile_ID`,
2. utworzenie logu ze statusem `STARTED`,
3. wykonanie materializacji grup,
4. zakończenie logu statusem `SUCCESS` albo `FAILED`.

Przy powodzeniu zapisywane są:

- liczba grup w zakresie wykonania,
- liczba grup przetworzonych do GOLD.

Przy błędzie zapisywany jest komunikat wyjątku. Log ten opisuje wynik techniczny całego wywołania `golden-load`, a nie wynik każdej pojedynczej reguły survivorship.

## 16.3. Czym jest lineage w tym systemie

Lineage opisuje pochodzenie aktualnie wybranej wartości Golden Record albo aktualnie utrwalonej relacji. Dla każdej zapisanej wartości system stara się zachować:

- system źródłowy,
- identyfikator rekordu źródłowego,
- partię importu,
- regułę wyboru,
- poziom zaufania,
- wynik jakości i walidacji.

Lineage nie przechowuje całej ścieżki wszystkich rozważanych kandydatów dla każdego atrybutu. Przechowuje wyłącznie to źródło, które zostało wykorzystane do zapisania bieżącej wartości.

## 16.4. Tabele lineage

Aktualna implementacja wykorzystuje następujące tabele:

- `gold.GoldenPersonLineage`,
- `gold.GoldenPartyLineage`,
- `gold.GoldenAddressLineage`,
- `gold.GoldenPartyIdentityLineage`,
- `gold.PersonAddressLineage`,
- `gold.PartyAddressLineage`.

Struktura tych tabel jest podobna. Zawierają one między innymi:

- identyfikator obiektu docelowego,
- nazwę atrybutu albo relacji,
- `SourceSystem_ID`,
- `Source_Record_ID`,
- `ImportBatch_ID`,
- `Selection_Rule`,
- `Trust_Score`,
- `Quality_Score`,
- `Validation_Status`,
- `Recorded_At`.

W praktyce oznacza to, że dla bieżącej wartości można ustalić nie tylko źródło, lecz także podstawę wyboru, na przykład:

- `NON_EMPTY_VALUE`,
- `PASSED_VALIDATION`,
- `TERYT_CONFIRMED_ADDRESS`,
- `SOURCE_PRIORITY`,
- `TRUST_LEVEL`,
- `NEWEST_IMPORT`,
- `INPUT_ORDER_FALLBACK`.

## 16.5. Lineage osób, podmiotów i adresów

Lineage atrybutów wymiarów jest zapisywane funkcją `write_dimension_lineage()`. Mechanizm działa po utworzeniu albo aktualizacji:

- `gold.DimPerson`,
- `gold.DimParty`,
- `gold.DimAddress`,
- `gold.FactlessPartyIdentities`.

Dla każdego atrybutu, który otrzymał niepustą wartość i dla którego dostępne są dane źródłowe, zapisywany jest osobny wpis lineage.

Przykładowo można ustalić:

- z którego źródła pochodzi imię osoby,
- z której partii importu pochodzi nazwa podmiotu,
- które źródło dostarczyło zwycięski kod pocztowy,
- z jakiego materiału pochodzi zapisany numer LEI.

Lineage adresu jest zapisywane osobno od lineage osoby albo podmiotu. Oznacza to, że adres jako obiekt `DimAddress` posiada własne pochodzenie swoich atrybutów, niezależne od tego, z kim został później powiązany.

## 16.6. Lineage relacji adresowych

Oprócz lineage samych wymiarów system zapisuje lineage relacji adresowych:

- `PersonAddressLineage` dla relacji osoby z adresem,
- `PartyAddressLineage` dla relacji podmiotu z adresem.

Nie jest to kopia całego zestawu pól adresowych. Implementacja wybiera jeden reprezentatywny wybór źródła dla relacji, zgodnie z priorytetem:

1. `Full_Address`,
2. `Street`,
3. `City`,
4. `Postal_Code`,
5. `Building_Number`,
6. `Apartment_Number`,
7. `Postal_City`,
8. `District`,
9. `Province`,
10. `Country`.

Na tej podstawie system zapisuje, z którego źródła i importu pochodzi utworzenie albo aktualizacja konkretnego powiązania adresowego. Reguła wyboru jest dodatkowo oznaczana prefiksem `ADDRESS_LINK_FROM_...`.

## 16.7. Wykorzystanie walidacji w lineage

Warstwa goldenizacji nie zapisuje do lineage surowego wyniku wszystkich reguł walidacyjnych. Zamiast tego:

- pobiera zagregowany status dla pola,
- przekształca go do uproszczonego `Validation_Status`,
- wylicza uproszczony `Quality_Score`.

Agregacja działa następująco:

- jeżeli dla pola wystąpi `ERROR`, wynik pola jest `ERROR`,
- w przeciwnym razie `WARNING` ma pierwszeństwo nad `PASS`,
- przy braku problemów wynik to `PASS`.

`Quality_Score` jest następnie redukowany do prostego sygnału:

- `1.0` dla wartości uznanej za poprawną,
- `0.0` dla wartości niepoprawnej.

Mechanizm ten wzmacnia użyteczność lineage, ale nie zastępuje pełnego wglądu w tabelę `stg.Validation_Result`.

## 16.8. Rejestr zmian wymiarów

Zmiany atrybutów są zapisywane w tabeli `gold.EntityChangeLog`. Rekord zmiany zawiera:

- typ encji,
- odniesienie do zmienionego obiektu,
- nazwę atrybutu,
- starą wartość,
- nową wartość,
- datę zmiany,
- opcjonalny `ImportBatch_ID`.

Model przewiduje obsługę zmian dla typów:

- `PERSON`,
- `PARTY`,
- `ADDRESS`,
- `PARTY_IDENTITY`.

W aktualnej logice warstwy `integration_golden` rejestr zmian jest wykorzystywany bezpośrednio przy aktualizacji:

- `DimPerson`,
- `DimParty`.

Jeżeli nowa wartość atrybutu różni się od poprzedniej, funkcja `record_dimension_changes()` zapisuje wpis z poprzednią i nową wartością. Gdy wartości są równoważne, zmiana nie jest dopisywana.

## 16.9. Co dokładnie daje historia zmian

Rejestr zmian pozwala odpowiedzieć na pytania typu:

- która wartość atrybutu osoby została zmieniona,
- jaka była poprzednia i nowa wartość,
- przy której partii importu nastąpiła zmiana,
- kiedy ta zmiana została zapisana.

Jest to więc historia ewolucji pól wymiaru, a nie pełna migawka całego rekordu po każdym przebiegu procesu. System nie zapisuje kompletnej wersji encji po każdym imporcie.

## 16.10. Ograniczenia historii lineage i zmian

Najważniejsze ograniczenia są następujące:

- wpis lineage dla danego atrybutu reprezentuje aktualne pochodzenie, a nie pełną sekwencję wcześniejszych źródeł tego samego atrybutu,
- przy ponownym zapisie lineage dla tego samego obiektu i atrybutu wcześniejszy wpis jest zastępowany nowym,
- `EntityChangeLog` przechowuje zmianę wartości, ale nie przechowuje pełnej logiki wyboru wszystkich kandydatów rozważanych w survivorship,
- aktualna warstwa zapisuje historię zmian bezpośrednio dla osób i podmiotów; model dopuszcza więcej typów encji, lecz nie wszystkie są obecnie materializowane w analogicznym zakresie,
- logi techniczne procesu nie są pełnym dziennikiem wszystkich decyzji matchingowych.

W praktyce oznacza to, że system dobrze pokazuje:

- skąd pochodzi aktualna wartość,
- jak zmieniała się wartość atrybutu,
- kiedy i w jakiej partii zaszła zmiana.

Nie pozwala natomiast odtworzyć kompletnego, historycznego obrazu wszystkich wcześniejszych wariantów lineage dla tego samego atrybutu.

## 16.11. Przykłady informacji możliwych do odtworzenia

Na podstawie aktualnych struktur można ustalić między innymi:

- z którego systemu źródłowego pochodzi bieżące imię osoby GOLD,
- która partia importu dostarczyła aktualny numer REGON podmiotu,
- czy zwycięski adres był wybrany dzięki priorytetowi źródła czy dzięki potwierdzeniu w TERYT,
- jakie było poprzednie nazwisko albo poprzednia nazwa podmiotu,
- kiedy utworzono lub zaktualizowano relację osoby z adresem.

Takie informacje są wystarczające do audytu bieżącego wyniku oraz do prześledzenia najważniejszych zmian biznesowych, ale nie zastępują pełnego mechanizmu temporalnego.

## 16.12. Wykorzystanie przez warstwę serving

Zapisane dane audytowe nie pozostają wyłącznie wewnętrznym artefaktem warstwy GOLD. Zgodnie z zakresem projektu są później udostępniane przez warstwę `serving`, która potrafi zwrócić między innymi:

- lineage wybranych rekordów GOLD,
- historię zmian,
- wyniki walidacji powiązane z rekordami.

Oznacza to, że audytowalność nie jest wyłącznie cechą bazy danych, ale także częścią interfejsu odczytowego systemu.

## 16.13. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `app/layers/ingestion/models.py` - model `ProcessLog`,
- `app/layers/integration_golden/models.py` - `EntityChangeLog` oraz tabele lineage,
- `app/layers/integration_golden/repository.py` - zapis i aktualizacja lineage, zapis historii zmian, log `GOLDEN_LOAD`,
- `app/layers/integration_golden/service.py` - logika wyboru wpisów lineage, zapis zmian i wykorzystanie statusów walidacji,
- `app/layers/validation/models.py` - wyniki walidacji używane do budowy jakości pola,
- `tests/test_integration_golden_dimensions.py` - testy lineage, zmian atrybutów i relacji adresowych,
- `tests/test_integration_golden_load.py` - testy logowania `GOLDEN_LOAD`,
- `scripts/init_proposed_mssql_schema.sql` - definicje tabel i indeksów dla `ProcessLog`, `EntityChangeLog` i tabel lineage.
