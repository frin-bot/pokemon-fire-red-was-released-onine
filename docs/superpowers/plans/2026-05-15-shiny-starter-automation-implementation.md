# Shiny Starter Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working project skeleton for a fully unattended FireRed shiny starter hunt using Windows video capture, Python/OpenCV decision logic, attempt logging, an Arduino Nano serial bridge, and an Arduino Micro Switch controller.

**Architecture:** The Python app owns state, detection, capture, serial communication, and logging. The Arduino Micro runs deterministic controller routines and receives simple line commands through `Serial1`. The Arduino Nano bridges Windows USB serial to Micro `Serial1` using `SoftwareSerial` pins so the Nano hardware UART can stay attached to USB.

**Tech Stack:** Python 3, standard-library unit tests, optional OpenCV/NumPy/pyserial for hardware runs, Arduino AVR sketches, `NintendoSwitchControlLibrary` for Switch-compatible Micro input.

---

## File Structure

- `shiny_hunter/models.py`: immutable value objects for crop rectangles, color profiles, calibration, and detection results.
- `shiny_hunter/detector.py`: conservative crop-based color classifier.
- `shiny_hunter/run_logger.py`: persistent attempt counter, CSV/JSON run state, final shiny/paused summaries.
- `shiny_hunter/serial_link.py`: line-oriented controller serial link plus dry-run recorder.
- `shiny_hunter/cli.py`: commands for calibrating from an image, classifying an image, listing cameras, and running the hunt loop.
- `scripts/shiny-hunt.py`: thin CLI entrypoint.
- `tests/test_detector.py`: detector behavior tests.
- `tests/test_run_logger.py`: persistent attempt-count tests.
- `tests/test_serial_link.py`: dry-run serial protocol tests.
- `arduino/nano_bridge/nano_bridge.ino`: USB serial to Micro serial bridge.
- `arduino/micro_controller/micro_controller.ino`: Switch controller command receiver and starter/reset routines.
- `docs/setup.md`: Windows, Arduino, capture-card, calibration, and dry-run instructions.
- `docs/wiring.md`: pin-by-pin wiring guide.
- `requirements.txt`: Python runtime dependencies.

## Task 1: Python Core Tests

**Files:**
- Create: `tests/test_detector.py`
- Create: `tests/test_run_logger.py`
- Create: `tests/test_serial_link.py`

- [ ] **Step 1: Write failing detector tests**

```python
import unittest

from shiny_hunter.detector import classify_frame
from shiny_hunter.models import Calibration, ColorProfile, CropRect


class DetectorTests(unittest.TestCase):
    def test_classifies_non_shiny_when_crop_matches_normal_profile(self):
        frame = [[(12, 200, 80), (14, 198, 82)], [(13, 201, 81), (12, 199, 79)]]
        calibration = Calibration(
            starter="bulbasaur",
            crop=CropRect(0, 0, 2, 2),
            normal_profile=ColorProfile((13.0, 199.5, 80.5)),
            shiny_profile=ColorProfile((180.0, 220.0, 70.0)),
            confidence_threshold=0.15,
            decision_margin=10.0,
            normal_max_distance=25.0,
        )

        result = classify_frame(frame, calibration)

        self.assertEqual(result.label, "non_shiny")
        self.assertGreaterEqual(result.confidence, 0.15)

    def test_classifies_shiny_when_crop_matches_shiny_profile(self):
        frame = [[(178, 221, 72), (181, 219, 70)], [(180, 222, 71), (179, 220, 73)]]
        calibration = Calibration(
            starter="bulbasaur",
            crop=CropRect(0, 0, 2, 2),
            normal_profile=ColorProfile((13.0, 199.5, 80.5)),
            shiny_profile=ColorProfile((180.0, 220.0, 72.0)),
            confidence_threshold=0.15,
            decision_margin=10.0,
            normal_max_distance=25.0,
        )

        result = classify_frame(frame, calibration)

        self.assertEqual(result.label, "shiny")
        self.assertLess(result.shiny_distance, result.normal_distance)

    def test_returns_uncertain_without_shiny_profile_when_crop_is_far_from_normal(self):
        frame = [[(150, 150, 150), (150, 150, 150)], [(150, 150, 150), (150, 150, 150)]]
        calibration = Calibration(
            starter="squirtle",
            crop=CropRect(0, 0, 2, 2),
            normal_profile=ColorProfile((50.0, 80.0, 200.0)),
            shiny_profile=None,
            confidence_threshold=0.2,
            decision_margin=10.0,
            normal_max_distance=25.0,
        )

        result = classify_frame(frame, calibration)

        self.assertEqual(result.label, "uncertain")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Write failing run logger tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from shiny_hunter.models import DetectionResult
from shiny_hunter.run_logger import RunLogger


class RunLoggerTests(unittest.TestCase):
    def test_records_attempts_persistently(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = RunLogger(Path(tmp), starter="charmander")
            result = DetectionResult("non_shiny", 0.88, (200.0, 90.0, 40.0), 3.0, 140.0)

            record = logger.record_attempt(result)

            self.assertEqual(record.attempt, 1)
            state = json.loads((Path(tmp) / "current-run.json").read_text(encoding="utf-8"))
            self.assertEqual(state["attempt_count"], 1)
            self.assertIn("attempt,result,confidence", (Path(tmp) / "attempts.csv").read_text(encoding="utf-8"))

    def test_resumes_existing_attempt_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = RunLogger(Path(tmp), starter="bulbasaur")
            first.record_attempt(DetectionResult("non_shiny", 0.9, (1.0, 2.0, 3.0), 1.0, 50.0))

            second = RunLogger(Path(tmp), starter="bulbasaur")
            record = second.record_attempt(DetectionResult("shiny", 0.95, (5.0, 6.0, 7.0), 80.0, 2.0))

            self.assertEqual(record.attempt, 2)
            self.assertTrue((Path(tmp) / "shiny-found.json").exists())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Write failing dry-run serial tests**

```python
import unittest

from shiny_hunter.serial_link import DryRunControllerLink


class DryRunControllerLinkTests(unittest.TestCase):
    def test_records_line_commands(self):
        link = DryRunControllerLink()

        link.send_start_attempt("squirtle")
        link.send_reset()
        link.send_stop("uncertain")

        self.assertEqual(
            link.commands,
            ["START squirtle", "RESET", "STOP uncertain"],
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 4: Verify tests fail before implementation**

Run: `python -B -m unittest discover -s tests -v`

Expected: FAIL or ERROR because the `shiny_hunter` package does not exist yet.

## Task 2: Python Core Implementation

**Files:**
- Create: `shiny_hunter/__init__.py`
- Create: `shiny_hunter/models.py`
- Create: `shiny_hunter/detector.py`
- Create: `shiny_hunter/run_logger.py`
- Create: `shiny_hunter/serial_link.py`

- [ ] **Step 1: Implement model dataclasses**
- [ ] **Step 2: Implement detector mean-color distance classification**
- [ ] **Step 3: Implement persistent run logger**
- [ ] **Step 4: Implement dry-run and pyserial controller links**
- [ ] **Step 5: Run core tests**

Run: `python -B -m unittest discover -s tests -v`

Expected: PASS.

## Task 3: CLI And Hardware Integration

**Files:**
- Create: `shiny_hunter/cli.py`
- Create: `scripts/shiny-hunt.py`
- Create: `requirements.txt`

- [ ] **Step 1: Add JSON calibration load/save helpers**
- [ ] **Step 2: Add `calibrate-image` command that writes normal color profile JSON from an image and crop**
- [ ] **Step 3: Add `classify-image` command that prints a JSON detection result**
- [ ] **Step 4: Add `list-cameras` command using OpenCV**
- [ ] **Step 5: Add `run` command with dry-run support, serial commands, attempt logging, and conservative stop behavior**
- [ ] **Step 6: Run unit tests again**

Run: `python -B -m unittest discover -s tests -v`

Expected: PASS.

## Task 4: Arduino Sketches

**Files:**
- Create: `arduino/nano_bridge/nano_bridge.ino`
- Create: `arduino/micro_controller/micro_controller.ino`

- [ ] **Step 1: Add Nano `SoftwareSerial` bridge on D10/D11**
- [ ] **Step 2: Add Micro line-command parser on `Serial1`**
- [ ] **Step 3: Add Micro starter selection routine with adjustable timings**
- [ ] **Step 4: Add Micro soft-reset-to-save routine**
- [ ] **Step 5: Add Micro stop and ping/status responses**

Expected: sketches are ready to compile in Arduino IDE after installing `NintendoSwitchControlLibrary`.

## Task 5: Documentation

**Files:**
- Create: `README.md`
- Create: `docs/setup.md`
- Create: `docs/wiring.md`
- Modify: `docs/superpowers/specs/2026-05-15-shiny-starter-automation-design.md`

- [ ] **Step 1: Document dependencies and purchase requirements**
- [ ] **Step 2: Document exact Nano-to-Micro wiring using D10/D11 SoftwareSerial**
- [ ] **Step 3: Document Arduino upload order and serial echo test**
- [ ] **Step 4: Document capture-card calibration and dry-run flow**
- [ ] **Step 5: Update the design spec wiring section to match D10/D11**

Expected: user can buy the capture card later and still begin Arduino/Python setup now.

## Self-Review

- Spec coverage: hardware layout, automation flow, shiny detection, attempt counter, safety rules, verification, and setup guide are all represented by tasks.
- Placeholder scan: no steps use `TBD` or unbounded “handle later” language.
- Type consistency: detector tests use `DetectionResult`, `Calibration`, `ColorProfile`, and `CropRect`; implementation tasks define those names before use.
