from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from .models import AttemptRecord, DetectionResult


class RunLogger:
    def __init__(self, run_dir: Path, starter: str):
        self.run_dir = Path(run_dir)
        self.starter = starter
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "screenshots").mkdir(exist_ok=True)
        self.state_path = self.run_dir / "current-run.json"
        self.csv_path = self.run_dir / "attempts.csv"
        self.attempt_count = self._load_attempt_count()
        self._ensure_csv_header()

    def record_attempt(
        self,
        result: DetectionResult,
        screenshot_path: Path | str | None = None,
    ) -> AttemptRecord:
        self.attempt_count += 1
        record = AttemptRecord(
            attempt=self.attempt_count,
            timestamp=datetime.now(UTC).isoformat(),
            starter=self.starter,
            result=result,
            screenshot_path=str(screenshot_path) if screenshot_path is not None else None,
        )
        self._append_csv(record)
        self._write_state(record)

        if result.label == "shiny":
            self._write_summary("shiny-found.json", record)
        elif result.label == "uncertain":
            self._write_summary("paused-uncertain.json", record)

        return record

    def _load_attempt_count(self) -> int:
        if not self.state_path.exists():
            return 0
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        return int(state.get("attempt_count", 0))

    def _ensure_csv_header(self) -> None:
        if self.csv_path.exists():
            return
        with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "attempt",
                    "result",
                    "confidence",
                    "timestamp",
                    "starter",
                    "mean_r",
                    "mean_g",
                    "mean_b",
                    "normal_distance",
                    "shiny_distance",
                    "screenshot_path",
                ]
            )

    def _append_csv(self, record: AttemptRecord) -> None:
        result = record.result
        with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    record.attempt,
                    result.label,
                    f"{result.confidence:.6f}",
                    record.timestamp,
                    record.starter,
                    f"{result.mean_rgb[0]:.3f}",
                    f"{result.mean_rgb[1]:.3f}",
                    f"{result.mean_rgb[2]:.3f}",
                    f"{result.normal_distance:.3f}",
                    "" if result.shiny_distance is None else f"{result.shiny_distance:.3f}",
                    record.screenshot_path or "",
                ]
            )

    def _write_state(self, record: AttemptRecord) -> None:
        state = {
            "starter": self.starter,
            "attempt_count": self.attempt_count,
            "last_attempt": _record_to_json(record),
        }
        self.state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _write_summary(self, filename: str, record: AttemptRecord) -> None:
        path = self.run_dir / filename
        path.write_text(json.dumps(_record_to_json(record), indent=2), encoding="utf-8")


def _record_to_json(record: AttemptRecord) -> dict[str, object]:
    data = asdict(record)
    return data

