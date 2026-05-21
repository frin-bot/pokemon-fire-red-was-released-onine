import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shiny_hunter import cli


class FakeCapture:
    def __init__(self, index, api_preference):
        self.index = index
        self.api_preference = api_preference
        self.read_count = 0
        self.released = False

    def isOpened(self):
        return True

    def read(self):
        self.read_count += 1
        return True, f"frame-{self.read_count}"

    def release(self):
        self.released = True


class FakeCv2:
    CAP_ANY = 0
    CAP_DSHOW = 700
    CAP_MSMF = 1400

    def __init__(self):
        self.captures = []
        self.writes = []

    def VideoCapture(self, index, api_preference):
        capture = FakeCapture(index, api_preference)
        self.captures.append(capture)
        return capture

    def imwrite(self, path, frame):
        self.writes.append((Path(path), frame))
        return True


class CliCaptureFrameTests(unittest.TestCase):
    def test_capture_frame_saves_final_frame_after_warmup(self):
        fake_cv2 = FakeCv2()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "calibration" / "normal.png"

            with patch.object(cli, "_import_cv2", return_value=fake_cv2):
                result = cli.main(
                    [
                        "capture-frame",
                        "--backend",
                        "msmf",
                        "--camera-index",
                        "3",
                        "--output",
                        str(output),
                        "--warmup-frames",
                        "2",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(len(fake_cv2.captures), 1)
            self.assertEqual(fake_cv2.captures[0].index, 3)
            self.assertEqual(fake_cv2.captures[0].api_preference, FakeCv2.CAP_MSMF)
            self.assertEqual(fake_cv2.captures[0].read_count, 3)
            self.assertTrue(fake_cv2.captures[0].released)
            self.assertEqual(fake_cv2.writes, [(output, "frame-3")])

    def test_capture_frame_defaults_to_opencv_auto_backend(self):
        fake_cv2 = FakeCv2()
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "normal.png"

            with patch.object(cli, "_import_cv2", return_value=fake_cv2):
                result = cli.main(["capture-frame", "--camera-index", "1", "--output", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(fake_cv2.captures[0].api_preference, FakeCv2.CAP_ANY)


if __name__ == "__main__":
    unittest.main()
