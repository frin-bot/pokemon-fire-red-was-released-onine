import unittest

from shiny_hunter.serial_link import DryRunControllerLink, SerialControllerLink


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.writes = []
        self.flushed = False
        self.closed = False

    def write(self, data):
        self.writes.append(data)

    def flush(self):
        self.flushed = True

    def readline(self):
        if self.responses:
            return self.responses.pop(0)
        return b""

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
    def test_start_attempt_waits_for_busy_acknowledgement(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"READY\n", b"BUSY START\n"])
        link._ack_timeout = 0.1

        ack = link.send_start_attempt("charmander")

        self.assertEqual(ack, "BUSY START")
        self.assertEqual(link._serial.writes, [b"START charmander\n"])
        self.assertTrue(link._serial.flushed)

    def test_start_attempt_raises_when_controller_does_not_answer(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([])
        link._ack_timeout = 0.01

        with self.assertRaisesRegex(RuntimeError, "did not acknowledge START charmander"):
            link.send_start_attempt("charmander")

    def test_raw_command_returns_first_response(self):
        link = SerialControllerLink.__new__(SerialControllerLink)
        link._serial = FakeSerial([b"PONG\n"])
        link._ack_timeout = 0.1

        self.assertEqual(link.exchange_command("PING"), "PONG")
        self.assertEqual(link._serial.writes, [b"PING\n"])


if __name__ == "__main__":
    unittest.main()
