# pyright: reportAny=false, reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnusedCallResult=false
from __future__ import annotations

import atexit
from pathlib import Path
import threading
from collections.abc import Mapping
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
from mtf_calc.models import Anchor, BarSection, FitResult, MtfResult, NormRegion, Profile, Roi
from mtf_calc.profiles import evaluate_fit


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


def _roi_diagnostic_name(section: BarSection) -> str:
    dim = section.dim.lower()
    return f"g{int(section.group)}_e{int(section.element)}_{dim}.png"


def _roi_diagnostic_title(section: BarSection, fit: FitResult, *, rms_error: float) -> str:
    return (
        f"ROI Fit Diagnostic - Group {int(section.group)}, Element {int(section.element)}, "
        f"Dim {section.dim}, {section.frequency:.3f} lp/mm, "
        f"{len(fit.harmonic_amplitudes)} harmonics, RMSE {rms_error:.4f}"
    )


def _render_fit_diagnostic_figure(
    section: BarSection,
    profile: Profile,
    fit: FitResult,
):
    import matplotlib.pyplot as plt

    observed = np.asarray(profile.norm_values, dtype=np.float64)
    fitted = evaluate_fit(profile, fit)
    x = np.arange(observed.size, dtype=np.float64)
    residuals = observed - fitted
    rms_error = float(np.sqrt(np.mean(np.square(residuals))))

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(
        x,
        observed,
        marker="o",
        markersize=3,
        linewidth=1.5,
        color="#1f77b4",
        label="Real data",
    )
    ax.plot(
        x,
        fitted,
        linewidth=2.0,
        color="#d62728",
        label="Fitted curve",
    )
    ax.fill_between(x, observed, fitted, color="#d62728", alpha=0.12)
    ax.set_title(_roi_diagnostic_title(section, fit, rms_error=rms_error))
    ax.set_xlabel("Sample index")
    ax.set_ylabel("Normalized value")
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def save_fit_diagnostic_png(
    section: BarSection,
    profile: Profile,
    fit: FitResult,
    *,
    output_path: str | Path,
    dpi: int = 200,
) -> Path:
    import matplotlib.pyplot as plt

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig = _render_fit_diagnostic_figure(section, profile, fit)
    try:
        fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    finally:
        plt.close(fig)
    return output_path


def write_fit_diagnostic_pngs(
    roi_fits: Mapping[BarSection, tuple[Profile, FitResult]],
    *,
    output_dir: str | Path,
    dpi: int = 200,
) -> list[Path]:
    if not roi_fits:
        raise ValueError("Cannot write fit diagnostics: no ROI fits were provided.")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for section, (profile, fit) in sorted(
        roi_fits.items(),
        key=lambda item: (int(item[0].group), int(item[0].element), item[0].dim),
    ):
        written_paths.append(
            save_fit_diagnostic_png(
                section,
                profile,
                fit,
                output_path=output_dir / _roi_diagnostic_name(section),
                dpi=dpi,
            )
        )

    return written_paths


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
