from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response

from mtf_calc.services import InvalidROI, WorkspaceService


def create_roi_router(workspace_service: WorkspaceService) -> APIRouter:
    router = APIRouter(prefix="/actions/roi")

    @router.get("")
    def get_rois() -> JSONResponse:
        return JSONResponse(content=workspace_service.roi_sequence())

    @router.post("")
    async def set_roi(request: Request) -> Response:
        body = await request.json()
        key = body.get("key")
        rect = body.get("rect")

        if not key or not rect:
            return Response(content="key and rect required", status_code=400)

        try:
            row, col, height, width = int(rect["row"]), int(rect["col"]), int(rect["height"]), int(rect["width"])
        except (KeyError, TypeError, ValueError):
            return Response(content="rect must have row, col, height, width", status_code=400)

        try:
            seq = workspace_service.set_roi(key, (row, col, height, width))
        except InvalidROI as error:
            return Response(content=str(error), status_code=400)

        return JSONResponse(content=seq)

    @router.delete("/{key}")
    def clear_roi(key: str) -> Response:
        try:
            seq = workspace_service.clear_roi(key)
        except InvalidROI as error:
            return Response(content=str(error), status_code=400)

        return JSONResponse(content=seq)

    return router
