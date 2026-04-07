# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAny=false

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage
from typing import cast

from mtf_calc.models import Anchor, Point, Roi


def find_anchor(raw_image: NDArray[np.float32]) -> Anchor:
    x1, y1, x2, y2 = _find_large_square(raw_image)
    return _refine_anchor(raw_image, x1, y1, x2, y2)


def _find_large_square(raw_image: NDArray[np.float32]) -> tuple[int, int, int, int]:
    mask = raw_image < 0.2
    labels, _ = cast(tuple[NDArray[np.int32], int], ndimage.label(mask))
    objects = cast(list[tuple[slice, slice] | None], ndimage.find_objects(labels))

    best_bbox: tuple[int, int, int, int] | None = None
    best_area = 0

    for label_index, slices in enumerate(objects, start=1):
        if slices is None:
            continue

        height = slices[0].stop - slices[0].start
        width = slices[1].stop - slices[1].start
        area = int(np.sum(labels[slices] == label_index))
        aspect_ratio = min(height, width) / max(height, width)
        fill_ratio = area / (height * width)

        if aspect_ratio > 0.8 and fill_ratio > 0.8 and area > best_area:
            best_area = area
            best_bbox = (
                slices[1].start,
                slices[0].start,
                slices[1].stop,
                slices[0].stop,
            )

    if best_bbox is None:
        raise RuntimeError("Could not find a reference square in the image")

    return best_bbox


def _refine_anchor(
    raw_image: NDArray[np.float32],
    x1: int,
    y1: int,
    x2: int,
    y2: int,
) -> Anchor:
    margin = 25
    roi_y1 = max(0, y1 - margin)
    roi_y2 = min(raw_image.shape[0] - 1, y2 + margin)
    roi_x1 = max(0, x1 - margin)
    roi_x2 = min(raw_image.shape[1] - 1, x2 + margin)
    roi = raw_image[roi_y1 : roi_y2 + 1, roi_x1 : roi_x2 + 1]

    smoothed = cast(NDArray[np.float64], ndimage.gaussian_filter(roi, 1.0))
    grad_x = cast(NDArray[np.float64], ndimage.sobel(smoothed, axis=1))
    grad_y = cast(NDArray[np.float64], ndimage.sobel(smoothed, axis=0))
    grad_mag = np.sqrt(grad_x**2 + grad_y**2)

    edge_mask = grad_mag > 0.15
    edge_y, edge_x = np.where(edge_mask)
    if len(edge_x) < 8:
        raise RuntimeError("Anchor edge detection produced too few edge points")

    grad_x_values = grad_x[edge_y, edge_x]
    grad_y_values = grad_y[edge_y, edge_x]

    roi_center_y = roi.shape[0] / 2
    roi_center_x = roi.shape[1] / 2

    horizontal_mask = np.abs(grad_y_values) > np.abs(grad_x_values)
    horizontal_x = edge_x[horizontal_mask]
    horizontal_y = edge_y[horizontal_mask]
    top_mask = horizontal_y < roi_center_y
    bottom_mask = horizontal_y >= roi_center_y

    vertical_mask = ~horizontal_mask
    vertical_x = edge_x[vertical_mask]
    vertical_y = edge_y[vertical_mask]
    left_mask = vertical_x < roi_center_x
    right_mask = vertical_x >= roi_center_x

    if not top_mask.any() or not bottom_mask.any() or not left_mask.any() or not right_mask.any():
        raise RuntimeError("Could not classify anchor edges")

    top_coeffs = np.polyfit(horizontal_x[top_mask], horizontal_y[top_mask], 1)
    bottom_coeffs = np.polyfit(horizontal_x[bottom_mask], horizontal_y[bottom_mask], 1)
    left_coeffs = np.polyfit(vertical_y[left_mask], vertical_x[left_mask], 1)
    right_coeffs = np.polyfit(vertical_y[right_mask], vertical_x[right_mask], 1)

    top_left = _intersect_hv(top_coeffs, left_coeffs, roi_x1, roi_y1)
    top_right = _intersect_hv(top_coeffs, right_coeffs, roi_x1, roi_y1)
    bottom_right = _intersect_hv(bottom_coeffs, right_coeffs, roi_x1, roi_y1)
    bottom_left = _intersect_hv(bottom_coeffs, left_coeffs, roi_x1, roi_y1)

    return Anchor(
        roi=Roi(
            top_left=top_left,
            top_right=top_right,
            bottom_left=bottom_left,
            bottom_right=bottom_right,
        )
    )


def _intersect_hv(
    horizontal_coeffs: NDArray[np.float64],
    vertical_coeffs: NDArray[np.float64],
    roi_x1: int,
    roi_y1: int,
) -> Point:
    h_slope, h_intercept = horizontal_coeffs
    v_slope, v_intercept = vertical_coeffs
    denominator = 1.0 - (v_slope * h_slope)

    if abs(denominator) < 1e-6:
        raise RuntimeError("Anchor line fit became degenerate")

    x = (v_slope * h_intercept + v_intercept) / denominator
    y = (h_slope * x) + h_intercept
    return Point(x=float(x + roi_x1), y=float(y + roi_y1))
