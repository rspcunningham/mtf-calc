"""Server-rendered HTML pages for each pipeline stage."""

from __future__ import annotations

import json
from html import escape
from typing import Any

from mtf_calc.pipeline import Pipeline, StageInfo, StageStatus


def _stage_header(stages: list[StageInfo], current: int) -> str:
    """Render the pipeline progress header."""
    items = []
    for s in stages:
        cls = f"stage-{s.status.value}"
        if s.index == current:
            cls += " stage-current"
        items.append(
            f'<div class="stage-item {cls}" data-index="{s.index}">'
            f'<span class="stage-num">{s.index}</span>'
            f'<span class="stage-title">{escape(s.title)}</span>'
            f'</div>'
        )
    return f'<div id="stage-header">{"".join(items)}</div>'


def _base_page(*, pipeline: Pipeline, body_html: str, title: str = "MTF Calculator") -> str:
    stages = pipeline.info()
    current = pipeline.current_index
    header = _stage_header(stages, current)

    pipeline_json = json.dumps(
        {"stages": [s.model_dump() for s in stages], "current": current},
        separators=(",", ":"),
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
  {header}
  <div id="stage-content">
    {body_html}
  </div>
  <script type="application/json" id="pipeline-state">{pipeline_json}</script>
  <script type="module" src="/static/app.js"></script>
</body>
</html>
"""


def render_load_page(pipeline: Pipeline) -> str:
    """Landing page: load a source .npy file."""
    body = """
<div class="stage-panel">
  <div class="stage-heading">Load Source</div>
  <div class="stage-body">
    <div id="drop-zone">
      <div class="drop-icon"></div>
      <p>Drop <strong>.npy</strong> file or <span class="browse" id="browse-btn">browse</span></p>
    </div>
    <div id="landing-status" class="landing-status"></div>
  </div>
  <input type="file" id="file-input" accept=".npy">
</div>
"""
    return _base_page(pipeline=pipeline, body_html=body)


def render_stage_page(pipeline: Pipeline) -> str:
    """Render the page for the current active stage."""
    if pipeline.source is None:
        return render_load_page(pipeline)

    stage = pipeline.current_stage
    body = f"""
<div class="stage-panel">
  <div class="stage-heading">{escape(stage.title)}</div>
  <div class="stage-body">
    <p class="stage-placeholder">Stage content will go here.</p>
  </div>
  <div class="stage-actions">
    <button class="btn-next" id="btn-next" type="button">Next</button>
  </div>
</div>
"""
    return _base_page(pipeline=pipeline, body_html=body)


def render_complete_page(pipeline: Pipeline) -> str:
    """Render the final completion page."""
    body = """
<div class="stage-panel">
  <div class="stage-heading">Pipeline Complete</div>
  <div class="stage-body">
    <p class="stage-placeholder">All stages finished.</p>
  </div>
</div>
"""
    return _base_page(pipeline=pipeline, body_html=body)
