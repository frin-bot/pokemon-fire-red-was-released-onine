from __future__ import annotations

from math import sqrt
from typing import Sequence

from .models import Calibration, CropRect, DetectionResult

Pixel = Sequence[float]
Frame = Sequence[Sequence[Pixel]]


def classify_frame(frame_rgb: Frame, calibration: Calibration) -> DetectionResult:
    crop = _crop_frame(frame_rgb, calibration.crop)
    mean_rgb = _mean_rgb(crop)
    normal_distance = _distance(mean_rgb, calibration.normal_profile.mean_rgb)

    if calibration.shiny_profile is None:
        if normal_distance <= calibration.normal_max_distance:
            confidence = max(0.0, 1.0 - normal_distance / calibration.normal_max_distance)
            return DetectionResult("non_shiny", confidence, mean_rgb, normal_distance, None)
        confidence = min(1.0, normal_distance / max(calibration.normal_max_distance, 1.0))
        return DetectionResult("uncertain", confidence, mean_rgb, normal_distance, None)

    shiny_distance = _distance(mean_rgb, calibration.shiny_profile.mean_rgb)
    distance_delta = abs(normal_distance - shiny_distance)
    confidence = distance_delta / max(normal_distance, shiny_distance, 1.0)

    if distance_delta < calibration.decision_margin or confidence < calibration.confidence_threshold:
        return DetectionResult("uncertain", confidence, mean_rgb, normal_distance, shiny_distance)

    if shiny_distance < normal_distance:
        return DetectionResult("shiny", confidence, mean_rgb, normal_distance, shiny_distance)

    return DetectionResult("non_shiny", confidence, mean_rgb, normal_distance, shiny_distance)


def mean_rgb_for_crop(frame_rgb: Frame, crop_rect: CropRect) -> tuple[float, float, float]:
    return _mean_rgb(_crop_frame(frame_rgb, crop_rect))


def _crop_frame(frame_rgb: Frame, crop_rect: CropRect) -> list[list[Pixel]]:
    left, top, right, bottom = crop_rect.bounds()
    if left < 0 or top < 0 or crop_rect.width <= 0 or crop_rect.height <= 0:
        raise ValueError("crop rectangle must be positive and inside the frame")
    rows = [list(row[left:right]) for row in frame_rgb[top:bottom]]
    if len(rows) != crop_rect.height or any(len(row) != crop_rect.width for row in rows):
        raise ValueError("crop rectangle extends outside the frame")
    return rows


def _mean_rgb(crop: Frame) -> tuple[float, float, float]:
    total_r = 0.0
    total_g = 0.0
    total_b = 0.0
    count = 0

    for row in crop:
        for pixel in row:
            total_r += float(pixel[0])
            total_g += float(pixel[1])
            total_b += float(pixel[2])
            count += 1

    if count == 0:
        raise ValueError("cannot classify an empty crop")

    return (total_r / count, total_g / count, total_b / count)


def _distance(left: tuple[float, float, float], right: tuple[float, float, float]) -> float:
    return sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))
