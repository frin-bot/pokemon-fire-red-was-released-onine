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
            self.assertIn(
                "attempt,result,confidence",
                (Path(tmp) / "attempts.csv").read_text(encoding="utf-8"),
            )

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
