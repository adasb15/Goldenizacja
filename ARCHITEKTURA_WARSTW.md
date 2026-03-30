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
