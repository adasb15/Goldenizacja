Paczka syntetycznych danych rejestrowych.

Układ:
- csv/*.csv
- json/*.json
- xml/*.xml
- xlsx/*.xlsx

Zasada:
- dla każdego formatu wygenerowano osobny zestaw danych wejściowych;
- rekordy między formatami są różne, czyli CSV/JSON/XML/XLSX nie zawierają tych samych obserwacji;
- wewnątrz jednego formatu rejestry są powiązywalne przez identyfikatory źródłowe (PESEL, NIP, REGON, KRS, LEI);
- nazwy pól pozostawiono w stylu źródłowym, bez unifikacji;
- zastosowano kontrolowane anomalie: różne formaty telefonów, skróty nazw spółek, warianty adresów, wielkie litery, braki.

Liczność:
- w każdym formacie wygenerowano po 200 encji bazowych;
- liczba rekordów na plik zależy od rejestru (np. KRS/GLEIF zawierają tylko podmioty, które do nich pasują).
