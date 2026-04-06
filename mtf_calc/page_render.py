from __future__ import annotations

import json
from html import escape

from typing import Any

from mtf_calc.services import SourceViewModel


def _base_page(*, page: str, title: str, body_html: str, config_json: str | None = None) -> str:
    config_block = ""
    if config_json is not None:
        config_block = (
            f'<script type="application/json" id="source-config">{config_json}</script>'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body data-page="{escape(page)}">
  {body_html}
  {config_block}
  <script type="module" src="/static/app.js"></script>
</body>
</html>
"""


def render_select_page() -> str:
    body_html = """
<div id="landing">
  <div class="brand">
    <div class="brand-name">Parasight</div>
    <div class="brand-sub">MTF Calculator</div>
  </div>

  <div id="landing-columns">
    <div class="landing-col">
      <div id="drop-zone">
        <div class="drop-icon"></div>
        <p>Drop <strong>.npy</strong> file or <span class="browse" id="browse-btn">browse</span></p>
      </div>
      <div class="landing-status" id="landing-status"></div>
    </div>

    <div class="landing-col">
      <div id="config-panel">
        <div class="config-header">Frequencies (1/m)</div>
        <div id="freq-list"></div>
        <div class="config-actions">
          <button class="config-btn" id="freq-add" type="button">+ Add</button>
          <button class="config-btn config-btn-save" id="freq-save" type="button">Save</button>
        </div>
      </div>
    </div>
  </div>

  <input type="file" id="file-input" accept=".npy">
</div>
"""
    return _base_page(
        page="select",
        title="PARASIGHT // MTF Calculator",
        body_html=body_html,
    )


def render_view_page(source: SourceViewModel, roi_sequence: list[dict[str, Any]]) -> str:
    config_json = json.dumps(
        {
            "revision": source.revision,
            "fileName": source.file_name,
            "sourceLabel": source.source_label,
            "byteLength": source.byte_length,
            "rows": source.rows,
            "cols": source.cols,
            "dtype": source.dtype,
            "dataMin": source.data_min,
            "dataMax": source.data_max,
            "histogram": source.histogram,
            "roiSequence": roi_sequence,
        },
        separators=(",", ":"),
    )

    body_html = f"""
<div id="viewer">
  <div id="toolbar">
    <span id="file-name">{escape(source.file_name)}</span>
    <span id="array-info">{source.rows}x{source.cols}</span>

    <div class="tb-spacer"></div>

    <div class="tb-group">
      <button class="tb-btn" id="btn-fit" type="button" title="Fit to view">Fit</button>
      <button class="tb-btn" id="btn-1x" type="button" title="1:1 pixels">1:1</button>
      <button class="tb-btn" id="btn-open" type="button" title="Open new file">Open</button>
      <form method="post" action="/actions/source/reset" class="tb-form">
        <button class="tb-btn" type="submit" title="Return to source selection">New</button>
      </form>
    </div>
  </div>

  <div id="histogram-container">
    <canvas id="histogram-canvas"></canvas>
    <button id="hist-auto-btn" type="button">Auto</button>
    <button id="hist-reset-btn" type="button">Reset</button>
    <span class="hist-label" id="hist-label-min"></span>
    <span class="hist-label" id="hist-label-max"></span>
    <div id="hist-wl-info"></div>
  </div>

  <div id="roi-bar">
    <span id="roi-prompt"></span>
    <span id="roi-progress"></span>
  </div>

  <div id="canvas-container">
    <canvas id="main-canvas"></canvas>
    <canvas id="roi-canvas"></canvas>
    <div id="inspector" style="display:none;"></div>
    <div id="zoom-indicator">1.00x</div>
  </div>

  <div id="roi-sidebar">
    <div id="roi-list"></div>
  </div>

  <div id="meta-strip">
    <div class="meta-block">
      <span class="meta-label">Shape</span>
      <span class="meta-value">{source.rows} x {source.cols}</span>
    </div>
    <div class="meta-block">
      <span class="meta-label">Dtype</span>
      <span class="meta-value">{escape(source.dtype)}</span>
    </div>
    <div class="meta-block">
      <span class="meta-label">Range</span>
      <span class="meta-value">{source.data_min:.4f} .. {source.data_max:.4f}</span>
    </div>
    <div class="meta-block">
      <span class="meta-label">Bytes</span>
      <span class="meta-value">{escape(_fmt_bytes(source.byte_length))}</span>
    </div>
  </div>

  <input type="file" id="file-input" accept=".npy">
</div>
"""
    return _base_page(
        page="view",
        title="PARASIGHT // MTF Calculator",
        body_html=body_html,
        config_json=config_json,
    )


def _fmt_bytes(byte_length: int) -> str:
    if byte_length <= 0:
        return "-"

    units = ["B", "KB", "MB", "GB"]
    size = float(byte_length)
    index = 0

    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1

    precision = 0 if index == 0 else 1
    return f"{size:.{precision}f} {units[index]}"
