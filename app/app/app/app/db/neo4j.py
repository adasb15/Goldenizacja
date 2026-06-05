from neo4j import GraphDatabase

from app.core.config import settings


def get_neo4j_driver():
    # Tworzymy driver na żądanie, żeby moduł grafowy nie blokował startu głównego pipeline'u
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
