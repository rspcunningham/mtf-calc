from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from threading import RLock
from typing import Any

import numpy as np

from mtf_calc.config import AppConfig


HIST_BINS = 256


class WorkspaceError(Exception):
    """Base exception for workspace-domain failures."""


class InvalidSourceError(WorkspaceError):
    """Raised when a source payload cannot be accepted into the workspace."""


class NoSourceLoadedError(WorkspaceError):
    """Raised when source-dependent operations run without a loaded source."""


class InvalidROIError(WorkspaceError):
    """Raised when an ROI rect is invalid."""


Rect = tuple[int, int, int, int]  # (row, col, height, width)


@dataclass(slots=True)
class NormROI:
    kind: str  # "black" | "white"
    rect: Rect | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "rect": _rect_dict(self.rect),
        }


@dataclass(slots=True)
class BarROI:
    frequency: float  # 1/m
    axis: str  # "h" | "v"
    rect: Rect | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "frequency": self.frequency,
            "axis": self.axis,
            "rect": _rect_dict(self.rect),
        }

    @property
    def key(self) -> str:
        return f"bar-{self.frequency}-{self.axis}"


def _rect_dict(rect: Rect | None) -> dict[str, int] | None:
    if rect is None:
        return None
    return {"row": rect[0], "col": rect[1], "height": rect[2], "width": rect[3]}


@dataclass(slots=True)
class SourceRecord:
    revision: int
    file_name: str
    source_label: str
    byte_length: int
    rows: int
    cols: int
    dtype: str
    data_min: float
    data_max: float
    histogram: list[int]
    array: np.ndarray = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "fileName": self.file_name,
            "sourceLabel": self.source_label,
            "byteLength": self.byte_length,
            "rows": self.rows,
            "cols": self.cols,
            "dtype": self.dtype,
            "dataMin": self.data_min,
            "dataMax": self.data_max,
            "histogram": self.histogram,
        }


class WorkspaceStore:
    def __init__(self, config: AppConfig) -> None:
        self._lock = RLock()
        self._config = config
        self._source: SourceRecord | None = None
        self._source_revision = 0
        self._norm_rois: dict[str, NormROI] = {
            "black": NormROI(kind="black"),
            "white": NormROI(kind="white"),
        }
        self._bar_rois: list[BarROI] = self._build_bar_rois()

    def _build_bar_rois(self) -> list[BarROI]:
        rois = []
        for freq in self._config.frequencies:
            rois.append(BarROI(frequency=freq, axis="h"))
            rois.append(BarROI(frequency=freq, axis="v"))
        return rois

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            self._config = config
            self._bar_rois = self._build_bar_rois()

    def roi_sequence(self) -> list[dict[str, Any]]:
        with self._lock:
            seq: list[dict[str, Any]] = []
            for kind in ("black", "white"):
                roi = self._norm_rois[kind]
                seq.append({"key": kind, "type": "norm", **roi.to_dict()})
            for bar in self._bar_rois:
                seq.append({"key": bar.key, "type": "bar", **bar.to_dict()})
            return seq

    def set_norm_roi(self, kind: str, rect: Rect) -> dict[str, Any]:
        with self._lock:
            if kind not in self._norm_rois:
                raise InvalidROIError(f"Unknown norm ROI kind: {kind}")
            self._validate_rect(rect)

            if kind == "white":
                black = self._norm_rois["black"]
                if black.rect is None:
                    raise InvalidROIError("Black square must be set before white.")
                rect = (rect[0], rect[1], black.rect[2], black.rect[3])

            self._norm_rois[kind] = NormROI(kind=kind, rect=rect)

            if kind == "black" and self._norm_rois["white"].rect is not None:
                white = self._norm_rois["white"]
                self._norm_rois["white"] = NormROI(
                    kind="white",
                    rect=(white.rect[0], white.rect[1], rect[2], rect[3]),
                )

            return self.roi_sequence()

    def set_bar_roi(self, frequency: float, axis: str, rect: Rect) -> dict[str, Any]:
        with self._lock:
            self._validate_rect(rect)
            for i, bar in enumerate(self._bar_rois):
                if bar.frequency == frequency and bar.axis == axis:
                    self._bar_rois[i] = BarROI(frequency=frequency, axis=axis, rect=rect)
                    return self.roi_sequence()
            raise InvalidROIError(f"No bar ROI for frequency={frequency}, axis={axis}")

    def clear_roi(self, key: str) -> dict[str, Any]:
        with self._lock:
            if key in self._norm_rois:
                self._norm_rois[key] = NormROI(kind=key)
                return self.roi_sequence()
            for i, bar in enumerate(self._bar_rois):
                if bar.key == key:
                    self._bar_rois[i] = BarROI(frequency=bar.frequency, axis=bar.axis)
                    return self.roi_sequence()
            raise InvalidROIError(f"Unknown ROI key: {key}")

    def clear_all_rois(self) -> dict[str, Any]:
        with self._lock:
            self._norm_rois = {
                "black": NormROI(kind="black"),
                "white": NormROI(kind="white"),
            }
            self._bar_rois = self._build_bar_rois()
            return self.roi_sequence()

    def _validate_rect(self, rect: Rect) -> None:
        if not self._source:
            raise NoSourceLoadedError("No source loaded.")
        row, col, height, width = rect
        if height <= 0 or width <= 0:
            raise InvalidROIError("ROI must have positive dimensions.")
        if row < 0 or col < 0:
            raise InvalidROIError("ROI origin must be non-negative.")
        if row + height > self._source.rows or col + width > self._source.cols:
            raise InvalidROIError("ROI extends outside the source array.")

    def has_source(self) -> bool:
        with self._lock:
            return self._source is not None

    def source_summary(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._source:
                return None
            return self._source.to_dict()

    def clear(self) -> None:
        with self._lock:
            self._source = None
            self.clear_all_rois()

    def load_source_bytes(
        self,
        *,
        payload: bytes,
        file_name: str,
        source_label: str,
    ) -> None:
        if not payload:
            raise InvalidSourceError("The uploaded file was empty.")

        try:
            array = np.load(BytesIO(payload), allow_pickle=False)
        except Exception as error:
            raise InvalidSourceError("Not a valid .npy file.") from error

        if not isinstance(array, np.ndarray):
            raise InvalidSourceError("Expected a NumPy array payload.")

        if array.dtype != np.float32:
            raise InvalidSourceError(f"Expected float32 data, got dtype={array.dtype}.")

        if array.ndim != 2:
            raise InvalidSourceError(f"Expected a 2D array, got shape {tuple(array.shape)}.")

        contiguous = np.ascontiguousarray(array)
        if not np.isfinite(contiguous).all():
            raise InvalidSourceError("Array contains NaN or infinite values.")

        data_min = float(contiguous.min())
        data_max = float(contiguous.max())
        if data_min < 0 or data_max > 1:
            raise InvalidSourceError(
                f"Expected values in [0, 1], got range {data_min:.4f} .. {data_max:.4f}.",
            )

        histogram, _ = np.histogram(contiguous, bins=HIST_BINS, range=(0.0, 1.0))

        with self._lock:
            self._source_revision += 1
            self._source = SourceRecord(
                revision=self._source_revision,
                file_name=file_name,
                source_label=source_label,
                byte_length=len(payload),
                rows=int(contiguous.shape[0]),
                cols=int(contiguous.shape[1]),
                dtype="float32",
                data_min=data_min,
                data_max=data_max,
                histogram=histogram.astype(np.int64).tolist(),
                array=contiguous,
            )
            self.clear_all_rois()

    def source_buffer(self) -> bytes:
        with self._lock:
            if not self._source:
                raise NoSourceLoadedError("No source array is loaded.")
            return self._source.array.tobytes(order="C")

