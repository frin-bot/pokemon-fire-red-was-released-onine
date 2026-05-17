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
