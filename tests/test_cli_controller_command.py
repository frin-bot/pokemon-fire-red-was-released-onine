import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from shiny_hunter import cli


class FakeControllerLink:
    def __init__(self):
        self.commands = []
        self.closed = False

    def exchange_command(self, command):
        self.commands.append(command)
        return "PONG"

    def close(self):
        self.closed = True


class CliControllerCommandTests(unittest.TestCase):
    def test_controller_command_prints_controller_response(self):
        link = FakeControllerLink()
        output = io.StringIO()

        with patch.object(cli, "_serial_link_from_args", return_value=link):
            with redirect_stdout(output):
                result = cli.main(["controller-command", "--serial-port", "COM3", "--command", "PING"])

        self.assertEqual(result, 0)
        self.assertEqual(link.commands, ["PING"])
        self.assertTrue(link.closed)
        self.assertIn("PONG", output.getvalue())


if __name__ == "__main__":
    unittest.main()
