# 12. Preprocessing i standaryzacja

Warstwa preprocessing przekształca dane zapisane w tabelach staging do ujednoliconej postaci wykorzystywanej przez walidację, wyszukiwanie duplikatów i proces goldenizacji. Oryginalne wartości pozostają w tabelach staging, natomiast ich znormalizowane odpowiedniki są zapisywane w tabelach `Person_Preprocessed` albo `Party_Preprocessed`.

Preprocessing nie rozstrzyga, czy wartość jest poprawna biznesowo. Przykładowo ujednolica zapis numeru telefonu lub adresu, ale nie potwierdza ich istnienia. Takie kontrole należą do kolejnych etapów przetwarzania.

## 12.1. Uruchomienie procesu

Proces jest udostępniony przez endpoint:

```text
POST /layers/preprocessing/preprocessing-load
```

Żądanie zawiera:

- `raw_file_id` – identyfikator pliku, którego rekordy mają zostać przetworzone,
- `entity_type` – typ encji: `PERSON` albo `PARTY`.

Serwis pobiera z warstwy staging wszystkie rekordy powiązane z podanym plikiem i typem encji. Dla każdego rekordu tworzy dokładnie jeden rekord warstwy preprocessed. Relacja ta jest zabezpieczona ograniczeniem unikalności na identyfikatorze rekordu staging.

Jeżeli plik nie ma odpowiednich rekordów staging albo został już przetworzony dla danego typu encji, żądanie jest odrzucane z kodem HTTP 400. Ponowne uruchomienie nie nadpisuje istniejących danych i nie tworzy ich kopii.

## 12.2. Przebieg przetwarzania

Przetwarzanie obejmuje następujące kroki:

1. normalizację i sprawdzenie typu encji,
2. pobranie rekordów staging dla wskazanego pliku,
3. sprawdzenie, czy dane nie zostały już przetworzone,
4. utworzenie wpisu `ProcessLog` dla kroku `STANDARDIZATION`,
5. zastosowanie reguł właściwych dla osoby albo podmiotu,
6. zapis rekordów w odpowiedniej tabeli preprocessed,
7. zakończenie wpisu procesu statusem `SUCCESS` lub `FAILED`.

Preprocessing nie zmienia statusu całej partii importowej, ponieważ odpowiada wyłącznie za jeden z etapów jej przetwarzania. Aktualna implementacja nie wykonuje całego etapu jako jednej wspólnej transakcji. Repozytorium zatwierdza osobno utworzenie logu procesu, zapis rekordów preprocessed i zakończenie logu. W przypadku błędu niezakończona część operacji jest wycofywana, ale wcześniej zatwierdzone kroki techniczne mogą pozostać zapisane.

## 12.3. Reguły wspólne

Podstawowe reguły standaryzacji są stosowane zależnie od rodzaju pola.

| Rodzaj danych | Sposób standaryzacji |
|---|---|
| Tekst | Usunięcie nadmiarowych spacji i zamiana liter na wielkie. Polskie znaki są zachowywane. |
| Identyfikator | Zamiana liter na wielkie oraz usunięcie separatorów i znaków innych niż litery i cyfry. |
| Adres e-mail | Usunięcie spacji na początku i końcu oraz zamiana liter na małe. |
| Numer telefonu | Próba zapisu w formacie E.164, z domyślnym regionem Polski; w razie braku możliwości pełnego rozpoznania stosowana jest prostsza normalizacja cyfr. |
| Adres WWW | Zamiana liter na małe oraz usunięcie prefiksów `http://`, `https://` i `www.`. |
| Kod pocztowy | Sprowadzenie do cyfr i zapis w formacie `NN-NNN`, jeżeli wartość ma pięć cyfr. |
| Dane JSON | Próba odczytania JSON, uporządkowanie kluczy i zapis w ujednoliconej postaci; niepoprawny JSON jest traktowany jako tekst. |

Wartości puste lub zawierające wyłącznie białe znaki są zapisywane jako `NULL`. Preprocessing nie uzupełnia brakujących danych wartościami domyślnymi, z wyjątkiem opisanych niżej reguł wyprowadzania pól.

## 12.4. Standaryzacja danych osoby

Dla encji `PERSON` przetwarzane są w szczególności:

- PESEL,
- imię, drugie imię i nazwisko,
- numer dowodu osobistego i paszportu,
- miejsce urodzenia i obywatelstwo,
- numer telefonu i adres e-mail.

Na podstawie dostępnych części imienia i nazwiska powstaje pole `Full_Name`. Nieobecne elementy są pomijane, dzięki czemu w wartości nie pojawiają się dodatkowe separatory ani wielokrotne spacje.

Data urodzenia, płeć i pola logiczne są przenoszone z warstwy staging w postaci nadanej podczas wcześniejszego ładowania danych. Preprocessing nie wykonuje ponownie ich konwersji.

## 12.5. Standaryzacja danych podmiotu

Dla encji `PARTY` ujednolicane są między innymi:

- nazwa pełna i skrócona,
- forma prawna,
- NIP, REGON, KRS i LEI,
- dane rejestrowe i numery decyzji,
- dane kontaktowe,
- informacje o relacjach z innymi podmiotami.

Identyfikatory są odczytywane z pola `Identifiers_JSON`. Jeżeli źródło GLEIF zawiera identyfikator organu walidacyjnego odpowiadający rejestrowi KRS albo REGON, numer rejestracyjny może zostać przypisany do właściwego pola. Wartość podana bezpośrednio w identyfikatorach źródłowych ma pierwszeństwo przed wartością wyprowadzoną.

Jeżeli brakuje nazwy skróconej lub formy prawnej, serwis może wyprowadzić je z nazwy pełnej. Rozpoznawane są najczęściej występujące polskie formy, między innymi spółka akcyjna, spółka z ograniczoną odpowiedzialnością, spółka jawna, spółka komandytowa, fundacja i stowarzyszenie. Określenia opisujące profil działalności, takie jak `PPHU`, nie są traktowane jako forma prawna.

Reguła ta ma charakter pomocniczy. Nie zastępuje danych rejestrowych i nie przesądza o poprawności prawnej rozpoznanego oznaczenia.

## 12.6. Rozdzielanie i składanie adresu

Adres źródłowy może być zapisany jako jedno pole albo jako kilka części. Preprocessing próbuje rozpoznać:

- ulicę,
- numer budynku,
- numer lokalu,
- kod pocztowy,
- miejscowość,
- kraj.

Obsługiwane są między innymi zapisy, w których ulica występuje przed kodem i miejscowością albo po nich. Numery lokali oznaczone jako `m.`, `lok.` lub `lokal` są sprowadzane do zapisu z ukośnikiem. Prefiksy ulic są ujednolicane, przykładowo do `UL`, `AL`, `OS` i `PL`.

Po rozdzieleniu elementów tworzona jest również wartość `Full_Address`, zawierająca dostępne części adresu w ustalonej kolejności. Ułatwia to późniejsze porównywanie rekordów, natomiast osobne kolumny pozwalają dopasowywać tylko wybrane elementy.

Mechanizm jest oparty na regułach i wyrażeniach regularnych. Nietypowe lub niejednoznaczne adresy mogą nie zostać rozdzielone w pełni. Weryfikacja miejscowości i kodu pocztowego względem danych TERYT jest wykonywana w warstwie walidacji, a nie podczas preprocessingu.

## 12.7. Informacja o zastosowanych regułach

Każdy rekord preprocessed zawiera pole `Preprocessing_Rules_JSON`. Przechowuje ono ogólne oznaczenia zastosowanych grup reguł:

- standaryzacji tekstu,
- normalizacji telefonu,
- rozdzielania adresu,
- czasu wykonania operacji.

Pole opisuje sposób przetwarzania na poziomie ogólnym. Nie stanowi szczegółowego rejestru każdej zmiany wykonanej na poszczególnych wartościach. Zachowanie wartości źródłowych w warstwie staging umożliwia jednak porównanie danych przed i po standaryzacji.

## 12.8. Przygotowanie danych do dopasowywania

Tabele preprocessed zawierają zarówno ujednolicone pola pojedyncze, jak i pola złożone używane przez kolejne etapy. Dla osoby są to przykładowo pełne imię i nazwisko oraz zestawienia imienia, nazwiska, daty i miejsca urodzenia. Dla podmiotu wykorzystywane są przede wszystkim identyfikatory rejestrowe, nazwa, adres i dane kontaktowe.

W bazie utworzono indeksy wspierające wyszukiwanie po najważniejszych identyfikatorach i kombinacjach pól. Obejmują one między innymi PESEL, dokumenty tożsamości, NIP, REGON, KRS, LEI, dane kontaktowe oraz wybrane zestawienia nazw i adresów.

Preprocessing przygotowuje dane do porównania, ale nie łączy rekordów i nie wybiera rekordu golden. Decyzje te są podejmowane przez dalsze warstwy systemu.

## 12.9. Ograniczenia

Najważniejsze ograniczenia etapu to:

- regułowy charakter rozpoznawania adresów i form prawnych,
- zależność dokładności normalizacji telefonów od możliwości biblioteki `phonenumbers`,
- brak kontroli poprawności biznesowej identyfikatorów i danych kontaktowych,
- ogólny, a nie szczegółowy charakter pola `Preprocessing_Rules_JSON`,
- przetwarzanie wszystkich rekordów danego pliku i typu encji w ramach jednego wywołania.

Ograniczenia te nie powodują utraty danych źródłowych, ponieważ rekord staging pozostaje dostępny i jest wskazywany przez rekord preprocessed.

## 12.10. Odniesienia do implementacji

Najważniejsze elementy implementacji znajdują się w plikach:

- `app/layers/preprocessing/api.py` – endpoint uruchamiający preprocessing,
- `app/layers/preprocessing/service.py` – reguły standaryzacji i przebieg procesu,
- `app/layers/preprocessing/repository.py` – odczyt i zapis danych,
- `app/layers/preprocessing/models.py` – modele tabel preprocessed,
- `app/layers/preprocessing/schemas.py` – model odpowiedzi API,
- `tests/test_preprocessing.py` – testy reguł normalizacji,
- `scripts/init_proposed_mssql_schema.sql` – definicje tabel, ograniczeń i indeksów.
