import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.sql import engine
from app.layers.ingestion import models as ingestion_models  # noqa: F401
from app.layers.integration_golden import models as integration_golden_models  # noqa: F401
from app.layers.preprocessing import models as preprocessing_models  # noqa: F401
from app.layers.staging_validation import models as staging_validation_models  # noqa: F401
from app.layers.validation import models as validation_models  # noqa: F401
from app.models.base import Base


def _ensure_database_exists() -> None:
    # Zakładamy bazę z poziomu aplikacji, żeby świeże środowisko Dockerowe samo wystartowało
    master_engine = create_engine(settings.sqlalchemy_master_url, pool_pre_ping=True)
    create_sql = text(
        "IF DB_ID(:db_name) IS NULL "
        "BEGIN "
        "DECLARE @sql NVARCHAR(MAX) = N'CREATE DATABASE [' + :db_name + N']'; "
        "EXEC(@sql); "
        "END"
    )
    with master_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.execute(create_sql, {"db_name": settings.mssql_db})


def init_db() -> None:
    attempts = 15
    delay_s = 2
    last_error: Exception | None = None

    for _ in range(attempts):
        try:
            _ensure_database_exists()
            # Tworzymy tabele z modeli SQLAlchemy, żeby podstawowe metadane istniały przed testami API
            Base.metadata.create_all(bind=engine)
            return
        except DBAPIError as exc:
            # Ponawiamy połączenie z SQL Serverem, żeby API nie padło gdy baza startuje wolniej
            last_error = exc
            time.sleep(delay_s)

    if last_error is not None:
        raise last_error
