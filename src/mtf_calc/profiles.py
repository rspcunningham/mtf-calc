import numpy as np
from collections.abc import Mapping
from numpy.typing import NDArray

from mtf_calc.models import Dim, FitResult, NormRegion, Profile, Roi


def get_norm(
    raw_image: NDArray[np.float32],
    norm_roi_dict: dict[NormRegion, Roi],
) -> tuple[float, float]:
    def roi_mean(roi: Roi) -> float:
        x0 = int(roi.top_left.x)
        x1 = int(roi.top_right.x)
        y0 = int(roi.top_left.y)
        y1 = int(roi.bottom_left.y)

        return float(raw_image[y0:y1, x0:x1].mean())

    return roi_mean(norm_roi_dict[0]), roi_mean(norm_roi_dict[1])

def extract(
    raw_image: NDArray[np.float32],
    *,
    bar_roi: Roi,
    norm_rois: Mapping[NormRegion, Roi],
    dim: Dim,
) -> Profile:
    del raw_image, bar_roi, norm_rois, dim
    raise NotImplementedError


def fit(
    profile: Profile,
    *,
    norm_rois: Mapping[NormRegion, Roi],
    n_harmonics: int,
) -> FitResult:
    del profile, norm_rois, n_harmonics
    raise NotImplementedError
