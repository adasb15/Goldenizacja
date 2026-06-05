from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    # Trzymamy parametry API w .env, żeby ten sam obraz działał lokalnie i w Dockerze
    app_name: str = "goldenizacja-api"
    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    mssql_server: str = "mssql"
    mssql_port: int = 1433
    mssql_db: str = "goldenizacja"
    mssql_user: str = "sa"
    mssql_password: str
    mssql_encrypt: str = "yes"
    mssql_trust_server_certificate: str = "yes"


    # Konfigurujemy Neo4j dla modułu demo, żeby pokazać zapis dokumentu także w grafie
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    filestream_path: str = "/data/filestream"
    cors_origins: str = "http://localhost:5173"
    oracle_odbc_connection_string: str | None = None
    oracle_app_user: str = "insurance_core"
    oracle_app_password: str = "insurance_core"
    oracle_host: str = "oracle"
    oracle_port: int = 1521
    oracle_service_name: str = "FREEPDB1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def sqlalchemy_database_url(self) -> str:
        # Budujemy URL przez SQLAlchemy, żeby poprawnie złożyć hasło i parametry ODBC
        return URL.create(
            "mssql+pyodbc",
            username=self.mssql_user,
            password=self.mssql_password,
            host=self.mssql_server,
            port=self.mssql_port,
            database=self.mssql_db,
            query={
                "driver": "ODBC Driver 18 for SQL Server",
                "Encrypt": self.mssql_encrypt,
                "TrustServerCertificate": self.mssql_trust_server_certificate,
            },
        ).render_as_string(hide_password=False)


    @property
    def sqlalchemy_master_url(self) -> str:
        # Budujemy URL do master, żeby init_db mógł utworzyć bazę docelową przy pierwszym starcie
        return URL.create(
            "mssql+pyodbc",
            username=self.mssql_user,
            password=self.mssql_password,
            host=self.mssql_server,
            port=self.mssql_port,
            database="master",
            query={
                "driver": "ODBC Driver 18 for SQL Server",
                "Encrypt": self.mssql_encrypt,
                "TrustServerCertificate": self.mssql_trust_server_certificate,
            },
        ).render_as_string(hide_password=False)


    @property
    def cors_origins_list(self) -> list[str]:
        # Rozbijamy tekst z .env na listę originów, żeby CORS dostał format wymagany przez FastAPI
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
