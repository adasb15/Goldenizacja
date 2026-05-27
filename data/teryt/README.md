# TERYT (GUS) - pliki do walidacji adresów

Ten katalog nie zawiera danych TERYT w repo.

Aby włączyć walidację adresów (miasto + ulica/osiedle/plac) w warstwie `validation`:

1. Pobierz aktualne pliki TERYT **SIMC** i **ULIC** (format CSV z separatorem `;`).
2. Umieść je w tym katalogu jako:
   - `SIMC.csv`
   - `ULIC.csv`
3. Ustaw w `.env`:
   - `TERYT_ENABLED=true`

Backend wczyta dane offline i doda do wyników walidacji reguły:
- `ADDR_TERYT_CITY_EXISTS`
- `ADDR_TERYT_STREET_EXISTS`

