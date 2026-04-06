from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from mtf_calc.config import load_config
from mtf_calc.routes import (
    create_actions_router,
    create_config_router,
    create_pages_router,
    create_render_router,
    create_roi_router,
)
from mtf_calc.services import WorkspaceService
from mtf_calc.workspace import WorkspaceStore


PACKAGE_DIR = Path(__file__).resolve().parent
UI_DIR = PACKAGE_DIR / "ui"


def create_app() -> FastAPI:
    config = load_config()
    workspace_store = WorkspaceStore(config)
    workspace_service = WorkspaceService(workspace_store)

    app = FastAPI(title="MTF Calculator", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=UI_DIR), name="static")
    app.include_router(create_pages_router(workspace_service))
    app.include_router(create_actions_router(workspace_service))
    app.include_router(create_render_router(workspace_service))
    app.include_router(create_config_router(workspace_store))
    app.include_router(create_roi_router(workspace_service))
    return app
