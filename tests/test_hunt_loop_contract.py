from pathlib import Path
import unittest


class HuntLoopContractTests(unittest.TestCase):
    def test_non_shiny_check_resets_after_classification(self):
        source = Path("shiny_hunter/cli.py").read_text(encoding="utf-8")

        classify = "result = classify_frame(frame_rgb, calibration)"
        record = "record = logger.record_attempt(result, screenshot_path)"
        non_shiny = 'if result.label == "non_shiny":'
        reset = "link.send_reset()"
        stop = "link.send_stop(result.label)"

        self.assertIn(classify, source)
        self.assertIn(record, source)
        self.assertIn(non_shiny, source)
        self.assertIn(reset, source)
        self.assertIn(stop, source)
        self.assertLess(source.index(classify), source.index(record))
        self.assertLess(source.index(record), source.index(non_shiny))
        self.assertLess(source.index(non_shiny), source.index(reset))
        self.assertLess(source.index(reset), source.index(stop))


if __name__ == "__main__":
    unittest.main()
