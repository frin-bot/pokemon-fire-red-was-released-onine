from pathlib import Path
import re
import unittest


class MicroControllerSequenceTests(unittest.TestCase):
    def setUp(self):
        self.sketch = Path("arduino/micro_controller/micro_controller.ino").read_text()

    def test_starter_attempt_declines_nickname_then_opens_summary_check(self):
        match = re.search(r"void runStarterAttempt\(String starter\) \{(?P<body>.*?)\n\}", self.sketch, re.S)
        self.assertIsNotNone(match)

        body = match.group("body")
        receive_text = "tap(Button::A, 650, 2);"
        decline_nickname = "tap(Button::B, 650, 6);"
        open_summary = "openStarterSummaryForCheck();"

        self.assertNotIn("tap(Button::A, 700, 8);", body)
        self.assertNotIn("tap(Button::A, 700, 16);", body)
        self.assertIn(receive_text, body)
        self.assertIn(decline_nickname, body)
        self.assertIn(open_summary, body)
        self.assertLess(body.index(receive_text), body.index(decline_nickname))
        self.assertLess(body.index(decline_nickname), body.index(open_summary))

    def test_summary_check_opens_menu_and_first_pokemon_summary(self):
        match = re.search(r"void openStarterSummaryForCheck\(\) \{(?P<body>.*?)\n\}", self.sketch, re.S)
        self.assertIsNotNone(match)

        body = match.group("body")
        open_menu = "tap(Button::PLUS, 1000);"
        choose_party = "tap(Button::A, 900);"
        choose_summary = "tap(Button::A, 1200);"

        self.assertIn(open_menu, body)
        self.assertEqual(2, body.count(choose_party))
        self.assertIn(choose_summary, body)
        self.assertLess(body.index(open_menu), body.index(choose_party))
        self.assertLess(body.rindex(choose_party), body.index(choose_summary))

    def test_soft_reset_command_only_presses_reset_combo(self):
        self.assertIn('if (command == "soft_reset" || command == "sr")', self.sketch)

        match = re.search(
            r'if \(command == "soft_reset" \|\| command == "sr"\) \{(?P<body>.*?)\n  \}',
            self.sketch,
            re.S,
        )
        self.assertIsNotNone(match)

        body = match.group("body")
        self.assertIn('sendStatus("BUSY SOFT_RESET");', body)
        self.assertIn("pressSoftResetCombo();", body)
        self.assertIn('sendStatus("READY_TITLE");', body)
        self.assertNotIn("softResetToSave();", body)


if __name__ == "__main__":
    unittest.main()
