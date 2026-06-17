# 17. Interfejs użytkownika

Frontend jest osobną aplikacją React, która komunikuje się z backendem przez HTTP i korzysta z odczytowych endpointów warstwy `serving`. W aktualnej wersji nie służy do uruchamiania pipeline'u ani do ręcznego zatwierdzania decyzji integracyjnych. Jego zadaniem jest prezentacja wybranych wyników procesu w czytelnej formie tabelarycznej.

W praktyce frontend pełni rolę lekkiej konsoli odczytowej dla trzech obszarów:

1. listy i szczegółów Golden Record,
2. wyników walidacji,
3. wyników matchingu.

## 17.1. Technologia i sposób uruchomienia

Interfejs został wykonany w:

- React 18,
- Vite,
- JavaScript z modułami ES.

Skrypt `dev` uruchamia środowisko developerskie Vite, `build` przygotowuje produkcyjny bundle, a `preview` wystawia zbudowaną aplikację na porcie `4173`.

Kod wejściowy znajduje się w:

- `frontend/src/main.jsx`,
- `frontend/src/App.jsx`.

W `main.jsx` aplikacja jest montowana przez `ReactDOM.createRoot(...)`, a style ładowane są z `frontend/src/styles/index.css`.

## 17.2. Struktura aplikacji

W kodzie widoczny jest prosty podział na warstwy frontendowe:

- `api/` - komunikacja z backendem,
- `features/` - widoki funkcjonalne,
- `components/ui/` - małe komponenty wielokrotnego użytku,
- `constants/` - stałe widoków i filtrowania,
- `utils/` - formatowanie i funkcje pomocnicze,
- `styles/` - podział arkuszy CSS według obszarów interfejsu.

Aktualna struktura nie korzysta z globalnego store ani routingu URL. Nawigacja pomiędzy widokami jest obsługiwana lokalnym stanem komponentu `App`.

## 17.3. Komunikacja z backendem

Komunikacja z API została wydzielona do pliku:

- `frontend/src/api/serving.js`.

Warstwa ta:

- pobiera bazowy adres API z `VITE_API_URL`,
- domyślnie używa `http://localhost:8000`,
- buduje parametry zapytania na podstawie obiektu filtrów,
- wykonuje `fetch`,
- próbuje odczytać `detail` albo `message` z odpowiedzi błędu,
- zwraca zdeserializowany JSON.

Frontend korzysta obecnie z funkcji:

- `getGoldenRecords(...)`,
- `getPersonDetail(...)`,
- `getPartyDetail(...)`,
- `getValidationResults(...)`,
- `getMatchResults(...)`,
- `getMatchComparison(...)`,
- `getLineage(...)`,
- `getChangeHistory(...)`.

Oznacza to, że interfejs jest ściśle związany z odczytowymi endpointami `serving`, a nie z operacjami zapisu czy wywołaniami pipeline'u.

## 17.4. Główny układ aplikacji

Komponent `App.jsx` definiuje wspólny szkielet interfejsu:

- sekcję nagłówkową z tytułem aktywnego widoku,
- prezentację aktualnego adresu API,
- przycisk odświeżenia danych,
- przełącznik widoku `Golden Records` / `Walidacja` / `Matching`,
- obszar roboczy z aktywnym komponentem funkcjonalnym.

Stan główny obejmuje:

- `activeView` - wybór aktualnego widoku,
- `refreshToken` - prosty licznik wymuszający ponowne pobranie danych.

Frontend nie utrzymuje złożonego drzewa zależności pomiędzy widokami. Każdy widok sam odpowiada za pobranie i prezentację swoich danych.

## 17.5. Widok listy Golden Record

Widok listy Golden Record został zaimplementowany w:

- `frontend/src/features/golden-records/GoldenRecordsView.jsx`.

Komponent pobiera dane z endpointu:

```text
GET /layers/serving/golden-records
```

Obsługiwane filtry obejmują:

- `search`,
- `entity_type`.

Widok udostępnia:

- tabelę rekordów GOLD,
- filtrowanie po typie encji,
- wyszukiwanie po nazwie lub głównym identyfikatorze,
- paginację,
- ręczne odświeżanie danych przez komponent główny,
- przycisk `Szczegóły` dla każdego rekordu.

W tabeli prezentowane są:

- `record_id`,
- `entity_type`,
- nazwa wyświetlana,
- główny identyfikator,
- data utworzenia,
- data ostatniej aktualizacji.

Po kliknięciu `Szczegóły` otwierany jest modal ładowany zależnie od typu encji przez:

- `GET /layers/serving/persons/{person_id}`,
- `GET /layers/serving/parties/{party_id}`.

Modal udostępnia trzy zakładki:

- `Szczegóły`,
- `Pochodzenie (lineage)`,
- `Historia zmian`.

W zakładce szczegółów osoba prezentuje również pochodzenie wartości identyfikatorów i adresów, a podmiot dodatkowo listę identyfikatorów i adresów. Dwie pozostałe zakładki korzystają odpowiednio z endpointów:

- `GET /layers/serving/lineage/{entity_type}/{record_id}`,
- `GET /layers/serving/history/{entity_type}/{record_id}`.

## 17.6. Widok walidacji

Widok walidacji został zaimplementowany w:

- `frontend/src/features/validation/ValidationView.jsx`.

Komponent pobiera dane z endpointu:

```text
GET /layers/serving/validation-results
```

Obsługiwane filtry obejmują:

- `entity_type`,
- `source_system_code`,
- `rule_code`,
- `status`,
- `severity`.

Widok udostępnia:

- formularz filtrów,
- tabelę wyników,
- obsługę paginacji,
- komunikat ładowania,
- komunikat błędu,
- komunikat pustego wyniku.

W tabeli prezentowane są między innymi:

- identyfikator wyniku walidacji,
- źródło,
- typ encji,
- kod reguły,
- pole,
- status,
- poziom istotności,
- sprawdzana wartość,
- komunikat,
- data utworzenia.

Dodatkowo komponent `ruleHighlight.js` nadaje części reguł wyróżnienia wizualne. Nie zmienia to logiki danych, ale poprawia czytelność najważniejszych problemów walidacyjnych.

## 17.7. Widok matchingu

Widok matchingu znajduje się w:

- `frontend/src/features/matching/MatchingView.jsx`.

Komponent może pracować w dwóch trybach:

- `levenshtein`,
- `jaro-winkler`.

Zmiana trybu powoduje przełączenie zestawu danych i ponowne pobranie listy kandydatów z endpointów:

```text
GET /layers/serving/match-results/levenshtein
GET /layers/serving/match-results/jaro-winkler
```

Widok udostępnia:

- przełącznik algorytmu,
- tabelę kandydatów,
- paginację,
- obsługę błędów,
- przycisk `Porównaj` dla każdej pary.

W tabeli matchingu prezentowane są między innymi:

- identyfikator kandydata,
- typ encji,
- wynik liczbowy,
- decyzja,
- silne pola,
- pola konfliktowe,
- informacja o przejściu do drugiego sita,
- pola tekstowe,
- para `left_preprocessed_id` / `right_preprocessed_id`,
- data utworzenia.

Interfejs pokazuje więc nie tylko samą decyzję, ale także podstawowe przesłanki porównania.

## 17.8. Porównanie pary rekordów

Szczegółowe porównanie dwóch rekordów zostało wydzielone do komponentu:

- `frontend/src/features/matching/MatchingComparisonPanel.jsx`.

Po kliknięciu `Porównaj` frontend wywołuje:

```text
GET /layers/serving/match-results/comparison
```

z parametrami:

- `entity_type`,
- `left_preprocessed_id`,
- `right_preprocessed_id`.

W odpowiedzi otrzymuje:

- szczegóły kandydata Levenshteina,
- szczegóły kandydata Jaro-Winklera,
- dwa rekordy źródłowe jako słowniki pól.

Modal porównania:

- zestawia lewą i prawą wartość tego samego pola,
- oznacza zgodność albo różnicę,
- rozpoznaje pola silne, konfliktowe i tekstowe,
- pozwala zamknąć okno kliknięciem tła albo klawiszem `Escape`.

Jest to obecnie najbardziej analityczny element frontendu, ponieważ pozwala przejść od listy kandydatów do porównania atrybut po atrybucie.

## 17.9. Komponenty wspólne

Na potrzeby wielu widoków wydzielono dwa małe komponenty interfejsu:

- `Pager.jsx`,
- `StatusBadge.jsx`.

`Pager` obsługuje ruch po stronach wyników i pokazuje zakres aktualnie prezentowanych rekordów.  
`StatusBadge` nadaje wspólny wygląd statusom takim jak:

- `PASS`,
- `ERROR`,
- `AUTO_MERGE`,
- `REVIEW`,
- `TAK`,
- `NIE`.

Dzięki temu oba główne widoki zachowują wspólną konwencję wizualną.

## 17.10. Formatowanie i stałe

Widoki korzystają z warstwy pomocniczej:

- `frontend/src/utils/formatters.js`,
- `frontend/src/utils/matching.js`.

Funkcje te odpowiadają za:

- formatowanie dat,
- bezpieczne wyświetlanie pustych wartości,
- dobór wariantu wizualnego znacznika statusu,
- prezentację wyniku punktowego matchingu.

Stałe pomocnicze znajdują się w:

- `frontend/src/constants/goldenRecords.js`,
- `frontend/src/constants/validation.js`,
- `frontend/src/constants/matching.js`,
- `frontend/src/constants/validationFilters.js`.

Zawierają one między innymi:

- limity stron,
- puste struktury danych,
- listy opcji filtrów,
- listy algorytmów dostępnych w widoku matchingu,
- opcje filtrowania typu encji dla listy Golden Record.

## 17.11. Warstwa stylów

Style zostały podzielone na kilka plików:

- `styles/base.css`,
- `styles/layout.css`,
- `styles/components.css`,
- `styles/views.css`,
- `styles/index.css`.

Podział jest funkcjonalny:

- `base` definiuje podstawy typografii i zmiennych,
- `layout` opisuje główny układ aplikacji,
- `components` obejmuje wspólne elementy interfejsu,
- `views` zawiera klasy specyficzne dla widoków,
- `index.css` spina całość.

Takie rozdzielenie wystarcza dla obecnej skali aplikacji i ogranicza konieczność utrzymywania jednego dużego arkusza stylów.

## 17.12. Zakres funkcjonalny obecnej wersji

Aktualnie frontend realizuje:

- odczyt listy Golden Record,
- filtrowanie listy Golden Record,
- wyszukiwanie Golden Record po nazwie albo identyfikatorze w ramach endpointu listy,
- odczyt szczegółów osoby i podmiotu,
- odczyt lineage i historii zmian dla wybranego rekordu,
- odczyt wyników walidacji,
- filtrowanie wyników walidacji,
- paginację,
- odczyt kandydatów matchingu dla dwóch algorytmów,
- porównanie szczegółów dwóch rekordów,
- ręczne odświeżenie danych.

Nie realizuje natomiast:

- uruchamiania etapów pipeline'u,
- ręcznej obsługi przypadków `REVIEW`,
- edycji danych.

Jest to więc interfejs odczytowy dla najważniejszych wyników warstwy `serving`, ale nie pełny panel operacyjny goldenizacji.

## 17.13. Miejsce frontendu w architekturze

Frontend nie komunikuje się bezpośrednio z SQL Serverem, Airflow ani Oracle. Jego jedynym punktem dostępu do danych jest REST API backendu.

Z architektonicznego punktu widzenia oznacza to, że:

- wszystkie dane prezentowane użytkownikowi przechodzą przez warstwę `serving`,
- frontend pozostaje cienką warstwą prezentacji,
- reguły biznesowe, walidacyjne i matchingowe pozostają po stronie backendu.

To podejście upraszcza spójność systemu i pozwala rozwijać interfejs bez przenoszenia logiki domenowej do przeglądarki.

## 17.14. Ograniczenia

Najważniejsze ograniczenia obecnego frontendu to:

- brak routingu URL i głębszej nawigacji pomiędzy ekranami,
- brak mechanizmu uwierzytelniania użytkownika,
- brak funkcji zapisu lub akcji na pipeline,
- brak interfejsu do ręcznej pracy z decyzjami `REVIEW`,
- zależność od dostępności backendu i poprawnej konfiguracji `VITE_API_URL`.

Nie są to braki przypadkowe. Frontend w aktualnej wersji został zawężony do czytelnego podglądu danych servingowych dla Golden Record, walidacji i matchingu.

## 17.15. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `frontend/src/main.jsx` - punkt wejścia aplikacji,
- `frontend/src/App.jsx` - główny układ i przełączanie widoków,
- `frontend/src/api/serving.js` - komunikacja z backendem,
- `frontend/src/features/golden-records/GoldenRecordsView.jsx` - lista Golden Record,
- `frontend/src/features/golden-records/GoldenRecordDetailModal.jsx` - szczegóły, lineage i historia zmian,
- `frontend/src/features/validation/ValidationView.jsx` - widok wyników walidacji,
- `frontend/src/features/validation/ruleHighlight.js` - wyróżnianie wybranych reguł,
- `frontend/src/features/matching/MatchingView.jsx` - widok kandydatów matchingu,
- `frontend/src/features/matching/MatchingComparisonPanel.jsx` - modal porównania rekordów,
- `frontend/src/components/ui/Pager.jsx` - paginacja,
- `frontend/src/components/ui/StatusBadge.jsx` - wspólny komponent statusów,
- `frontend/src/utils/formatters.js` - formatowanie wartości i dat,
- `frontend/src/utils/matching.js` - prezentacja wyników matchingu,
- `frontend/src/constants/validation.js` i `frontend/src/constants/matching.js` - limity i puste struktury danych,
- `frontend/src/styles/` - style aplikacji,
- `frontend/package.json` - konfiguracja zależności i skryptów uruchomieniowych.
