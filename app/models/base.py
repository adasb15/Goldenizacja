from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Definiujemy wspólną bazę modeli, żeby init_db mógł zebrać metadane wszystkich tabel
    pass
