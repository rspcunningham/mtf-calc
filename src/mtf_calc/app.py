from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mtf_calc.pipeline import Pipeline
from mtf_calc.routes import create_router


PACKAGE_DIR = Path(__file__).resolve().parent
UI_DIR = PACKAGE_DIR / "ui"


def create_app() -> FastAPI:
    pipeline = Pipeline()

    app = FastAPI(title="MTF Calculator", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")
    app.include_router(create_router(pipeline))
    return app
