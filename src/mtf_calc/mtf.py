from collections.abc import Mapping
from math import pi
from typing import cast

from mtf_calc.models import BarSection, FitResult, MtfPoint, MtfResult


def _first_harmonic_mtf(fit: FitResult) -> float:
    if not fit.harmonic_amplitudes:
        raise ValueError("Fit result is missing harmonic amplitudes.")

    ideal_amplitude = 2.0 / pi
    return abs(float(fit.harmonic_amplitudes[0])) / ideal_amplitude


def compute(results: Mapping[BarSection, FitResult]) -> MtfResult:
    if not results:
        raise ValueError("Cannot compute MTF: no fitted bar results were provided.")

    grouped: dict[tuple[int, int], dict[str, tuple[BarSection, FitResult]]] = {}

    for section, fit in results.items():
        key = (int(section.group), int(section.element))
        by_dim = grouped.setdefault(key, {})
        by_dim[section.dim] = (section, fit)

    mtf_points: list[MtfPoint] = []
    for _, by_dim in grouped.items():
        x_entry = by_dim.get("X")
        y_entry = by_dim.get("Y")
        if x_entry is None and y_entry is None:
            continue

        section = x_entry[0] if x_entry is not None else cast(tuple[BarSection, FitResult], y_entry)[0]
        mtf_x = _first_harmonic_mtf(x_entry[1]) if x_entry is not None else None
        mtf_y = _first_harmonic_mtf(y_entry[1]) if y_entry is not None else None
        avg_terms = [value for value in (mtf_x, mtf_y) if value is not None]
        mtf_avg = sum(avg_terms) / len(avg_terms) if avg_terms else None

        mtf_points.append(
            MtfPoint(
                lp_per_mm=float(section.frequency),
                line_width=float(section.line_width),
                mtf_x=mtf_x,
                mtf_y=mtf_y,
                mtf_avg=mtf_avg,
            )
        )

    if not mtf_points:
        raise ValueError("Cannot compute MTF: no usable fitted bar results were available.")

    mtf_points.sort(key=lambda point: point.lp_per_mm)
    return mtf_points
