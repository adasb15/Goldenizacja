from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router as core_router
from app.core.config import settings
from app.db.init_db import init_db
from app.layers.router import router as layers_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(core_router)
app.include_router(layers_router)
