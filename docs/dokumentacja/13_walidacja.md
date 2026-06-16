# 13. Walidacja

Warstwa walidacji ocenia jakość danych po preprocessingu. Nie modyfikuje sprawdzanych rekordów i nie uzupełnia ich danymi zewnętrznymi. Dla każdej wykonanej reguły zapisuje osobny wynik, który wskazuje sprawdzane pole, wartość, status oraz komunikat.

Błąd danych nie przerywa przetwarzania pozostałych rekordów. Dzięki temu po zakończeniu procesu dostępny jest zestaw wszystkich wykrytych niezgodności, a nie tylko pierwszy napotkany problem.

## 13.1. Uruchomienie procesu

Walidację uruchamia endpoint:

```text
POST /layers/validation/validation-load
```

Żądanie zawiera:

- `raw_file_id` – identyfikator pliku,
- `entity_type` – typ encji `PERSON` albo `PARTY`,
- `check_email_dns` – informację, czy oprócz składni adresu e-mail należy sprawdzić jego domenę; domyślna wartość to `true`.

Walidacja wymaga wcześniejszego utworzenia rekordów preprocessed. Serwis pobiera odpowiadające sobie rekordy z tabel staging i preprocessed. Brak takich danych lub niepoprawny typ encji powoduje odpowiedź HTTP 400.

## 13.2. Przebieg walidacji

Proces obejmuje:

1. pobranie rekordów staging i preprocessed dla wskazanego pliku,
2. usunięcie wcześniejszych wyników walidacji tego pliku i typu encji,
3. utworzenie wpisu `ProcessLog` dla kroku `VALIDATION`,
4. wykonanie reguł odpowiednich dla osoby albo podmiotu,
5. zapis wyników w tabeli `stg.Validation_Result`,
6. zakończenie wpisu procesu statusem `SUCCESS` lub `FAILED`.

Ponowne uruchomienie zastępuje wcześniejszy zestaw wyników, dlatego w tabeli pozostają rezultaty ostatniego wykonania walidacji. Może się on różnić od poprzedniego między innymi po zmianie danych, reguł, plików TERYT albo ustawienia kontroli DNS.

Status procesu opisuje wykonanie techniczne etapu. Wykrycie niepoprawnych wartości nie oznacza awarii procesu. Jeżeli wszystkie reguły zostały wykonane i zapisane, `ProcessLog` otrzymuje status `SUCCESS`, nawet gdy część wyników ma status `ERROR`.

## 13.3. Model wyniku

Każdy wpis `Validation_Result` dotyczy jednej reguły zastosowanej do jednego rekordu. Zawiera między innymi:

- identyfikatory partii, pliku, rekordu staging i rekordu preprocessed,
- typ encji,
- poziom danych: `STAGING` albo `PREPROCESSING`,
- kod reguły i nazwę sprawdzanego pola,
- sprawdzaną wartość,
- status, poziom istotności i komunikat.

Poprawny wynik ma status `PASS`, poziom `INFO` i komunikat `OK`. Niezgodność otrzymuje status oraz poziom istotności `ERROR`, a komunikat zawiera kod rozpoznanego błędu. Podsumowanie odpowiedzi API podaje liczbę wszystkich wyników oraz liczbę reguł zakończonych jako `PASS` i `ERROR`. Nie są to liczby poprawnych i błędnych rekordów, ponieważ jeden rekord jest sprawdzany przez wiele reguł.

Zapisane wyniki można później odczytać przez endpoint `GET /layers/serving/validation-results`, z opcjonalnym filtrowaniem po typie encji, systemie źródłowym i kodzie reguły.

## 13.4. Walidacja osoby

Dla encji `PERSON` wykonywane są następujące kontrole:

| Reguła | Zakres |
|---|---|
| `PERSON_PESEL_CHECKSUM` | Format i suma kontrolna numeru PESEL. |
| `PERSON_PESEL_BIRTH_DATE_MATCH` | Zgodność daty urodzenia zapisanej w PESEL z datą w rekordzie. |
| `PERSON_PESEL_SEX_MATCH` | Zgodność płci zapisanej w PESEL z wartością źródłową. |
| `PERSON_PESEL_BIRTH_DATE_NOT_FUTURE` | Sprawdzenie, czy data zakodowana w PESEL nie jest przyszła. |
| `PERSON_BIRTH_DATE_NOT_FUTURE` | Sprawdzenie, czy data urodzenia z rekordu nie jest przyszła. |
| `PERSON_EMAIL_SYNTAX` | Kontrola adresu e-mail i opcjonalnie jego domeny. |
| `PERSON_ID_CARD_CHECKSUM` | Format i suma kontrolna polskiego dowodu osobistego. |
| Reguły nazw | Dopuszczalny zapis imion i nazwisk, w tym polskich znaków, spacji, apostrofu i łącznika. |

Przy porównaniu płci serwis w pierwszej kolejności próbuje odczytać jej wartość z `Raw_Record_JSON`. Jest to zabezpieczenie przed błędną konwersją wartości źródłowej do typu logicznego podczas wcześniejszego etapu. Jeżeli wartość nie jest dostępna w surowym rekordzie, używane jest pole staging.

Brak PESEL jest traktowany jako błąd podstawowej reguły jego poprawności. Większość pozostałych pól opcjonalnych nie powoduje błędu wyłącznie z powodu braku wartości. Przykładowo suma kontrolna dowodu jest sprawdzana dopiero wtedy, gdy numer został podany.

## 13.5. Walidacja podmiotu

Dla encji `PARTY` sprawdzane są:

| Reguła | Zakres |
|---|---|
| `PARTY_NIP_CHECKSUM` | Format i suma kontrolna NIP. |
| `PARTY_REGON_CHECKSUM` | Format i suma kontrolna REGON o długości 9 albo 14 cyfr. |
| `PARTY_KRS_FORMAT` | Obecność dokładnie 10 cyfr w numerze KRS. |
| `PARTY_LEI_CHECKSUM` | Format i suma kontrolna identyfikatora LEI. |
| `PARTY_EMAIL_SYNTAX` | Kontrola adresu e-mail i opcjonalnie jego domeny. |
| `PARTY_NAME_STRING` | Sprawdzenie, czy nazwa jest niepustym tekstem. |

NIP, REGON, KRS i LEI są polami opcjonalnymi na tym etapie. Brak identyfikatora daje wynik `PASS`, natomiast podana wartość musi spełnić odpowiednią regułę. W przypadku KRS kontrolowany jest format, a nie zgodność numeru z rejestrem.

Walidacja podmiotu obejmuje również porządek dat:

- data utworzenia nie może być późniejsza od daty wyrejestrowania,
- data rejestracji nie może być późniejsza od daty wyrejestrowania,
- data kolejnego odnowienia nie może być wcześniejsza od daty ostatniej aktualizacji,
- początek relacji z bezpośrednim podmiotem dominującym nie może być późniejszy od jej końca,
- początek relacji z najwyższym podmiotem dominującym nie może być późniejszy od jej końca.

Jeżeli jedna z dat pary nie występuje, kolejność nie jest kwestionowana. Podana, lecz nierozpoznana wartość daty powoduje wynik `ERROR`.

## 13.6. Kontrola adresu z wykorzystaniem TERYT

Walidacja adresu korzysta z plików `SIMC.csv` i `ULIC.csv`. Dane mogą znajdować się w katalogu wskazanym przez zmienną `TERYT_DIR` albo w katalogu `teryt` pod ścieżką `FILESTREAM_PATH`. W repozytorium dostępne są pliki w `data/teryt`.

Pliki można również przekazać przez endpoint:

```text
POST /layers/validation/teryt-load
```

Endpoint zapisuje przekazane pliki w systemie plików. Nie wzbogaca rekordów i nie importuje TERYT do tabel bazy danych.

Jeżeli oba wymagane pliki są dostępne, dla osoby i podmiotu wykonywane są dwie reguły:

- `ADDR_TERYT_CITY_EXISTS` – występowanie miejscowości w rejestrze SIMC,
- `ADDR_TERYT_STREET_EXISTS` – występowanie ulicy w rejestrze ULIC dla rozpoznanej miejscowości.

Nazwy są porównywane po ujednoliceniu wielkości liter i odstępów. Dla ulic uwzględniane są prefiksy `UL`, `AL`, `OS` i `PL`. Serwis obsługuje również wariant, w którym kolejność ostatnich członów nazwy ulicy jest odwrócona względem zapisu TERYT.

Brak miejscowości lub ulicy nie jest sam w sobie oznaczany jako błąd TERYT. Jeżeli miejscowość została podana, ale nie występuje w SIMC, zarówno kontrola miejscowości, jak i powiązanej ulicy otrzymuje `ERROR`. Gdy pliki TERYT nie są dostępne, reguły adresowe nie są wykonywane i nie powstają dla nich wyniki.

## 13.7. Walidacja adresu e-mail

Adres e-mail jest najpierw sprawdzany składniowo. Jeżeli parametr `check_email_dns` ma wartość `true`, po poprawnej kontroli składni serwis sprawdza również istnienie domeny.

Kontrola domeny próbuje rozwiązać jej adres sieciowy, a następnie rekord MX. Zapytania DNS mają krótki limit czasu, aby ograniczyć wpływ niedostępnej sieci na czas przetwarzania. Wynik tej reguły może zatem zależeć od aktualnej dostępności DNS. Dla środowiska bez dostępu do sieci można wyłączyć tę część kontroli, pozostawiając samą walidację składni.

## 13.8. Wykorzystanie wyników

Wyniki walidacji są wykorzystywane przez warstwę goldenizacji przy wyborze wartości przeżywającej. Status jest pobierany dla konkretnego pola rekordu preprocessed. Wartość z wynikiem `PASS` może otrzymać pierwszeństwo przed kandydatem, który nie przeszedł walidacji.

Potwierdzenie adresu przez TERYT stanowi dodatkową przesłankę przy wyborze adresu. Walidacja nie wykonuje jednak matchingu, nie grupuje rekordów i nie tworzy rekordu golden.

## 13.9. Ograniczenia

Najważniejsze ograniczenia walidacji to:

- brak sprawdzania identyfikatorów bezpośrednio w rejestrach zewnętrznych,
- kontrola KRS ograniczona do formatu,
- zależność kontroli domeny e-mail od dostępności DNS,
- wykonywanie reguł TERYT tylko wtedy, gdy oba pliki referencyjne są dostępne,
- brak weryfikacji numerów telefonu i adresów WWW,
- zastępowanie wcześniejszych wyników podczas ponownego uruchomienia.

Warstwa rejestruje wykryte problemy, lecz nie poprawia wartości automatycznie. Zachowane powiązania z rekordami staging i preprocessed pozwalają ustalić, której wartości oraz reguły dotyczy wynik.

## 13.10. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `app/layers/validation/api.py` – endpointy walidacji i ładowania plików TERYT,
- `app/layers/validation/service.py` – reguły walidacyjne i obsługa TERYT,
- `app/layers/validation/repository.py` – pobieranie danych i zapis wyników,
- `app/layers/validation/models.py` – model `Validation_Result`,
- `app/layers/validation/schemas.py` – modele odpowiedzi API,
- `tests/test_validation.py` – testy reguł osoby i podmiotu,
- `tests/test_teryt_validation.py` – testy kontroli adresów,
- `scripts/init_proposed_mssql_schema.sql` – definicja tabeli i indeksów walidacji.
