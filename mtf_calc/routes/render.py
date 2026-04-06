from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

from mtf_calc.services import SourceNotLoaded, WorkspaceService


def create_render_router(workspace_service: WorkspaceService) -> APIRouter:
    router = APIRouter(prefix="/render")

    @router.get("/source.float32")
    def source_buffer() -> Response:
        try:
            result = workspace_service.get_source_buffer()
        except SourceNotLoaded as error:
            return Response(
                content=str(error),
                media_type="text/plain",
                status_code=404,
            )

        return Response(
            content=result.content,
            media_type="application/octet-stream",
            headers=result.headers,
        )

    return router
