from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Włączamy pool_pre_ping, żeby połączenia SQL odżywały po restarcie kontenera bazy
engine = create_engine(settings.sqlalchemy_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    # Tworzymy sesję per request, żeby endpointy nie współdzieliły transakcji między wywołaniami
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
