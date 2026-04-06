from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mtf_calc.workspace import (
    InvalidROIError,
    InvalidSourceError,
    NoSourceLoadedError,
    WorkspaceStore,
)


class WorkspaceServiceError(Exception):
    """Base exception for service-layer failures."""


class InvalidSourcePayload(WorkspaceServiceError):
    """Raised when a user-provided source payload is invalid."""


class SourceNotLoaded(WorkspaceServiceError):
    """Raised when an operation requires a loaded source."""


class InvalidROI(WorkspaceServiceError):
    """Raised when an ROI operation fails."""


@dataclass(frozen=True, slots=True)
class SourceBufferResult:
    content: bytes
    headers: dict[str, str]


@dataclass(frozen=True, slots=True)
class SourceViewModel:
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


class WorkspaceService:
    def __init__(self, store: WorkspaceStore) -> None:
        self._store = store

    def has_source(self) -> bool:
        return self._store.has_source()

    def current_source_view(self) -> SourceViewModel:
        source = self._store.source_summary()
        if source is None:
            raise SourceNotLoaded("No source array is loaded.")

        return SourceViewModel(
            revision=int(source["revision"]),
            file_name=str(source["fileName"]),
            source_label=str(source["sourceLabel"]),
            byte_length=int(source["byteLength"]),
            rows=int(source["rows"]),
            cols=int(source["cols"]),
            dtype=str(source["dtype"]),
            data_min=float(source["dataMin"]),
            data_max=float(source["dataMax"]),
            histogram=[int(value) for value in source["histogram"]],
        )

    def reset(self) -> None:
        self._store.clear()

    def load_uploaded_source(self, *, payload: bytes, file_name: str) -> None:
        try:
            self._store.load_source_bytes(
                payload=payload,
                file_name=file_name,
                source_label="Local file",
            )
        except InvalidSourceError as error:
            raise InvalidSourcePayload(str(error)) from error

    def get_source_buffer(self) -> SourceBufferResult:
        try:
            content = self._store.source_buffer()
            source = self.current_source_view()
        except NoSourceLoadedError as error:
            raise SourceNotLoaded(str(error)) from error

        headers = {
            "X-Source-Revision": str(source.revision),
            "X-Source-Rows": str(source.rows),
            "X-Source-Cols": str(source.cols),
            "X-Source-Dtype": source.dtype,
        }

        return SourceBufferResult(content=content, headers=headers)

    def roi_sequence(self) -> list[dict[str, Any]]:
        return self._store.roi_sequence()

    def set_roi(self, key: str, rect: tuple[int, int, int, int]) -> list[dict[str, Any]]:
        try:
            if key in ("black", "white"):
                return self._store.set_norm_roi(key, rect)
            if key.startswith("bar-"):
                parts = key.split("-", 2)
                frequency = float(parts[1])
                axis = parts[2]
                return self._store.set_bar_roi(frequency, axis, rect)
            raise InvalidROI(f"Unknown ROI key: {key}")
        except (InvalidROIError, NoSourceLoadedError) as error:
            raise InvalidROI(str(error)) from error

    def clear_roi(self, key: str) -> list[dict[str, Any]]:
        try:
            return self._store.clear_roi(key)
        except InvalidROIError as error:
            raise InvalidROI(str(error)) from error

    def clear_all_rois(self) -> list[dict[str, Any]]:
        return self._store.clear_all_rois()
