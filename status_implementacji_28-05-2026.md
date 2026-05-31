# Status implementacji - 28.05.2026

## Zakres aktualizacji względem 22.05.2026

Od poprzedniego statusu powstał pierwszy mechanizm identyfikacji rekordów, które mogą opisywać ten sam byt. Jest to etap przygotowujący dane do późniejszej integracji golden recordów. Mechanizm działa w dwóch krokach: najpierw szeroko wyszukuje kandydatów do połączenia, a następnie dokładniej ocenia ich podobieństwo tekstowe.

Drugim obszarem prac było dodanie walidacji adresów z wykorzystaniem danych referencyjnych TERYT. System potrafi sprawdzać, czy miejscowość oraz ulica występują w oficjalnych danych referencyjnych. Dzięki temu walidacja nie ogranicza się tylko do formatu danych, ale zaczyna wykorzystywać zewnętrzne źródło odniesienia.

Etap `integration_golden` nadal nie tworzy jeszcze finalnych golden recordów. Na tym etapie odpowiada za identyfikację kandydatów, czyli wskazanie rekordów, które powinny zostać później zgrupowane i zintegrowane.

## Najważniejsze zmiany

| Obszar | Status |
| --- | --- |
| Pierwsze sito matchingu oparte o scoring ważony i Levenshteina | Zrobione |
| Drugie sito matchingu oparte o Jaro-Winkler | Zrobione |
| Osobna tabela wyników dla pierwszego sita | Zrobione |
| Osobna tabela wyników dla drugiego sita | Zrobione |
| Endpoint API dla pierwszego sita | Zrobione |
| Endpoint API dla drugiego sita | Zrobione |
| Podpięcie matchingu do pipeline Airflow | Zrobione |
| Walidacja miejscowości względem TERYT | Zrobione |
| Walidacja ulicy względem TERYT | Zrobione |
| Testy jednostkowe dla walidacji TERYT | Zrobione |
| Utworzenie schematu docelowego `gold` w MSSQL | Zrobione |
| Grupowanie rekordów w klastry golden recordów | Do zrobienia |
| Wybór wartości zwycięskich do golden recordu | Do zrobienia |
| Zapis finalnych rekordów do tabel `gold.*` | Do zrobienia |

## Nowy mechanizm matchingu

Dodano mechanizm identyfikacji rekordów, które mogą opisywać ten sam byt. Jest to pierwszy realny element warstwy `integration_golden`.

Proces działa obecnie jako dwa sita:

```text
preprocessing -> pierwsze sito Levenshtein -> drugie sito Jaro-Winkler -> kandydaci do goldenizacji
```

Pierwsze sito ma znaleźć możliwie szeroką listę par kandydatów. Drugie sito bierze tylko wyniki pierwszego sita i dokładniej sprawdza pola tekstowe. Dzięki temu system nie musi od razu porównywać wszystkiego bardzo precyzyjną metodą, tylko najpierw ogranicza zakres pracy, a potem doprecyzowuje wynik.

Sita nie tworzą jeszcze finalnych golden recordów. Ich zadaniem jest przygotowanie uporządkowanej listy par rekordów, które powinny zostać później zgrupowane i poddane integracji.

## Dane wejściowe do matchingu

Matching działa na danych po preprocessingu, a nie bezpośrednio na danych ze stagingu.

Jest to istotne, ponieważ staging przechowuje dane możliwie blisko postaci źródłowej, natomiast preprocessing przygotowuje wartości techniczne do porównywania:

- normalizuje tekst,
- rozbija adresy,
- porządkuje identyfikatory,
- przygotowuje pełne nazwy osób i podmiotów,
- tworzy pola pomocnicze wykorzystywane przez scoring.

Dla osób matching korzysta z danych z tabeli:

```text
stg.Person_Preprocessed
```

Dla podmiotów matching korzysta z danych z tabeli:

```text
stg.Party_Preprocessed
```

Takie rozdzielenie pozwala nie niszczyć danych źródłowych, a jednocześnie porównywać wartości w postaci bardziej stabilnej i przewidywalnej.

## Podział atrybutów w matchingu

W mechanizmie matchingu pola nie są traktowane jednakowo. Każde pole ma określoną rolę oraz wagę.

W uproszczeniu stosowane są trzy grupy atrybutów:

- atrybuty silne,
- atrybuty stałe lub półstałe,
- atrybuty dynamiczne i kontekstowe.

Atrybuty silne to takie, które zwykle jednoznacznie identyfikują osobę albo podmiot.

Przykłady:

```text
PESEL
NIP
REGON
KRS
LEI
numer dowodu
numer paszportu
```

Jeżeli silny identyfikator jest zgodny, para może zostać potraktowana jako bardzo mocny kandydat do integracji. Jeżeli silne identyfikatory są różne, system traktuje to jako istotny konflikt.

Atrybuty stałe i półstałe to dane, które są ważne, ale mogą mieć różne warianty zapisu.

Przykłady:

```text
imię
nazwisko
nazwa podmiotu
data urodzenia
typ formy prawnej
```

Atrybuty dynamiczne to dane, które mogą zmieniać się w czasie i nie powinny samodzielnie decydować o tożsamości rekordu.

Przykłady:

```text
telefon
e-mail
adres
strona WWW
```

Dzięki temu system nie traktuje zmiany telefonu albo adresu jako automatycznego dowodu, że są to dwa różne byty.

## Pierwsze sito matchingu

Pierwsze sito działa jako etap wyszukiwania kandydatów. Porównuje rekordy po preprocessingu i ocenia, czy mogą opisywać tę samą osobę albo ten sam podmiot.

Ten etap jest celowo mniej restrykcyjny. Ma znaleźć potencjalne dopasowania nawet wtedy, gdy dane nie są idealnie zgodne, na przykład gdy nazwa jest zapisana skrótem, adres jest częściowo inny albo jedno ze źródeł ma literówkę.

Mechanizm wykorzystuje:

- silne identyfikatory, takie jak PESEL, NIP, REGON, KRS, LEI, numer dowodu albo paszport,
- pola stałe i półstałe, na przykład datę urodzenia, imię, nazwisko, nazwę podmiotu,
- pola dynamiczne, na przykład telefon, e-mail i adres,
- ważony scoring pól,
- algorytm Levenshteina dla pól tekstowych,
- klasyfikację wyniku do decyzji `AUTO_MERGE`, `REVIEW`, `CANDIDATE` albo `NO_MATCH`.

Wyniki pierwszego sita są zapisywane w tabeli:

```text
stg.Match_Candidate_Levenshtein
```

Efektem pierwszego sita nie jest jeszcze decyzja o utworzeniu golden recordu. Efektem jest lista par rekordów z oceną podobieństwa i decyzją techniczną, czy para wygląda jak kandydat do dalszej analizy.

## Jak działa scoring pierwszego sita

Pierwsze sito oblicza wynik podobieństwa na podstawie wielu pól jednocześnie.

Dla każdego pola system:

- pobiera wartość z lewego rekordu,
- pobiera wartość z prawego rekordu,
- pomija pole, jeśli jedna ze stron nie ma wartości,
- oblicza podobieństwo,
- mnoży podobieństwo przez wagę pola,
- dodaje wynik do łącznego scoringu.

Wynik końcowy jest średnią ważoną z pól, które faktycznie dało się porównać.

Przykładowo, jeżeli dwa rekordy mają ten sam NIP, bardzo podobną nazwę i inny telefon, to różnica telefonu nie powinna przekreślać dopasowania. Telefon jest polem dynamicznym, więc ma mniejsze znaczenie niż identyfikator podatkowy albo nazwa.

Pierwsze sito wykrywa również konflikty.

Przykłady konfliktów:

- dwa różne numery PESEL,
- dwa różne numery NIP,
- różna data urodzenia przy braku silnego identyfikatora,
- bardzo niska zgodność imienia albo nazwiska.

Konflikty wpływają na decyzję końcową. Para może mieć wysoki wynik liczbowy, ale jeżeli występuje konflikt na silnym identyfikatorze, system nie powinien automatycznie uznać jej za pewne dopasowanie.

## Decyzje pierwszego sita

Pierwsze sito klasyfikuje pary do jednej z decyzji:

```text
AUTO_MERGE
REVIEW
CANDIDATE
NO_MATCH
```

Znaczenie decyzji:

- `AUTO_MERGE` - para wygląda na bardzo mocne dopasowanie i może być później automatycznie grupowana,
- `REVIEW` - para jest prawdopodobna, ale wymaga ostrożności,
- `CANDIDATE` - para jest słabszym kandydatem, ale warto zachować ją do dalszych etapów,
- `NO_MATCH` - para nie spełnia warunków dopasowania.

Do tabeli wynikowej trafiają tylko pary, które przekraczają ustawiony próg minimalny i nie są odrzucone jako `NO_MATCH`.

## Przykład działania pierwszego sita

Przykład dla podmiotu:

```text
Rekord A:
NIP = 1234567890
Name = FIRMA
City = RZESZÓW

Rekord B:
NIP = 1234567890
Name = FIRMA DŁUGA NAZWA
City = RZESZÓW
```

Pierwsze sito wykrywa mocny wspólny identyfikator `NIP`. Różnica w nazwie nie usuwa pary, ponieważ nazwa może być zapisana pełniej w jednym źródle i krócej w drugim.

Przykład dla osoby:

```text
Rekord A:
PESEL = 90013112345
First_Name = IWONA
Last_Name = NOWACKA

Rekord B:
PESEL = 90013112345
First_Name = IWONA
Last_Name = NOWACKA-KOWALSKA
```

Pierwsze sito zachowa taką parę jako bardzo silnego kandydata, ponieważ PESEL jest identyfikatorem rozstrzygającym, a różnica w nazwisku może wynikać ze zmiany nazwiska albo pełniejszego zapisu w jednym źródle.

## Drugie sito matchingu

Drugie sito jest etapem doprecyzowania wyników pierwszego sita. Nie porównuje wszystkich rekordów od początku, tylko bierze kandydatów zapisanych wcześniej w `stg.Match_Candidate_Levenshtein`.

Ten etap wykorzystuje algorytm Jaro-Winkler, który lepiej sprawdza się przy porównywaniu nazw, imion, nazwisk i innych krótkich pól tekstowych. Jest bardziej przydatny przy różnicach typu literówki, skróty, odmiany końcówek albo częściowo zgodne nazwy.

Przykładowy sens drugiego sita:

```text
Pierwsze sito:
rekord A - rekord B: możliwy kandydat

Drugie sito:
rekord A - rekord B: ponowna ocena nazw i pól tekstowych algorytmem Jaro-Winkler
```

Drugie sito zawęża listę kandydatów w ten sposób, że słabe pary tekstowe bez silnego identyfikatora nie trafiają dalej do tabeli drugiego sita. Jeżeli para ma zgodny silny identyfikator, na przykład ten sam PESEL albo NIP, może zostać zachowana mimo słabszej zgodności nazwy, ale zwykle z ostrożniejszą decyzją.

W praktyce oznacza to, że pierwsze sito odpowiada na pytanie: "czy te rekordy mogą być podobne?", a drugie sito odpowiada na pytanie: "czy podobieństwo tekstowe nadal potwierdza ten trop?".

Wyniki drugiego sita są zapisywane w tabeli:

```text
stg.Match_Candidate_JaroWinkler
```

Tabela przechowuje między innymi:

- powiązanie z kandydatem z pierwszego sita,
- wynik Levenshteina,
- wynik Jaro-Winkler,
- decyzję matchingu,
- pola silnego dopasowania,
- pola konfliktowe,
- pola tekstowe wykorzystane przy drugim sicie.

## Dlaczego dodano Jaro-Winkler

Levenshtein dobrze mierzy liczbę operacji potrzebnych do przekształcenia jednego tekstu w drugi. Jest przydatny jako pierwsze sito, ale nie zawsze najlepiej oddaje podobieństwo krótkich nazw, imion i nazwisk.

Jaro-Winkler lepiej sprawdza się przy danych osobowych i nazwach, ponieważ większą wagę przykłada do zgodności początku tekstu. Jest to przydatne w przypadkach, gdzie nazwa zaczyna się tak samo, ale dalej pojawiają się dopiski, skróty albo końcówki.

Przykłady sytuacji, w których drugie sito jest potrzebne:

- literówki w nazwisku,
- skrócona i pełna nazwa firmy,
- dopisek imienia właściciela przy nazwie działalności,
- różne warianty zapisu imienia,
- różne końcówki nazwisk,
- częściowo zgodny adres albo miejscowość.

Drugie sito nie zastępuje pierwszego. Jego zadaniem jest ponowna ocena tych par, które pierwsze sito uznało za warte sprawdzenia.

## Jak drugie sito zawęża wyniki

Zawężenie polega na tym, że druga tabela nie jest prostą kopią wyników pierwszego sita.

Dla każdej pary z pierwszego sita system:

- pobiera oba rekordy,
- ponownie porównuje wybrane pola tekstowe,
- oblicza wynik Jaro-Winkler,
- przenosi informację o silnych dopasowaniach z pierwszego sita,
- uwzględnia konflikty,
- podejmuje nową decyzję,
- zapisuje tylko te pary, które nadal spełniają warunki drugiego sita.

Jeżeli para ma słabe podobieństwo tekstowe i nie posiada silnego identyfikatora, nie jest zapisywana w tabeli drugiego sita.

Jeżeli para ma silny identyfikator, ale teksty są słabsze, system może zachować ją jako `REVIEW`. Dzięki temu dopasowania oparte na PESEL albo NIP nie znikają tylko dlatego, że nazwa lub adres są zapisane inaczej.

Przykładowy przepływ:

```text
Pierwsze sito znajduje 100 kandydatów
Drugie sito ponownie ocenia te 100 par
Do tabeli Jaro-Winkler trafia tylko część par
Najmocniejsze pary dostają AUTO_MERGE
Niepewne pary dostają REVIEW albo CANDIDATE
Słabe pary bez silnych identyfikatorów są pomijane
```

To przygotowuje dane do kolejnego etapu, w którym pary trzeba będzie zamienić na grupy rekordów.

## Decyzje drugiego sita

Drugie sito również zwraca decyzje:

```text
AUTO_MERGE
REVIEW
CANDIDATE
NO_MATCH
```

Różnica polega na tym, że decyzja drugiego sita bazuje już na dokładniejszym podobieństwie tekstowym.

Przykładowe znaczenie decyzji po drugim sicie:

- `AUTO_MERGE` - para ma bardzo dobry wynik Jaro-Winkler i brak istotnych konfliktów,
- `REVIEW` - para wygląda prawdopodobnie, ale wymaga ostrożności,
- `CANDIDATE` - para zostaje zachowana jako słaby kandydat,
- `NO_MATCH` - para nie przechodzi drugiego sita i nie powinna być podstawą do integracji.

W praktyce do dalszej goldenizacji najbardziej wartościowe będą wyniki `AUTO_MERGE` i część wyników `REVIEW`.

## Zakres zapisu wyników matchingu

Pierwsze i drugie sito zapisują wyniki w osobnych tabelach.

Pierwsza tabela:

```text
stg.Match_Candidate_Levenshtein
```

Druga tabela:

```text
stg.Match_Candidate_JaroWinkler
```

Rozdzielenie tabel jest celowe. Pozwala sprawdzić:

- ile par znalazło pierwsze sito,
- ile par przeszło przez drugie sito,
- jak zmienił się wynik podobieństwa,
- czy Jaro-Winkler potwierdził, czy osłabił dopasowanie,
- które pola były silnymi dopasowaniami,
- które pola zostały uznane za konfliktowe.

Taki zapis ułatwia analizę działania algorytmu i późniejsze tłumaczenie decyzji.

## Endpointy API dla matchingu

Dodano endpointy dla obu etapów matchingu:

```text
POST /layers/integration_golden/match-candidates
POST /layers/integration_golden/match-candidates/jaro-winkler
```

Pierwszy endpoint uruchamia szerokie sito i zapisuje kandydatów Levenshteina.

Drugi endpoint uruchamia dokładniejsze sito Jaro-Winkler na wynikach pierwszego etapu.

Endpointy przyjmują między innymi:

- typ encji,
- opcjonalny `RawFile_ID`,
- minimalny próg wyniku,
- limit liczby porównywanych par dla pierwszego sita.

Dzięki temu można testować matching osobno dla osób i osobno dla podmiotów oraz ograniczać zakres testu do konkretnego pliku źródłowego.

## Integracja z Airflow

Pipeline Airflow został rozszerzony o etap:

```text
integration_golden_match
```

Ten krok uruchamia obecnie oba sita:

```text
match-candidates -> match-candidates/jaro-winkler
```

Dzięki temu po przejściu danych przez RAW, staging, preprocessing i validation pipeline może automatycznie przygotować kandydatów do późniejszej goldenizacji.

DAG posiada parametry sterujące matchingiem, między innymi:

- minimalny wynik pierwszego sita,
- minimalny wynik Jaro-Winkler,
- limit liczby porównywanych par.

Limit par jest zabezpieczeniem przed przypadkowym uruchomieniem zbyt dużego porównania każdy-z-każdym.

Po tej zmianie pipeline obejmuje nie tylko przygotowanie i walidację danych, ale również automatyczne uruchomienie identyfikacji kandydatów.

Aktualny przebieg logiczny wygląda następująco:

```text
raw_load
staging_load
preprocessing_load
validation_load
integration_golden_match
```

Ostatni krok wykonuje oba sita w odpowiedniej kolejności. Drugie sito zależy od wyników pierwszego, dlatego nie może zostać uruchomione samodzielnie bez wcześniejszego przygotowania kandydatów Levenshteina.

## Walidacja adresów z wykorzystaniem TERYT

Dodano walidację adresów opartą o dane referencyjne TERYT.

Walidacja działa na danych po preprocessingu, ponieważ dopiero tam adres jest rozbity i znormalizowany do postaci przydatnej do sprawdzania.

Sprawdzane są obecnie dwie reguły:

```text
ADDR_TERYT_CITY_EXISTS
ADDR_TERYT_STREET_EXISTS
```

Pierwsza reguła sprawdza, czy miejscowość występuje w danych TERYT.

Druga reguła sprawdza, czy ulica występuje w danej miejscowości. Jeżeli nie da się powiązać ulicy z konkretną miejscowością, system korzysta z ostrożniejszego sprawdzenia po indeksie ulic.

Walidacja korzysta z plików:

```text
SIMC.csv
ULIC.csv
```

Domyślna lokalizacja danych to:

```text
data/teryt
```

Można ją nadpisać zmienną środowiskową:

```text
TERYT_DIR
```

Jeżeli dane TERYT nie są dostępne, reguły TERYT nie blokują procesu. Dzięki temu lokalne środowisko może działać także bez pobranych plików referencyjnych.

## Jak działa walidacja TERYT

Walidacja TERYT buduje lokalny indeks miejscowości i ulic na podstawie plików referencyjnych.

Plik `SIMC.csv` jest wykorzystywany do sprawdzania miejscowości. System odczytuje nazwy miejscowości oraz ich identyfikatory, a następnie tworzy indeks pozwalający szybko sprawdzić, czy dana miejscowość istnieje.

Plik `ULIC.csv` jest wykorzystywany do sprawdzania ulic. System wiąże ulice z miejscowościami przez identyfikatory TERYT, dzięki czemu może sprawdzić nie tylko to, czy ulica istnieje gdziekolwiek, ale też czy występuje w danej miejscowości.

Wynik walidacji trafia do standardowej tabeli wyników:

```text
stg.Validation_Result
```

Dla błędnych danych zapisywane są między innymi komunikaty:

```text
ERR_TERYT_CITY_NOT_FOUND
ERR_TERYT_STREET_NOT_FOUND
```

Dzięki temu błędny adres nie przerywa procesu, tylko zostaje oznaczony konkretnym kodem błędu.

## Obsługa wariantów nazw ulic

Walidacja TERYT uwzględnia różnice w zapisie nazw ulic.

Obsługiwane są między innymi:

- prefiksy typu `ul.`, `ulica`, `al.`, `aleja`, `os.`, `plac`,
- normalizacja wielkości liter,
- polskie znaki,
- wariant zapisu patrona w kolejności spotykanej w danych użytkownika i w TERYT.

Przykład:

```text
UL ŻÓŁKIEWSKIEGO STANISŁAWA
UL STANISŁAWA ŻÓŁKIEWSKIEGO
```

Oba warianty mogą zostać rozpoznane jako ta sama ulica, jeżeli odpowiadają wpisowi w TERYT.

## Znaczenie walidacji TERYT

Walidacja adresów przez TERYT zwiększa wiarygodność danych przed etapem goldenizacji.

Bez tej walidacji system może jedynie sprawdzić, czy pole adresowe ma poprawny format. Po dodaniu TERYT może również ocenić, czy miejscowość i ulica mają sens względem oficjalnego rejestru.

Jest to ważne dla późniejszego matchingu i goldenizacji, ponieważ adres jest atrybutem dynamicznym. Nie powinien samodzielnie decydować o tożsamości rekordu, ale może wzmacniać lub osłabiać dopasowanie.

Przykładowo:

- zgodny PESEL i różny adres nadal mogą oznaczać tę samą osobę,
- podobna nazwa firmy i zgodny adres mogą wzmocnić dopasowanie,
- nieistniejąca miejscowość albo ulica powinny obniżyć zaufanie do danych adresowych.

## Schemat finalny `gold`

Do skryptu inicjalizującego MSSQL dodano schemat:

```text
gold
```

Schemat zawiera tabele docelowe dla golden recordów, między innymi:

- `gold.DimPerson`,
- `gold.DimParty`,
- `gold.DimAddress`,
- tabele identyfikatorów,
- tabele relacji,
- tabele lineage.

Jest to przygotowanie struktury pod kolejny etap prac. Aktualnie sita wskazują kandydatów do integracji, ale nie zapisują jeszcze finalnych rekordów do `gold.*`.

## Testy

Dodano testy obejmujące nowe elementy.

Dla matchingu testowane są między innymi:

- scoring dla osób,
- scoring dla podmiotów,
- silne dopasowania po PESEL i NIP,
- konflikty na identyfikatorach,
- klasyfikacja `AUTO_MERGE`, `REVIEW` i `CANDIDATE`,
- zapis kandydatów pierwszego sita,
- działanie drugiego sita Jaro-Winkler,
- przypadek, w którym Jaro-Winkler promuje dobre dopasowanie tekstowe,
- przypadek, w którym słabe dopasowanie tekstowe zostaje odrzucone.

Dla walidacji TERYT testowane są między innymi:

- poprawna miejscowość i ulica,
- wariant zapisu ulicy z odwróconą kolejnością patrona,
- nieistniejąca miejscowość,
- nieistniejąca ulica,
- zapis odpowiednich kodów błędów walidacji.

Testy potwierdzają, że nowe reguły nie przerywają procesu, tylko zapisują wynik walidacji w standardowy sposób.

## Aktualny stan procesu

Na dzień 28.05.2026 gotowy przepływ obejmuje:

```text
RAW -> staging -> preprocessing -> validation -> matching Levenshtein -> matching Jaro-Winkler
```

W ramach tego przepływu system potrafi:

- przyjąć dane z plików i relacyjnego źródła Oracle,
- zapisać dane źródłowe w RAW,
- zmapować dane do stagingu,
- przygotować wartości do porównywania w preprocessingu,
- zwalidować identyfikatory, formaty i wybrane reguły spójności,
- sprawdzić adresy względem TERYT,
- znaleźć kandydatów do integracji pierwszym sitem,
- doprecyzować kandydatów drugim sitem,
- zapisać wyniki obu sit w bazie.

## Co pozostaje do zrobienia

Następnym logicznym etapem jest właściwa integracja golden recordów.

Do wykonania pozostaje:

- grupowanie par kandydatów w klastry rekordów opisujących ten sam byt,
- wybór wartości zwycięskich dla każdego atrybutu osobno,
- zapis finalnych osób, podmiotów, adresów i relacji do tabel `gold.*`,
- zapis lineage pokazującego, z którego źródła pochodzi każda wybrana wartość,
- obsługa konfliktów wymagających decyzji ręcznej,
- przygotowanie endpointów odczytowych dla danych golden.

Najważniejszy postęp względem statusu z 22.05.2026 to przejście od przygotowanych danych po preprocessingu i walidacji do rzeczywistej identyfikacji kandydatów do goldenizacji. System posiada już dwa sita matchingu oraz walidację adresową opartą o zewnętrzne dane referencyjne TERYT.
