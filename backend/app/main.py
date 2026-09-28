from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.previews_dir.mkdir(parents=True, exist_ok=True)
    settings.reference_slides_dir.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Beautify Slides API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix=settings.api_prefix)
settings.previews_dir.mkdir(parents=True, exist_ok=True)
app.mount("/previews", StaticFiles(directory=settings.previews_dir), name="previews")
