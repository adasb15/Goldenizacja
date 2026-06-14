# D-01. Architektura komponentów

```mermaid
flowchart LR
    U["Operator procesu"]
    B["Użytkownik przeglądarki"]
    C["Klient API / Swagger"]
    FILES[("Syntetyczne pliki danych<br/>CSV / JSON / XML / XLSX")]
    TERYT[("Dane referencyjne TERYT<br/>SIMC / ULIC")]

    subgraph LOCAL["Środowisko lokalne zdefiniowane w Docker Compose"]
        FE["Frontend React / Vite<br/>widoki walidacji i matchingu"]
        AF["Apache Airflow<br/>DAG goldenizacja_pipeline"]

        subgraph API["FastAPI"]
            CORE["Endpointy demonstracyjne"]
            ING["ingestion"]
            STG["staging_validation"]
            PRE["preprocessing"]
            VAL["validation"]
            GOLD["integration_golden"]
            ANA["analytics<br/>szkielet"]
            SERV["serving<br/>odczyt Golden Record i wyników procesu"]
        end

        MSSQL[("Microsoft SQL Server<br/>meta / raw / stg / gold")]
        ORACLE[("Oracle Insurance Core<br/>syntetyczne źródło relacyjne")]
        NEO[("Neo4j<br/>komponent demonstracyjny")]
    end

    U -->|"uruchomienie i parametry"| AF
    B -->|"HTTP"| FE
    FE -->|"GET /layers/serving/validation-results<br/>GET /layers/serving/match-results/*"| SERV
    C -->|"REST GET"| SERV

    FILES -->|"odczyt pliku"| AF
    TERYT -->|"upload plików"| AF
    AF -->|"wywołania HTTP"| ING
    AF -->|"wywołania HTTP"| STG
    AF -->|"wywołania HTTP"| PRE
    AF -->|"wywołania HTTP"| VAL
    AF -->|"wywołania HTTP"| GOLD

    ING -->|"zapytania źródłowe"| ORACLE

    ING --> MSSQL
    STG --> MSSQL
    PRE --> MSSQL
    VAL --> MSSQL
    GOLD --> MSSQL

    ING --> STG
    STG --> PRE
    PRE --> VAL
    VAL --> GOLD
    GOLD -.->|"brak kompletnej logiki"| ANA
    GOLD --> SERV
    SERV -->|"odczyt"| MSSQL

    CORE -.->|"demonstracyjny zapis dokumentów"| NEO

    subgraph OS["Przygotowane, nieprzetestowane zasoby OpenShift"]
        OSM["Manifesty API, frontend, Airflow,<br/>SQL Server, Neo4j, PVC i Route"]
        NOTE["Brak Oracle i pełnej weryfikacji<br/>zgodności z aktualnym środowiskiem"]
        OSM --- NOTE
    end

    AF -.->|"częściowe odwzorowanie środowiska"| OSM

    classDef active fill:#dcefe2,stroke:#287a45,color:#173d25;
    classDef database fill:#dce9f7,stroke:#326a9a,color:#17364f;
    classDef partial fill:#fff0cc,stroke:#a87500,color:#5c4300;
    classDef unverified fill:#f3e2e2,stroke:#9a4646,color:#552626;

    class FE,AF,CORE,ING,STG,PRE,VAL,GOLD,SERV active;
    class MSSQL,ORACLE database;
    class ANA,NEO partial;
    class OSM,NOTE unverified;
```

## Legenda

- Zielony: komponent używany i zweryfikowany w środowisku lokalnym.
- Niebieski: baza danych uczestnicząca w potwierdzonym przepływie.
- Żółty: komponent częściowy albo demonstracyjny.
- Czerwony: zasoby przygotowane, ale niezweryfikowane na docelowym środowisku.

## Uwagi

1. Neo4j nie uczestniczy w głównym procesie goldenizacji.
2. Warstwa `serving` udostępnia dane wynikowe przez REST, natomiast `analytics` pozostaje szkieletem.
3. Manifesty OpenShift nie zostały przetestowane i nie obejmują Oracle.
4. Airflow komunikuje się z FastAPI przez HTTP, a nie przez bezpośredni dostęp do SQL Servera.
