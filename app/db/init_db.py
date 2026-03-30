import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.sql import engine
from app.models.base import Base


def _ensure_database_exists() -> None:
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
            Base.metadata.create_all(bind=engine)
            return
        except DBAPIError as exc:
            last_error = exc
            time.sleep(delay_s)

    if last_error is not None:
        raise last_error
