# OpenShift Deployment

Ten katalog zawiera manifesty OpenShift dla projektu `goldenizacja`.

## Co jest w środku

- `01-configmap.yaml` - konfiguracja aplikacji
- `02-secrets.yaml` - hasła do MSSQL i Neo4j
- `03-pvc.yaml` - wolumeny persistent
- `04-mssql.yaml` - SQL Server (Deployment + Service)
- `05-neo4j.yaml` - Neo4j (Deployment + Service)
- `06-api.yaml` - FastAPI (Deployment + Service)
- `07-adminer.yaml` - Adminer (Deployment + Service)
- `09-frontend.yaml` - React frontend (Deployment + Service)
- `10-airflow.yaml` - Airflow (Deployment + Service)
- `11-airflow-dags-configmap.yaml` - przykładowy DAG
- `08-routes.yaml` - publiczne trasy OpenShift

## Jak wdrożyć

1. Zaloguj się i wybierz projekt:

```bash
oc login <cluster-url>
oc project <twoj-projekt>
```

2. Wgraj zasoby:

```bash
oc apply -f openshift/01-configmap.yaml
oc apply -f openshift/02-secrets.yaml
oc apply -f openshift/03-pvc.yaml
oc apply -f openshift/04-mssql.yaml
oc apply -f openshift/05-neo4j.yaml
oc apply -f openshift/07-adminer.yaml
oc apply -f openshift/11-airflow-dags-configmap.yaml
oc apply -f openshift/10-airflow.yaml
```

3. Zbuduj/podstaw obrazy API i Frontendu:

```bash
# ważne: podmień projekt w 06-api.yaml i 09-frontend.yaml (REPLACE_WITH_PROJECT)
# ważne: podmień hosty w 01-configmap.yaml (REPLACE_API_ROUTE, REPLACE_FRONTEND_ROUTE)
oc apply -f openshift/06-api.yaml
oc apply -f openshift/09-frontend.yaml
oc apply -f openshift/08-routes.yaml
```

4. Sprawdź rollout:

```bash
oc get pods
oc get svc
oc get route
```

## Ważne uwagi

- `06-api.yaml` używa obrazu z wewnętrznego rejestru OpenShift. Podmień `REPLACE_WITH_PROJECT`.
- `09-frontend.yaml` używa obrazu z wewnętrznego rejestru OpenShift. Podmień `REPLACE_WITH_PROJECT`.
- Oczekiwane nazwy obrazów: `goldenizacja-api:latest` i `goldenizacja-frontend:latest`.
- Przy zmianie kodu API użyj nowego image taga lub `oc rollout restart deployment/goldenizacja-api`.
- Przy zmianie kodu frontendu użyj nowego image taga lub `oc rollout restart deployment/goldenizacja-frontend`.
- Jeśli klaster blokuje uruchomienie MSSQL/Neo4j na domyślnym SCC, może być potrzebna korekta SecurityContext/SCC.
