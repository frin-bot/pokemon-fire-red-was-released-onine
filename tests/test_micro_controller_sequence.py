from pathlib import Path
import re
import unittest


class MicroControllerSequenceTests(unittest.TestCase):
    def test_starter_attempt_declines_nickname_before_resuming_a_spam(self):
        sketch = Path("arduino/micro_controller/micro_controller.ino").read_text()
        match = re.search(r"void runStarterAttempt\(String starter\) \{(?P<body>.*?)\n\}", sketch, re.S)
        self.assertIsNotNone(match)

        body = match.group("body")
        receive_text = "tap(Button::A, 650, 2);"
        decline_nickname = "tap(Button::B, 650, 6);"
        rival_dialogue = "tap(Button::A, 700, 16);"

        self.assertNotIn("tap(Button::A, 700, 8);", body)
        self.assertIn(receive_text, body)
        self.assertIn(decline_nickname, body)
        self.assertIn(rival_dialogue, body)
        self.assertLess(body.index(receive_text), body.index(decline_nickname))
        self.assertLess(body.index(decline_nickname), body.index(rival_dialogue))


if __name__ == "__main__":
    unittest.main()
