from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
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


    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str

    filestream_path: str = "/data/filestream"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def sqlalchemy_database_url(self) -> str:
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
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
