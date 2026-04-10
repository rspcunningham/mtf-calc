# pyright: reportAny=false, reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
from __future__ import annotations

import atexit
from pathlib import Path
import threading
from typing import cast

import numpy as np
from numpy.typing import NDArray
from viewer import HtmlViewer

from mtf_calc._roi_tools import (
    build_select_roi_config,
    build_show_anchor_config,
    build_show_rois_config,
    roi_from_payload,
)
from mtf_calc._roi_picker_page import get_roi_picker_html
from mtf_calc.models import Anchor, BarSection, MtfResult, NormRegion
from mtf_calc.models import Roi


_viewer: HtmlViewer | None = None
_viewer_lock = threading.Lock()


def select_roi(
    raw_image: NDArray[np.float32],
    size_ref: Roi | None = None,
    prompt: str | None = None,
) -> Roi:
    result = _get_viewer().show(
        get_roi_picker_html(),
        request=build_select_roi_config(raw_image, size_ref=size_ref, prompt=prompt),
        title="Select ROI",
    )
    if not isinstance(result, dict):
        raise RuntimeError("Visualization host returned an invalid ROI result")
    return roi_from_payload(cast(dict[str, object], result))


def show_anchor(raw_image: NDArray[np.float32], anchor: Anchor) -> None:
    _ = _get_viewer().show(
        get_roi_picker_html(),
        request=build_show_anchor_config(raw_image, anchor),
        title="Anchor Preview",
    )


def show_rois(
    raw_image: NDArray[np.float32],
    *,
    anchor: Anchor,
    norm_rois: dict[NormRegion, Roi],
    bar_rois: dict[BarSection, Roi],
) -> None:
    _ = _get_viewer().show(
        get_roi_picker_html(),
        request=build_show_rois_config(
            raw_image,
            anchor=anchor,
            norm_rois=norm_rois,
            bar_rois=bar_rois,
        ),
        title="Seeded ROI Review",
    )


def close() -> None:
    global _viewer

    with _viewer_lock:
        if _viewer is None:
            return
        _viewer.close()
        _viewer = None


def _close_for_atexit() -> None:
    global _viewer

    with _viewer_lock:
        if _viewer is None:
            return
        _viewer.close()
        _viewer = None


def _get_viewer() -> HtmlViewer:
    global _viewer

    with _viewer_lock:
        if _viewer is None:
            _viewer = HtmlViewer()
        return _viewer


_ = atexit.register(_close_for_atexit)


def show_mtf_graph(mtf_result: MtfResult, *, output_path: str | None = None) -> None:
    if not mtf_result:
        raise ValueError("Cannot show MTF graph: the computed Stage 7 result is empty.")

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(10, 6))
    plotted_values: list[float] = []

    for field, label, color in (
        ("mtf_x", "MTF X", "#0b7285"),
        ("mtf_y", "MTF Y", "#c92a2a"),
        ("mtf_avg", "MTF Avg", "#2b8a3e"),
    ):
        xs: list[float] = []
        ys: list[float] = []

        for point in mtf_result:
            value = getattr(point, field)
            if value is None:
                continue
            xs.append(point.lp_per_mm)
            ys.append(value)

        if not ys:
            continue

        plotted_values.extend(ys)
        ax.plot(xs, ys, marker="o", linewidth=2, label=label, color=color)

    ax.set_title("MTF Response")
    ax.set_xlabel("Spatial Frequency (lp/mm)")
    ax.set_ylabel("MTF")
    ax.grid(True, alpha=0.3)
    if plotted_values:
        ax.legend()
    ax.set_ylim(0.0, max(1.05, max(plotted_values, default=1.0) * 1.1))
    fig.tight_layout()

    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200, bbox_inches="tight")

    plt.show()
    plt.close(fig)
