import tempfile
import unittest
from pathlib import Path

from shiny_hunter.cli import load_calibration, parse_crop, save_calibration
from shiny_hunter.models import Calibration, ColorProfile, CropRect


class CliCalibrationTests(unittest.TestCase):
    def test_parse_crop_accepts_comma_separated_rectangle(self):
        self.assertEqual(parse_crop("10,20,30,40"), CropRect(10, 20, 30, 40))

    def test_calibration_round_trips_as_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.json"
            calibration = Calibration(
                starter="charmander",
                crop=CropRect(1, 2, 3, 4),
                normal_profile=ColorProfile((10.0, 20.0, 30.0)),
                shiny_profile=ColorProfile((40.0, 50.0, 60.0)),
                confidence_threshold=0.2,
                decision_margin=12.0,
                normal_max_distance=28.0,
            )

            save_calibration(path, calibration)

            self.assertEqual(load_calibration(path), calibration)


if __name__ == "__main__":
    unittest.main()
