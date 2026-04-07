from __future__ import annotations

from io import BytesIO

import numpy as np
from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from mtf_calc.pipeline import Pipeline
from mtf_calc.pages import render_load_page, render_stage_page, render_complete_page


def create_router(pipeline: Pipeline) -> APIRouter:
    router = APIRouter()

    # -- Pages --

    @router.get("/", response_class=HTMLResponse)
    def index() -> HTMLResponse:
        if pipeline.source is None:
            return HTMLResponse(content=render_load_page(pipeline))
        if pipeline.is_complete:
            return HTMLResponse(content=render_complete_page(pipeline))
        return HTMLResponse(content=render_stage_page(pipeline))

    # -- Actions --

    @router.post("/actions/load")
    async def load_source(request: Request) -> Response:
        body = await request.body()
        if not body:
            return Response(content="Empty payload", status_code=400)

        try:
            array = np.load(BytesIO(body), allow_pickle=False)
        except Exception:
            return Response(content="Not a valid .npy file", status_code=400)

        if not isinstance(array, np.ndarray) or array.dtype != np.float32 or array.ndim != 2:
            return Response(content="Expected 2D float32 array", status_code=400)

        pipeline.source = np.ascontiguousarray(array)
        pipeline.activate_current()
        return RedirectResponse(url="/", status_code=303)

    @router.post("/actions/next")
    async def advance_stage() -> Response:
        pipeline.complete_current()
        return RedirectResponse(url="/", status_code=303)

    @router.post("/actions/skip")
    async def skip_stage() -> Response:
        pipeline.skip_current()
        return RedirectResponse(url="/", status_code=303)

    # -- API --

    @router.get("/api/pipeline")
    def get_pipeline_state() -> JSONResponse:
        return JSONResponse(content={
            "stages": [s.model_dump() for s in pipeline.info()],
            "current": pipeline.current_index,
            "has_source": pipeline.source is not None,
            "is_complete": pipeline.is_complete,
        })

    @router.get("/api/source")
    def get_source_buffer() -> Response:
        if pipeline.source is None:
            return Response(content="No source loaded", status_code=404)
        data = pipeline.source
        return Response(
            content=data.tobytes(order="C"),
            media_type="application/octet-stream",
            headers={
                "X-Source-Rows": str(data.shape[0]),
                "X-Source-Cols": str(data.shape[1]),
            },
        )

    return router
