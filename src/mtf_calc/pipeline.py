from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class StageStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class StageMode(str, Enum):
    RUN = "run"
    SKIP = "skip"


class StageInfo(BaseModel):
    """Serializable snapshot of a stage for the frontend."""
    index: int
    name: str
    title: str
    status: StageStatus
    mode: StageMode


class Stage:
    def __init__(self, name: str, title: str, mode: StageMode = StageMode.RUN) -> None:
        self.name = name
        self.title = title
        self.mode = mode
        self.status = StageStatus.PENDING
        self.result: Any = None

    def info(self, index: int) -> StageInfo:
        return StageInfo(
            index=index,
            name=self.name,
            title=self.title,
            status=self.status,
            mode=self.mode,
        )


class Pipeline:
    def __init__(self) -> None:
        self.stages: list[Stage] = [
            Stage("anchor", "Anchor Detection"),
            Stage("scale", "Scale Identification"),
            Stage("bar_locations", "Bar Locations"),
            Stage("bar_rois", "Bar ROI Refinement"),
            Stage("norm_rois", "Normalization ROIs"),
        ]
        self._current = 0
        self.source: Any = None  # loaded numpy array

    @property
    def current_index(self) -> int:
        return self._current

    @property
    def current_stage(self) -> Stage:
        return self.stages[self._current]

    @property
    def is_complete(self) -> bool:
        return self._current >= len(self.stages)

    def info(self) -> list[StageInfo]:
        return [stage.info(i) for i, stage in enumerate(self.stages)]

    def activate_current(self) -> None:
        """Mark the current stage as active."""
        if not self.is_complete:
            self.current_stage.status = StageStatus.ACTIVE

    def complete_current(self, result: Any = None) -> None:
        """Complete the current stage and advance."""
        if self.is_complete:
            return
        stage = self.current_stage
        stage.status = StageStatus.COMPLETE
        stage.result = result
        self._current += 1
        if not self.is_complete:
            self.activate_current()

    def skip_current(self) -> None:
        """Skip the current stage and advance."""
        if self.is_complete:
            return
        stage = self.current_stage
        stage.status = StageStatus.SKIPPED
        self._current += 1
        if not self.is_complete:
            self.activate_current()

    def get_result(self, name: str) -> Any:
        """Get the result of a completed stage by name."""
        for stage in self.stages:
            if stage.name == name:
                return stage.result
        return None
