# Platforma Goldenizacji Danych (FastAPI)

To jest backendowy projekt studencki pod platformę integracji i goldenizacji danych podmiotów/osób.
Repo jest przygotowane tak, żeby dało się go szybko uruchomić lokalnie, pokazać działający przepływ danych i dalej rozbudowywać zgodnie z prezentacją (`Pobranie -> Staging -> Integracja -> Analityka -> Prezentacja`).

## Co jest w projekcie i po co

W tym momencie projekt ma dwie warstwy:

1. Działający rdzeń API (testowe endpointy i podstawowy przepływ danych)
2. Szkielet docelowej architektury warstwowej pod pełną goldenizację

Rdzeń API pozwala:
- wrzucić plik CSV i dostać liczbę odczytanych wierszy,
- zapisać dokument (MSSQL + plik na wolumenie),
- wyszukać podobne rekordy (RapidFuzz),
- zapisać relację dokumentu w Neo4j.

Szkielet warstwowy odzwierciedla podział z prezentacji:
- `ingestion`
- `staging_validation`
- `integration_golden`
- `analytics`
- `serving`

Dzięki temu możesz pokazać zespołowi nie tylko "co działa", ale też "jak to będzie rosło" bez przebudowy całego repo od zera.

## Stack technologiczny

- Python 3.12
- FastAPI
- Pydantic
- SQLAlchemy + pyodbc
- MS SQL Server (Docker)
- Neo4j (Docker)
- RapidFuzz
- Docker Compose
- Adminer (panel www)

## Struktura katalogów

- `app/` - kod aplikacji FastAPI
- `app/api/` - obecne endpointy rdzenia
- `app/layers/` - warstwy docelowej architektury
- `app/db/` - połączenia i inicjalizacja baz
- `app/models/`, `app/repositories/`, `app/services/`, `app/schemas/` - klasyczny podział backendowy
- `tests/` - testy API
- `docker-compose.yml` - cały stack lokalny
- `Dockerfile` - obraz API
- `ARCHITEKTURA_WARSTW.md` - opis warstw pod prezentację

## Endpointy (co działa teraz)

- `GET /health`
- `POST /files/line-count` - przyjmuje tylko `.csv`, zwraca liczbę wierszy
- `POST /documents`
- `GET /documents`
- `GET /documents/search?q=...`

Endpointy techniczne warstw:
- `GET /layers/ingestion/status`
- `GET /layers/staging_validation/status`
- `GET /layers/integration_golden/status`
- `GET /layers/analytics/status`
- `GET /layers/serving/status`

## Jak uruchomić

1. Uruchom środowisko:

```bash
docker compose up -d
```

## Adminer + MSSQL

Dane logowania do SQL Server w Adminer:
- `System`: `MS SQL`
- `Serwer`: `mssql`
- `Użytkownik`: `sa`
- `Hasło`: wartość `MSSQL_PASSWORD` z `.env`
- `Baza`: `goldenizacja`

## Tryb developerski (bez rebuildu po każdej zmianie)

API działa na `uvicorn --reload`, a katalog `./app` jest podmontowany do kontenera.
To znaczy, że zmiany w kodzie Python ładują się automatycznie.

Rebuild (`docker compose up --build`) jest potrzebny tylko gdy zmienisz:
- `requirements.txt`
- `Dockerfile`

## Jak ten projekt ma się do wymagań z prezentacji/PDF

Zrobione teraz:
- działający backend i środowisko uruchomieniowe,
- podstawowy ingest CSV,
- baza relacyjna + grafowa,
- fundament pod warstwy goldenizacji.


## Uwagi praktyczne

- W projekcie używamy wariantu `file-stream-like` (wolumen Docker) jako prostego i stabilnego odpowiednika składowania plików.
- Pełny SQL Server FILESTREAM można dodać później, jeśli będzie wymagany przez docelowe środowisko.

# Architektura warstwowa (zgodna z prezentacją)

## Warstwy

1. ingestion
2. staging_validation
3. integration_golden
4. analytics
5. serving

## Struktura katalogów

```text
app/layers/
  ingestion/
    api.py
    service.py
    repository.py
    models.py
    schemas.py
    README.md
  staging_validation/
    api.py
    service.py
    repository.py
    models.py
    schemas.py
    README.md
  integration_golden/
    api.py
    service.py
    repository.py
    models.py
    schemas.py
    README.md
  analytics/
    api.py
    service.py
    repository.py
    models.py
    schemas.py
    README.md
  serving/
    api.py
    service.py
    repository.py
    models.py
    schemas.py
    README.md
  router.py
```

## Endpointy techniczne warstw

- `GET /layers/ingestion/status`
- `GET /layers/staging_validation/status`
- `GET /layers/integration_golden/status`
- `GET /layers/analytics/status`
- `GET /layers/serving/status`

Te endpointy służą jako techniczny szkielet. Logika biznesowa jest rozwijana w plikach `service.py` i `repository.py` każdej warstwy.
