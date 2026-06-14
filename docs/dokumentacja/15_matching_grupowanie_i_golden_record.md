# 15. Matching, grupowanie i budowa Golden Record

Warstwa `integration_golden` odpowiada za rozpoznawanie rekordów opisujących tę samą osobę albo ten sam podmiot, budowę stabilnych grup encji oraz materializację wynikowych rekordów w schemacie `gold`. Jest to etap, w którym kończy się przetwarzanie porównawcze, a rozpoczyna utrwalanie wspólnej reprezentacji danych.

Implementacja rozdziela ten obszar na cztery kroki:

1. wyszukanie kandydatów metodą Levenshteina,
2. ponowną ocenę kandydatów metodą Jaro-Winklera,
3. grupowanie par `AUTO_MERGE`,
4. utworzenie albo aktualizację rekordów GOLD.

## 15.1. Uruchamianie procesu

Warstwa udostępnia cztery endpointy:

```text
POST /layers/integration_golden/match-candidates
POST /layers/integration_golden/match-candidates/jaro-winkler
POST /layers/integration_golden/match-groups
POST /layers/integration_golden/golden-load
```

Zakres parametrów:

- `entity_type` przyjmuje `PERSON` albo `PARTY`,
- `raw_file_id` zawęża matching albo ładowanie GOLD do wskazanego materiału,
- `min_score` pozwala sterować progiem kandydata w obu etapach matchingu,
- `max_pairs` ogranicza liczbę porównań w etapie Levenshteina,
- `entity_group_id` pozwala uruchomić materializację GOLD dla jednej grupy.

Matching wymaga wcześniejszego przygotowania rekordów `preprocessed`. Grupowanie wymaga zapisanych wyników Jaro-Winklera. Materializacja GOLD wymaga istnienia grup encji.

## 15.2. Model reguł dopasowania

Matching jest regułowy. Każde pole używane do porównania ma:

- wagę,
- rolę,
- sposób porównania,
- listę aliasów odczytu z rekordu preprocessed,
- opcjonalny status pola rozstrzygającego.

W implementacji używane są role:

- `STRONG` - silne identyfikatory,
- `FIXED` - pola oczekiwane jako zgodne,
- `SEMI_FIXED` - pola zwykle stabilne, ale dopuszczające rozbieżności,
- `DYNAMIC` - pola kontaktowe i adresowe,
- `CONTEXT` - pola pomocnicze, kontekstowe.

### Reguły dla osoby

Najwyższą wagę mają identyfikatory i pola tożsamości:

- `PESEL`,
- numer dowodu,
- numer paszportu,
- data urodzenia,
- imię i nazwisko,
- pełne imię i nazwisko,
- miejsce urodzenia.

Niższą wagę mają pola dynamiczne, takie jak:

- telefon,
- e-mail,
- adres,
- kod pocztowy,
- województwo.

Testy potwierdzają między innymi, że zgodny PESEL pozwala na automatyczne scalenie mimo zmian danych dynamicznych, natomiast konflikt wielu pól stabilnych obniża wynik do `CANDIDATE` albo `NO_MATCH`.

### Reguły dla podmiotu

Najsilniejsze identyfikatory to:

- `NIP`,
- `REGON`,
- `KRS`,
- `LEI`,
- w wybranych źródłach także numer decyzji i numer rejestrowy.

Dużą wagę mają również:

- nazwa,
- data utworzenia,
- nazwy i relacje podmiotów dominujących,
- wybrane pola rejestrowe i statusowe.

Pola adresowe, kontaktowe i kontekstowe wpływają na wynik, ale nie mają siły samodzielnego rozstrzygnięcia. Dzięki temu podobne adresy lub wspólne cechy branżowe nie powodują automatycznego scalenia niepowiązanych podmiotów.

## 15.3. Etap Levenshteina

Pierwszy etap matchingu wykorzystuje funkcję `score_match()`, która dla każdej pary rekordów:

1. odczytuje wartości pól zdefiniowanych w regułach,
2. liczy podobieństwo Levenshteina,
3. mnoży wynik przez wagę pola,
4. buduje łączny wynik ważony,
5. rejestruje zgodne pola silne oraz pola konfliktowe.

Domyślne progi etapu są następujące:

- próg wejścia kandydata: `0.50`,
- próg `REVIEW`: `0.70`,
- próg `AUTO_MERGE`: `0.90`,
- dodatkowy próg `0.95` dla bardzo wysokiego podobieństwa bez krytycznych konfliktów.

Wynik klasyfikowany jest do jednej z decyzji:

- `AUTO_MERGE`,
- `REVIEW`,
- `CANDIDATE`,
- `NO_MATCH`.

Sama zgodność silnego identyfikatora nie wystarcza zawsze do `AUTO_MERGE`. Jeżeli równocześnie wystąpią konflikty pól stabilnych, wynik może zostać obniżony do `CANDIDATE` albo `NO_MATCH`. Implementacja traktuje krytycznie zwłaszcza konflikty identyfikatorów takich jak PESEL, NIP, REGON, KRS, numer dowodu i numer paszportu.

Etap zapisuje wyniki do tabeli `stg.Match_Candidate_Levenshtein`. W tabeli pozostają tylko kandydaci, którzy przekroczyli minimalny próg i nie zostali sklasyfikowani jako `NO_MATCH`.

## 15.4. Ograniczenie liczby porównań

Aby uniknąć niekontrolowanego wzrostu liczby porównań, etap Levenshteina posiada limit bezpieczeństwa `matching_max_pairs`. Domyślna wartość to `2_000_000`.

Po przekroczeniu limitu serwis zwraca błąd wejściowy. Jest to zabezpieczenie techniczne, a nie reguła biznesowa. W razie potrzeby limit można zwiększyć albo wyłączyć przez ustawienie `0`.

## 15.5. Etap Jaro-Winklera

Drugi etap nie przegląda całego zbioru rekordów od nowa. Ocenia wyłącznie kandydatów zapisanych po etapie Levenshteina.

Funkcja `score_jaro_winkler_match()`:

- koncentruje się na polach tekstowych,
- zachowuje informację o silnych polach i wcześniejszych konfliktach,
- ponownie ocenia podobieństwo nazw, nazwisk, miejsc urodzenia, adresów i wybranych pól opisowych.

Domyślne progi tego etapu są wyższe:

- próg kandydata: `0.78`,
- próg `REVIEW`: `0.86`,
- próg `AUTO_MERGE`: `0.94`.

Wyniki są zapisywane do `stg.Match_Candidate_JaroWinkler`. Jeżeli kandydat nie spełnia progu i nie ma silnych podstaw do dalszej analizy, jest odrzucany na tym etapie.

## 15.6. Znaczenie decyzji matchingowych

Decyzje są interpretowane następująco:

- `AUTO_MERGE` - para może zostać użyta do budowy wspólnej grupy encji,
- `REVIEW` - para jest podobna, ale wymagałaby oceny ręcznej,
- `CANDIDATE` - para została wykryta jako potencjalnie interesująca, lecz nie spełnia warunków połączenia,
- `NO_MATCH` - para nie powinna być dalej brana pod uwagę.

Aktualna implementacja wykorzystuje automatycznie tylko pary `AUTO_MERGE`. Przypadki `REVIEW` są zachowywane w wynikach matchingu, ale system nie zawiera pełnego procesu ręcznej obsługi takich decyzji.

## 15.7. Grupowanie rekordów

Grupowanie opiera się na parach `AUTO_MERGE` po etapie Jaro-Winklera. Funkcja `build_entity_groups()` buduje spójne składowe grafu rekordów przy użyciu algorytmu typu union-find.

W praktyce oznacza to, że:

- jeżeli rekord A łączy się z B,
- a rekord B łączy się z C,
- to wszystkie trzy rekordy trafiają do jednej grupy, nawet jeśli para A-C nie była oceniana bezpośrednio jako niezależny przypadek połączenia.

Każda grupa otrzymuje stabilny `Group_Key`, wyliczony jako SHA-256 z uporządkowanej listy identyfikatorów `Preprocessed_ID`.

Po zbudowaniu grup wieloelementowych funkcja `add_singleton_entity_groups()` dopisuje również rekordy niepołączone z żadnym innym rekordem. Dzięki temu każda encja preprocessed należy do dokładnie jednej grupy:

- grupy scalonej,
- albo grupy jednoelementowej.

Wynik grupowania jest zapisywany w tabelach:

- `stg.Entity_Group`,
- `stg.Entity_Group_Member`.

Ponowne uruchomienie grupowania zastępuje aktualne członkostwa grup dla danego typu encji na podstawie bieżących kandydatów `AUTO_MERGE`.

## 15.8. Budowa Golden Record osoby

Materializacja osoby odbywa się funkcją `create_or_update_golden_person()`. Dla wskazanej grupy serwis:

1. pobiera wszystkich członków grupy i odpowiadające im rekordy `preprocessed`,
2. wybiera wartości przeżywające dla pól osoby,
3. wyszukuje istniejącą osobę po identyfikatorach tożsamości,
4. tworzy nowy rekord `gold.DimPerson` albo aktualizuje istniejący,
5. buduje lub ponownie wykorzystuje adres,
6. zakłada albo ponownie wykorzystuje powiązanie osoby z adresem.

Tożsamość osoby jest wyszukiwana po:

- `PESEL`,
- numerze dowodu osobistego,
- numerze paszportu.

Jeżeli rekord już istnieje, aktualizacja nie tworzy nowej osoby, tylko nadpisuje wartości bieżące i zapisuje zmiany atrybutów.

## 15.9. Budowa Golden Record podmiotu

Materializacja podmiotu działa analogicznie, ale z uwzględnieniem szerszego zestawu identyfikatorów. Funkcja `create_or_update_golden_party()`:

1. buduje wartości przeżywające dla atrybutów podmiotu,
2. wyszukuje istniejący rekord po `NIP`, `REGON`, `KRS` i `LEI`,
3. tworzy albo aktualizuje `gold.DimParty`,
4. tworzy albo ponownie wykorzystuje adres rejestrowy,
5. zapisuje powiązanie podmiotu z adresem,
6. zapisuje identyfikatory podmiotu jako osobne rekordy faktless.

Dla podmiotu utrwalane mogą być między innymi:

- `NIP`,
- `REGON`,
- `KRS`,
- `LEI`,
- numer rejestrowy KNF,
- numer decyzji.

Liczba zapisanych identyfikatorów zależy od danych dostępnych w zwycięskich wartościach grupy.

## 15.10. Reguły survivorship

Wybór wartości końcowej dla atrybutu realizuje funkcja `select_survivor_value()`. Kolejność kryteriów jest stała:

1. obecność niepustej wartości,
2. pozytywny wynik walidacji,
3. potwierdzenie adresu w TERYT dla pól adresowych,
4. priorytet źródła dla danego atrybutu,
5. poziom zaufania źródła,
6. czas rozpoczęcia importu,
7. kolejność wejściowa jako awaryjny tie-break.

Źródła mają różne priorytety zależnie od encji i pola. Przykładowo:

- dla danych tożsamości osoby preferowany jest `PESEL`,
- dla kontaktu osoby preferowane są `CEIDG` i `INSURANCE_CORE`,
- dla adresów podmiotu wysokie priorytety mają `REGON`, `VAT`, `CEIDG` i `KRS`,
- dla pola `LEI` preferowane jest źródło `GLEIF`.

Dobór wartości nie jest więc jednym globalnym rankingiem źródeł, tylko zestawem reguł zależnych od atrybutu.

## 15.11. Adresy i powiązania adresowe

Adres GOLD jest budowany osobno od rekordu osoby lub podmiotu. Funkcja `create_golden_address_for_records()`:

- wybiera zwycięskie pola adresowe,
- sprawdza, czy taki adres już istnieje,
- tworzy nowy rekord `gold.DimAddress` albo ponownie używa istniejącego.

Powiązanie z adresem również nie jest bezwarunkowo tworzone od nowa. Funkcja `ensure_golden_address_link()`:

- dla osoby używa typu adresu `RESIDENCE`,
- dla podmiotu używa typu `REGISTERED`,
- może pozostawić istniejące aktywne powiązanie,
- może zamknąć wcześniejsze aktywne powiązanie przez ustawienie `Valid_To`,
- może utworzyć nowe aktywne powiązanie z `Valid_From`.

Dzięki temu zmiana adresu nie niszczy wprost poprzedniego powiązania, lecz kończy jego obowiązywanie i zapisuje nowe.

## 15.12. Odrzucanie grup

Nie każda grupa prowadzi do powstania Golden Record. Aktualna implementacja zawiera jawny mechanizm odrzucenia grupy podmiotu, jeżeli po zastosowaniu reguł survivorship nie da się wyznaczyć wymaganych pól.

Obecnie dla `PARTY` polem wymaganym jest:

- `Name`.

Jeżeli nazwa pozostaje pusta, serwis:

- nie tworzy rekordu `DimParty`,
- zapisuje odrzucenie w `stg.Golden_Record_Reject`,
- zwraca informację o brakujących polach i identyfikatorach członków grupy.

Mechanizm ten służy do zachowania pełnej ścieżki technicznej również dla przypadków, w których rekord wynikowy nie może zostać utworzony poprawnie.

## 15.13. Transakcyjność etapu GOLD

Ładowanie GOLD nie jest realizowane jako jedna wspólna transakcja dla wszystkich grup objętych wywołaniem. Implementacja przetwarza grupy kolejno i zatwierdza zapis po wykonaniu logiki dla konkretnej grupy.

Oznacza to, że:

- część grup może zostać poprawnie utrwalona jeszcze przed wystąpieniem błędu,
- awaria późniejszej grupy nie usuwa wcześniej zapisanych wyników,
- ponowne uruchomienie opiera się na logice create-or-update.

Taki model ogranicza ryzyko pełnej utraty postępu przy dłuższym przebiegu, ale oznacza też brak atomowości dla całego wywołania `golden-load`.

## 15.14. Ograniczenia

Najważniejsze ograniczenia obecnej implementacji to:

- tylko decyzje `AUTO_MERGE` wpływają na grupowanie i budowę GOLD,
- brak pełnego procesu ręcznej obsługi przypadków `REVIEW`,
- grupowanie działa dla całego typu encji, a nie dla pojedynczego `RawFile_ID`,
- lineage przechowuje stan aktualnie wybranych wartości, a nie pełną historię kolejnych wersji wyboru,
- odrzucenie grup wprost zaimplementowano obecnie dla wymaganego pola nazwy podmiotu,
- budowa GOLD wykonuje zapis etapami dla kolejnych grup, a nie jako jedną transakcję globalną.

Ograniczenia te nie zmieniają faktu, że rdzeń automatycznego matchingu, grupowania i materializacji Golden Record działa w obecnym kodzie end-to-end.

## 15.15. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `app/layers/integration_golden/api.py` - endpointy matchingu, grupowania i ładowania GOLD,
- `app/layers/integration_golden/service.py` - scoring, klasyfikacja, grupowanie, survivorship i materializacja wymiarów,
- `app/layers/integration_golden/repository.py` - operacje odczytu i zapisu w schemacie `stg` i `gold`,
- `app/layers/integration_golden/models.py` - modele kandydatów, grup, odrzuceń i wymiarów GOLD,
- `app/layers/integration_golden/schemas.py` - modele odpowiedzi API,
- `tests/test_integration_golden_matching.py` - testy reguł matchingu, progów i survivorship,
- `tests/test_integration_golden_dimensions.py` - testy budowy rekordów GOLD i aktualizacji wymiarów,
- `tests/test_integration_golden_load.py` - testy przebiegu `golden_load`, odrzuceń i logiki grup,
- `tests/test_integration_golden_repository.py` - testy podstawowych operacji repozytorium,
- `scripts/init_proposed_mssql_schema.sql` - definicje tabel dla kandydatów, grup i wymiarów.
