from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DetectionLabel = Literal["non_shiny", "shiny", "uncertain"]


@dataclass(frozen=True)
class CropRect:
    x: int
    y: int
    width: int
    height: int

    def bounds(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass(frozen=True)
class ColorProfile:
    mean_rgb: tuple[float, float, float]


@dataclass(frozen=True)
class Calibration:
    starter: str
    crop: CropRect
    normal_profile: ColorProfile
    shiny_profile: ColorProfile | None = None
    confidence_threshold: float = 0.25
    decision_margin: float = 18.0
    normal_max_distance: float = 35.0


@dataclass(frozen=True)
class DetectionResult:
    label: DetectionLabel
    confidence: float
    mean_rgb: tuple[float, float, float]
    normal_distance: float
    shiny_distance: float | None = None


@dataclass(frozen=True)
class AttemptRecord:
    attempt: int
    timestamp: str
    starter: str
    result: DetectionResult
    screenshot_path: str | None = None

