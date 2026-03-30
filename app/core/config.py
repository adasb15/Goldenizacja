from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "goldenizacja-api"
    app_env: str = "dev"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    mssql_server: str = "mssql"
    mssql_port: int = 1433
    mssql_db: str = "goldenizacja"
    mssql_user: str = "sa"
    mssql_password: str = "YourStrong!Passw0rd"

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_password"

    filestream_path: str = "/data/filestream"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    @property
    def sqlalchemy_database_url(self) -> str:
        driver = "ODBC Driver 18 for SQL Server"
        return (
            f"mssql+pyodbc://{self.mssql_user}:{self.mssql_password}@"
            f"{self.mssql_server}:{self.mssql_port}/{self.mssql_db}"
            f"?driver={driver.replace(' ', '+')}&TrustServerCertificate=yes"
        )

    @property
    def sqlalchemy_master_url(self) -> str:
        driver = "ODBC Driver 18 for SQL Server"
        return (
            f"mssql+pyodbc://{self.mssql_user}:{self.mssql_password}@"
            f"{self.mssql_server}:{self.mssql_port}/master"
            f"?driver={driver.replace(' ', '+')}&TrustServerCertificate=yes"
        )


settings = Settings()
