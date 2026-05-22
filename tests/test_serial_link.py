import unittest
from types import SimpleNamespace
from unittest.mock import patch

from shiny_hunter import serial_link
from shiny_hunter.serial_link import DryRunControllerLink, SerialControllerLink


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.writes = []
        self.flushed = False
        self.closed = False
        self.input_reset = False

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        self.flushed = True

    def readline(self):
        if self.responses:
            return self.responses.pop(0)
        return b""

    def reset_input_buffer(self):
        self.input_reset = True

    def close(self):
        self.closed = True


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


class SerialControllerLinkTests(unittest.TestCase):
    def test_constructor_waits_after_opening_serial_port(self):
        fake_serial = FakeSerial([])
        fake_module = SimpleNamespace(Serial=lambda **_kwargs: fake_serial)

        with patch.dict("sys.modules", {"serial": fake_module}):
            with patch.object(serial_link.time, "sleep") as sleep:
                link = SerialControllerLink("COM3", open_delay=3.0)

        sleep.assert_called_once_with(3.0)
        self.assertTrue(fake_serial.input_reset)
        link.close()
        self.assertTrue(fake_serial.closed)

    def test_start_attempt_waits_for_busy_acknowledgement(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"READY\n", b"BUSY START\n", b"READY_CHECK\n"])
        link._ack_timeout = 0.1
        link._action_timeout = 0.1

        ack = link.send_start_attempt("charmander")

        self.assertEqual(ack, "READY_CHECK")
        self.assertEqual(link._serial.writes, [b"START charmander\n"])
        self.assertTrue(link._serial.flushed)

    def test_start_attempt_raises_when_controller_does_not_answer(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([])
        link._ack_timeout = 0.01

        with self.assertRaisesRegex(RuntimeError, "did not acknowledge START charmander"):
            link.send_start_attempt("charmander")

    def test_start_attempt_raises_when_summary_check_ready_never_arrives(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"BUSY START\n"])
        link._ack_timeout = 0.1
        link._action_timeout = 0.01

        with self.assertRaisesRegex(RuntimeError, "did not acknowledge START charmander; expected READY_CHECK"):
            link.send_start_attempt("charmander")

    def test_reset_waits_until_save_is_loaded(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"BUSY RESET\n", b"READY_SAVE\n"])
        link._ack_timeout = 0.1
        link._action_timeout = 0.1

        ack = link.send_reset()

        self.assertEqual(ack, "READY_SAVE")
        self.assertEqual(link._serial.writes, [b"RESET\n"])

    def test_raw_command_returns_first_response(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"PONG\n"])
        link._ack_timeout = 0.1
        link._action_timeout = 0.1

        self.assertEqual(link.exchange_command("PING"), "PONG")
        self.assertEqual(link._serial.writes, [b"PING\n"])


if __name__ == "__main__":
    unittest.main()
