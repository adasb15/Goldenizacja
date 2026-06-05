from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as core_router
from app.core.config import settings
from app.db.init_db import init_db
from app.layers.router import router as layers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Inicjalizujemy bazę przy starcie API, żeby kontener był gotowy bez ręcznego przygotowania tabel
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    # Ustawiamy CORS z konfiguracji, żeby front z innego portu mógł wołać API lokalnie
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Podpinamy router demo i router warstw, żeby oddzielić testowe endpointy od pipeline'u danych
app.include_router(core_router)
app.include_router(layers_router)
