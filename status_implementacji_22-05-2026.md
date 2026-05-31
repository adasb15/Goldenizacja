# Status implementacji - 22.05.2026

## Zakres aktualizacji względem 17.05.2026

Od poprzedniego statusu główne prace dotyczyły dodania nowego typu źródła danych: relacyjnej bazy Oracle. Projekt nie opiera się już wyłącznie na plikach wsadowych. Aktualny `main` zawiera mechanizm pobierania danych z zewnętrznego systemu relacyjnego, zapisania ich do RAW jako migawki JSON, a następnie przetworzenia przez istniejące warstwy staging, preprocessing i validation.

Drugim istotnym obszarem były poprawki walidacji danych oraz dopracowanie danych testowych tak, aby lepiej odzwierciedlały realne problemy: relacje między tabelami, nadmiarowe kolumny, niejednoznaczne nazwy pól, wartości `NULL`, literówki, polskie znaki i częściowo niespójne identyfikatory.

## Najważniejsze zmiany

| Obszar | Status |
| --- | --- |
| Dodanie Oracle jako źródła relacyjnego | Zrobione |
| Utworzenie przykładowego systemu `INSURANCE_CORE` w Oracle | Zrobione |
| Import danych relacyjnych do RAW jako dokument JSON | Zrobione |
| Eksport danych `PARTY` z Oracle | Zrobione |
| Eksport danych `PERSON` z Oracle | Zrobione |
| Wspólna nazwa zapytania `insurance_core_export` z wyborem `entity_type` | Zrobione |
| Tryb Airflow `RELATIONAL` dla Oracle | Zrobione |
| Tryb `AUTO` w Airflow uruchamiający osobno `PARTY` i `PERSON` dla Oracle | Zrobione |
| Mapowanie Oracle do stagingu dla `PARTY` | Zrobione |
| Mapowanie Oracle do stagingu dla `PERSON` | Zrobione |
| Normalizacja kodów form prawnych Oracle w preprocessingu | Zrobione |
| Rozszerzenie walidacji zakresów dat dla podmiotów | Zrobione |
| Testy dla importu relacyjnego, mapowania Oracle i preprocessingu | Zrobione |

## Źródło relacyjne Oracle

Dodano lokalny kontener Oracle do środowiska Docker Compose. Oracle pełni rolę zewnętrznego systemu źródłowego, z którego dane są pobierane relacyjnie, a nie przez upload pliku.

W środowisku działa przykładowy schemat:

```text
INSURANCE_CORE
```

Ten schemat celowo nie jest kopią docelowego modelu golden records. Ma udawać obcy system operacyjny, w którym:

- dane są rozbite na wiele tabel,
- nazwy kolumn nie odpowiadają bezpośrednio nazwom stagingu,
- występują kolumny nadmiarowe,
- część danych jest pusta albo jakościowo słabsza,
- część nazw i adresów zawiera polskie znaki,
- część rekordów koreluje z danymi plikowymi, ale nie jest identyczna.

Do konfiguracji projektu dodano parametry połączenia z Oracle oraz zależność `oracledb`. Kod importu wspiera połączenie przez `python-oracledb`, a opcjonalnie może użyć connection stringa ODBC, jeśli zostanie podany w konfiguracji.

## Model danych w Oracle

W Oracle dodano przykładowy system `INSURANCE_CORE` z tabelami:

- `ORG_UNIT` - jednostki organizacyjne i regiony obsługi
- `CLIENT_ACCOUNT` - główna tabela klientów, zawiera zarówno podmioty, jak i osoby
- `CUSTOMER_IDENTIFIER` - identyfikatory typu NIP, REGON, KRS
- `CUSTOMER_ADDRESS` - adresy klientów
- `CLIENT_CONTACT_LOG` - emaile i telefony
- `PAYMENT_ACCOUNT` - rachunki bankowe
- `CONTRACT` - umowy/polisy
- `CONTRACT_PARTY` - relacja klientów z umowami
- `AGENT_ASSIGNMENT` - osoby powiązane z podmiotami
- `RELATED_CLIENT` - relacje między klientami/podmiotami

Taki układ pozwala pokazać, że projekt potrafi przyjąć dane nie tylko z płaskich plików, ale również z relacyjnego źródła, w którym dane trzeba zebrać przez zapytania i połączenia między tabelami.

## Import relacyjny do RAW

Dodano endpoint:

```text
POST /layers/ingestion/relational-load
```

Endpoint przyjmuje:

```text
source_system_code = INSURANCE_CORE
query_name = insurance_core_export
entity_type = PARTY albo PERSON
```

Dane pobrane z Oracle nie trafiają bezpośrednio do stagingu. Najpierw są serializowane do JSON i zapisywane w RAW jako plik logiczny, np.:

```text
insurance_core_party_export.json
insurance_core_person_export.json
```

Dzięki temu zachowana jest ta sama zasada audytowalności, co przy plikach:

- powstaje `ImportBatch`,
- powstaje `RawFile`,
- zapisywany jest hash i rozmiar danych,
- kolejne warstwy pracują na `RawFile_ID`,
- staging i preprocessing można odtworzyć bez ponownego pobierania z Oracle.

## Eksport PARTY z Oracle

Dla podmiotów zapytanie pobiera dane z kilku tabel Oracle i składa jeden rekord źródłowy dla stagingu.

Wykorzystywane są między innymi:

- `CLIENT_ACCOUNT` jako główna tabela podmiotów,
- `CUSTOMER_IDENTIFIER` dla NIP, REGON i KRS,
- `CUSTOMER_ADDRESS` dla adresu,
- `CLIENT_CONTACT_LOG` dla emaila i telefonu,
- `PAYMENT_ACCOUNT` dla rachunku bankowego,
- `CONTRACT_PARTY` i `CONTRACT` dla informacji o aktywnych umowach,
- `AGENT_ASSIGNMENT` dla osób powiązanych z podmiotem,
- `RELATED_CLIENT` dla relacji między podmiotami.

Dane osób powiązanych z podmiotem są dołączane jako:

```text
RELATED_PERSONS_JSON
```

Dane relacji między podmiotami są dołączane jako:

```text
RELATED_PARTIES_JSON
```

Pozwala to przenieść z relacyjnego źródła informacje, które nie mieszczą się w prostych kolumnach stagingu.

## Eksport PERSON z Oracle

Dodano osobny eksport osób z Oracle.

Dane `PERSON` są pobierane z dwóch źródeł w ramach systemu Oracle:

- z `AGENT_ASSIGNMENT`, czyli osób pełniących role przy podmiotach,
- z rekordów `CLIENT_ACCOUNT`, które mają `SUBJECT_KIND = 'PERSON'`.

Dzięki temu Oracle może dostarczać zarówno podmioty, jak i osoby, a pipeline może przetworzyć oba typy encji w jednym przebiegu Airflow.

## Ujednolicenie `query_name` i `entity_type`

Wprowadzono jedną publiczną nazwę zapytania:

```text
insurance_core_export
```

Zakres danych jest wybierany przez:

```text
entity_type = PARTY
entity_type = PERSON
```

Wewnętrznie aplikacja mapuje to na właściwe zapytanie:

```text
insurance_core_party_export
insurance_core_person_export
```

To upraszcza użycie API i Airflow. Użytkownik nie musi pamiętać dwóch różnych nazw zapytań, tylko wybiera typ encji.

## Obsługa Oracle w Airflow

Pipeline Airflow został rozszerzony o tryb:

```text
input_type = RELATIONAL
```

Dla tego trybu domyślnym źródłem jest:

```text
INSURANCE_CORE
```

a domyślną nazwą zapytania:

```text
insurance_core_export
```

Jeżeli `entity_type = AUTO`, Airflow uruchamia import relacyjny dwa razy:

```text
PARTY
PERSON
```

Każdy typ encji dostaje własny `RawFile_ID`, a kolejne kroki pipeline korzystają z odpowiedniego identyfikatora dla danego typu danych. Dzięki temu nie miesza się staging podmiotów ze stagingiem osób.

## Mapowanie Oracle do stagingu

Dodano mapowanie kolumn dla źródła:

```text
INSURANCE_CORE
```

Dla `PARTY` mapowane są między innymi:

- `EXT_REF_NO` -> `Source_Record_ID`
- `PARTY_LABEL` -> `Name`
- `BRAND_LABEL` -> `Short_Name`
- `FORM_CD` -> `Legal_Entity_Type`
- `TAX_REF`, `STAT_REG_REF`, `COURT_REF` -> `Identifiers_JSON`
- `ADDR_TXT` -> `Street`
- `MUNICIPAL_UNIT` -> `City`
- `POST_AREA` -> `Postal_Code`
- `MAILBOX` -> `Email_Address`
- `TEL_NOTE` -> `Phone_Number`
- `SETTLEMENT_ACC` -> `Bank_Accounts_JSON`
- `RELATED_PERSONS_JSON` -> `Related_Persons_JSON`
- `RELATED_PARTIES_JSON` -> `Related_Parties_JSON`

Dla `PERSON` mapowane są między innymi:

- `PERSON_REF` -> `Source_Record_ID`
- `NATIONAL_REF` -> `PESEL`
- `GIVEN_TXT` -> `First_Name`
- `SECOND_GIVEN_TXT` -> `Second_Name`
- `FAMILY_TXT` -> `Last_Name`
- `BIRTH_DT_HINT` -> `Birth_Date`
- `BIRTH_PLACE_HINT` -> `Place_Of_Birth`
- `GENDER_HINT` -> `Sex`
- `MAILBOX` -> `Email_Address`
- `TEL_NOTE` -> `Phone_Number`
- `ADDR_TXT` -> `Street`
- `MUNICIPAL_UNIT` -> `City`
- `POST_AREA` -> `Postal_Code`

Mapowanie jest nadal jawne i kontrolowane w `meta.ColumnMapping`. Nie jest to jeszcze automatyczne rozpoznawanie znaczenia kolumn, ale obecny mechanizm pozwala obsłużyć obcy system relacyjny bez zmiany modelu stagingu.

## Preprocessing po zmianach

Preprocessing został rozszerzony o obsługę technicznych kodów form prawnych z Oracle.

Przykłady:

```text
LLC_PL -> SP. Z O.O.
JSC_PL -> S.A.
```

Dzięki temu wartości techniczne ze źródła relacyjnego nie trafiają dalej jako osobne formy prawne. Są sprowadzane do tego samego słownika pojęć, który jest używany dla danych z plików.

Preprocessing nadal wykonuje rozbijanie adresów i normalizację wartości przeznaczonych do porównywania, bez niszczenia danych źródłowych zapisanych w stagingu i RAW.

## Poprawki walidacji

Po statusie z 17.05 dodano walidacje zakresów dat dla podmiotów.

Sprawdzane są między innymi:

- data powstania względem daty wykreślenia,
- data rejestracji względem daty wyrejestrowania,
- data kolejnego odnowienia względem daty ostatniej aktualizacji,
- daty obowiązywania relacji do podmiotu nadrzędnego,
- daty obowiązywania relacji do podmiotu ultimate parent.

Dodane kody błędów obejmują między innymi:

```text
ERR_ESTABLISHMENT_AFTER_DEREGISTRATION
ERR_REGISTRATION_AFTER_DEREGISTRATION
ERR_NEXT_RENEWAL_BEFORE_LAST_UPDATE
ERR_DIRECT_PARENT_RELATIONSHIP_START_AFTER_END
ERR_ULTIMATE_PARENT_RELATIONSHIP_START_AFTER_END
```

Reguły nie przerywają przetwarzania danych. Błędne rekordy są oznaczane wynikiem walidacji i opisem błędu.

## Dane testowe

Dane testowe zostały rozszerzone pod kątem źródła relacyjnego.

W Oracle znajdują się dane:

- częściowo zgodne z rekordami z plików,
- częściowo nowe, bez odpowiednika w plikach,
- z celowymi błędami identyfikatorów,
- z brakującymi wartościami,
- z relacjami między podmiotami,
- z osobami powiązanymi z podmiotami,
- z polskimi znakami w nazwach, adresach, miastach i nazwiskach.

Celem tych danych jest sprawdzenie, czy system radzi sobie z realniejszym scenariuszem niż pojedynczy płaski plik.

## Testy

Sprawdzony zestaw testów:

```text
python3 -m unittest tests.test_relational_ingestion tests.test_staging_mapper tests.test_preprocessing tests.test_validation -v
```

Wynik:

```text
56/56 tests OK
```

Testy obejmują obecnie:

- import relacyjny Oracle do RAW,
- wybór `PARTY` i `PERSON` przez `entity_type`,
- odrzucenie błędnego źródła albo błędnego zapytania,
- składanie `RELATED_PERSONS_JSON` i `RELATED_PARTIES_JSON`,
- mapowanie rekordów Oracle do stagingu,
- mapowanie identyfikatorów Oracle do `Identifiers_JSON`,
- preprocessing kodów form prawnych Oracle,
- rozbijanie adresów w preprocessingu,
- walidację identyfikatorów,
- walidację emaili,
- walidację PESEL,
- walidację zakresów dat dla `PARTY`.

## Aktualny stan na 22.05.2026

Aktualnie projekt obsługuje dwa typy wejścia:

- pliki wsadowe w formatach CSV, JSON, XML i XLSX,
- relacyjne źródło Oracle `INSURANCE_CORE`.

Dane z obu typów źródeł są sprowadzane do wspólnej ścieżki:

```text
RAW -> staging -> preprocessing -> validation
```

Najważniejszy postęp względem 17.05.2026 to dodanie realnego scenariusza integracji z bazą relacyjną. System potrafi pobrać dane z Oracle, zapisać je jako audytowalny snapshot w RAW, zmapować do wspólnego stagingu i przetworzyć dalej tymi samymi mechanizmami, które działają dla plików.
