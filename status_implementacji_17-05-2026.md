# Status implementacji - 17.05.2026

## Zakres aktualizacji

Od poprzedniego statusu z 07.05.2026 prace koncentrowały się na automatyzacji uruchamiania procesu, poprawie danych testowych oraz dopracowaniu preprocessingu i walidacji. Nie zmieniano głównej koncepcji architektury: dane nadal przechodzą przez warstwy RAW, staging, preprocessing i validation.

Najważniejsza zmiana polega na tym, że proces nie jest już wyłącznie zestawem ręcznie uruchamianych endpointów. Został spięty w pipeline Airflow, który może wykonać kolejne etapy przetwarzania dla wskazanego pliku.

## Nowe i istotnie rozwinięte elementy

| Obszar | Status |
| --- | --- |
| Pipeline Airflow dla procesu RAW -> staging -> preprocessing -> validation | Zrobione |
| Automatyczne rozpoznawanie źródła danych na podstawie nazwy pliku | Zrobione |
| Obsługa rejestrów zawierających jednocześnie osoby i podmioty | Zrobione |
| Rozbudowa danych syntetycznych do testów procesu | Zrobione |
| Poprawiona normalizacja nazw firm i form prawnych | Zrobione |
| Poprawiona normalizacja i rozbijanie adresów | Zrobione |
| Walidacja zgodności PESEL z datą urodzenia | Zrobione |
| Walidacja zgodności PESEL z płcią | Zrobione |
| Walidacja emaila z opcjonalnym sprawdzaniem DNS | Zrobione |
| Walidacja imion i nazwisk z polskimi znakami | Zrobione |

## Automatyzacja procesu w Airflow

Dodano DAG `goldenizacja_pipeline`, który uruchamia pełną ścieżkę techniczną:

```text
raw_load -> staging_load -> preprocessing_load -> validation_load
```

DAG wywołuje istniejące endpointy API, dzięki czemu nie dubluje logiki biznesowej. Airflow pełni rolę orkiestratora procesu, a logika ładowania, mapowania, preprocessingu i walidacji pozostaje w aplikacji.

Pipeline może działać w trybie automatycznym. Na podstawie nazwy pliku potrafi rozpoznać źródło danych, na przykład PESEL, KRS, CEIDG, REGON, VAT, GLEIF albo rejestry KNF.

Wprowadzono też obsługę źródeł, które zawierają dane dla dwóch typów encji. Dla takich rejestrów proces uruchamia się osobno dla `PARTY` i `PERSON`, bez konieczności ręcznego wykonywania dwóch niezależnych requestów.

Dotyczy to między innymi:

- CEIDG
- KRS
- KNF agent
- KNF pracownik agenta
- KNF firmy inwestycyjne

## Rozbudowa danych testowych

Rozbudowano dane syntetyczne używane do testowania procesu. Każdy rejestr ma obecnie większy zestaw rekordów rozłożony na formaty CSV, JSON, XML i XLSX.

Dane testowe zawierają teraz również kontrolowane błędy, które pozwalają sprawdzać działanie walidacji:

- niepoprawne identyfikatory
- błędne domeny email
- braki w danych adresowych
- literówki w polach tekstowych
- przypadki relacji i ról w KRS


## Poprawki preprocessingu

Preprocessing został dopracowany pod kątem danych, które będą później używane do porównywania rekordów.

Dodano lub poprawiono:

- wyodrębnianie krótkiej nazwy firmy z pełnej nazwy
- rozpoznawanie form prawnych, takich jak `sp. z o.o.`, `S.A.` albo `spółka akcyjna`
- rozróżnianie form prawnych od nazw handlowych
- lepsze rozbijanie adresów na ulicę, numer budynku, numer lokalu, kod pocztowy i miasto
- obsługę przypadków, w których pełny adres trafia do nietypowego pola

Podjęto też ważną decyzję dotyczącą polskich znaków. Aktualna normalizacja nie usuwa znaków diakrytycznych. Wartości są porządkowane i zamieniane na wielkie litery, ale znaki takie jak `Ł`, `Ó`, `Ż` pozostają zachowane.

Przykład:

```text
Łukasz Żółć -> ŁUKASZ ŻÓŁĆ
```

To jest bezpieczniejsze na obecnym etapie, ponieważ nie tracimy informacji źródłowej potrzebnej do późniejszego wyjaśnienia wyniku matchingu.

## Poprawki walidacji

Walidacja została rozszerzona o reguły, które sprawdzają nie tylko format danych, ale też ich podstawową spójność.

Dla PESEL dodano:

- sprawdzenie sumy kontrolnej
- sprawdzenie zgodności daty urodzenia z numerem PESEL
- sprawdzenie zgodności płci z numerem PESEL

Dodane kody błędów:

```text
ERR_PESEL_BIRTH_DATE_MISMATCH
ERR_PESEL_SEX_MISMATCH
```

Poprawiono również obsługę płci. Ponieważ w stagingu płeć jest mapowana logicznie jako `1` dla kobiet i `0` dla mężczyzn, walidacja potrafi w razie potrzeby odczytać pierwotną wartość z `Raw_Record_JSON`. Pozwala to uniknąć błędnej interpretacji, gdy istotne jest porównanie z wartością źródłową.

## Walidacja emaili i nazw

Walidacja emaili została rozszerzona o opcjonalne sprawdzanie domeny. Można ją uruchamiać w dwóch trybach:

- szybkim, gdzie sprawdzana jest składnia emaila
- dokładniejszym, gdzie dodatkowo sprawdzana jest domena

Takie rozdzielenie jest praktyczne, ponieważ sprawdzanie DNS zależy od sieci i nie powinno zawsze blokować lokalnych testów.

Poprawiono również walidację imion i nazwisk. Reguły nadal wykrywają niedozwolone znaki, na przykład cyfry, ale poprawnie akceptują polskie litery.

## Testy

Aktualnie sprawdzony zestaw testów obejmuje staging, preprocessing i validation:

```text
python3 -m unittest tests.test_preprocessing tests.test_staging_mapper tests.test_validation -v
```

Wynik:

```text
43/43 tests OK
```

Testy obejmują między innymi:

- mapowanie danych do stagingu
- zachowanie adresów w stagingu bez rozbijania
- rozbijanie adresów w preprocessingu
- normalizację nazw firm i form prawnych
- przypadki GLEIF z identyfikatorami KRS i REGON
- walidację PESEL z datą urodzenia i płcią
- walidację emaili
- walidację imion i nazwisk z polskimi znakami

## Aktualny stan

Na dzień 17.05.2026 gotowe są następujące elementy:

- przyjęcie plików źródłowych do RAW
- mapowanie danych do stagingu
- preprocessing wartości używanych do porównywania i walidacji
- walidacja identyfikatorów, emaili oraz wybranych pól tekstowych
- automatyczne uruchamianie procesu przez Airflow
- dane syntetyczne pozwalające testować poprawne i błędne przypadki

Najważniejszy postęp względem poprzedniego statusu to przejście od ręcznego testowania pojedynczych endpointów do procesu, który można uruchomić jako pipeline, oraz rozszerzenie walidacji o reguły spójności danych.
