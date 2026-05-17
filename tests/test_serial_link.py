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
