from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST, PROJECT_DIR
from .routes import router
from .storage import read_key_json


@asynccontextmanager
async def lifespan(_app):
    """Validate the configured key file before accepting requests."""
    read_key_json()
    yield


def create_app():
    """Build and configure the FastAPI application."""
    app = FastAPI(title="SSH KMS", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    image_dir = PROJECT_DIR / "img"
    if image_dir.is_dir():
        app.mount("/img", StaticFiles(directory=image_dir), name="img")

    app.include_router(router)
    return app


app = create_app()
