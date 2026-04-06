from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from mtf_calc.page_render import render_select_page, render_view_page
from mtf_calc.services import SourceNotLoaded, WorkspaceService


def create_pages_router(workspace_service: WorkspaceService) -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse, include_in_schema=False)
    def index() -> HTMLResponse:
        if not workspace_service.has_source():
            return HTMLResponse(content=render_select_page())

        try:
            source = workspace_service.current_source_view()
        except SourceNotLoaded:
            return HTMLResponse(content=render_select_page())

        roi_sequence = workspace_service.roi_sequence()
        return HTMLResponse(content=render_view_page(source, roi_sequence))

    return router
