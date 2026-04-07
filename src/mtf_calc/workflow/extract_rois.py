import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel

from mtf_calc.workflow.identify_bars import BarSetLocation, BarIdentificationResult
from mtf_calc.workflow.identify_scale import ScaleResult


class BarROI(BaseModel):
    """A quadrilateral ROI tightly framing a single bar set."""
    group: int
    element: int
    orientation: str
    # Four corners in image pixel coordinates (top-left, top-right, bottom-right, bottom-left)
    x1: float
    y1: float
    x2: float
    y2: float
    x3: float
    y3: float
    x4: float
    y4: float


class ROIResult(BaseModel):
    rois: list[BarROI]


def _extract_single_roi(
    data: np.ndarray,
    bar: BarSetLocation,
    scale: ScaleResult,
) -> BarROI:
    """Extract the ROI for a single bar set. Placeholder implementation."""
    # TODO: use VLM or manual user input to define the ROI quadrilateral
    raise NotImplementedError("ROI extraction not yet implemented")


def main(
    data: np.ndarray,
    scale: ScaleResult,
    bars: BarIdentificationResult,
) -> ROIResult:
    print(f"Running stage 3: extract_rois ({len(bars.bar_sets)} bars)")

    rois: list[BarROI] = []
    with ThreadPoolExecutor() as pool:
        futures = {
            pool.submit(_extract_single_roi, data, bar, scale): bar
            for bar in bars.bar_sets
        }
        for future in as_completed(futures):
            bar = futures[future]
            roi = future.result()
            print(f"  G{bar.group}E{bar.element} {bar.orientation} — ROI extracted")
            rois.append(roi)

    result = ROIResult(rois=rois)
    print(f"  Total ROIs: {len(result.rois)}")
    return result
