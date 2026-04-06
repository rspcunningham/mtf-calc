from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from mtf_calc.config import AppConfig, load_config, save_config
from mtf_calc.workspace import WorkspaceStore


def create_config_router(workspace_store: WorkspaceStore | None = None) -> APIRouter:
    router = APIRouter(prefix="/config")

    @router.get("")
    def get_config() -> JSONResponse:
        config = load_config()
        return JSONResponse(content=config.to_dict())

    @router.post("")
    async def update_config(request: Request) -> Response:
        body = await request.json()
        freqs = body.get("frequencies")

        if not isinstance(freqs, list) or len(freqs) == 0:
            return Response(content="frequencies must be a non-empty list", status_code=400)

        try:
            parsed = [float(f) for f in freqs]
        except (TypeError, ValueError):
            return Response(content="all frequencies must be numbers", status_code=400)

        if any(f <= 0 for f in parsed):
            return Response(content="all frequencies must be positive", status_code=400)

        config = AppConfig(frequencies=sorted(parsed))
        save_config(config)
        if workspace_store is not None:
            workspace_store.update_config(config)
        return JSONResponse(content=config.to_dict())

    return router
