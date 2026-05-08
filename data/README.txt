Syntetyczne dane rejestrowe do testow golden record/entity matching.

Uklad:
- csv/json/xml/xlsx zawieraja rozne rekordy.
- Lacznie kazdy rejestr ma 800 rekordow: csv=200, json=200, xml=200, xlsx=200.
- CSV zapisane jako UTF-8 z BOM.
- XML zapisane jako UTF-8 z nazwami pol w atrybucie name dla bezpieczenstwa parserow.
- XLSX zapisane jako prosty plik OpenXML z wartosciami tekstowymi.
- GLEIF jest scalony do jednego pliku z kolumnami relacji direct/ultimate parent.
- KRS zawiera do 10 slotow dla osob/podmiotow powiazanych i daty relacji DataOd/DataDo.
- Adresy bazowe sa dobierane z kuratorowanej listy realnych kombinacji:
  wojewodztwo, powiat, gmina, miejscowosc, ulica i kod pocztowy.
- W danych wystepuja kontrolowane anomalie:
  pojedyncze literowki w ok. 2% rekordow, braki elementow adresu,
  ok. 0.75% niepoprawnych adresow oraz ok. 1-2% bledow/brakow identyfikatorow.
- Dane sa w pelni syntetyczne.

Regeneracja:
- node scripts/refine_synthetic_data.js
