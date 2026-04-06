from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from mtf_calc.services import InvalidSourcePayload, WorkspaceService


def create_actions_router(workspace_service: WorkspaceService) -> APIRouter:
    router = APIRouter(prefix="/actions")

    @router.post("/source/upload")
    async def upload_source(request: Request, name: str = "uploaded.npy") -> Response:
        payload = await request.body()

        try:
            workspace_service.load_uploaded_source(
                payload=payload,
                file_name=name,
            )
        except InvalidSourcePayload as error:
            return PlainTextResponse(str(error), status_code=400)

        return Response(status_code=204)

    @router.post("/source/reset")
    def reset_source() -> Response:
        workspace_service.reset()
        return RedirectResponse(url="/", status_code=303)

    return router
