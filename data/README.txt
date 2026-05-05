Syntetyczne dane rejestrowe do testów golden record/entity matching.

Układ:
- csv/json/xml/xlsx zawierają różne rekordy.
- Łącznie każdy rejestr ma 500 rekordów: csv=130, json=130, xml=120, xlsx=120.
- CSV zapisane jako UTF-8 z BOM.
- XML zapisane jako UTF-8 z nazwami pól w atrybucie name dla bezpieczeństwa parserów.
- GLEIF jest scalony do jednego pliku z kolumnami relacji direct/ultimate parent.
- KRS zawiera do 10 slotów dla osób/podmiotów powiązanych i daty relacji DataOd/DataDo.
- W danych występują kontrolowane anomalie: pojedyncze literówki, brakujące pola, różne formaty telefonów/adresów, sporadyczne błędne sumy kontrolne PESEL/NIP/REGON.
- Dane są w pełni syntetyczne.
