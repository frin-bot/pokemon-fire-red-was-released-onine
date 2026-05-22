from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Protocol


class ControllerLink(Protocol):
    def send_start_attempt(self, starter: str) -> str: ...

    def send_reset(self) -> str: ...

    def send_stop(self, reason: str) -> str: ...


@dataclass
class DryRunControllerLink:
    commands: list[str] = field(default_factory=list)

    def send_start_attempt(self, starter: str) -> str:
        self.commands.append(f"START {starter}")
        return "DRY_RUN START"

    def send_reset(self) -> str:
        self.commands.append("RESET")
        return "DRY_RUN RESET"

    def send_stop(self, reason: str) -> str:
        self.commands.append(f"STOP {reason}")
        return "DRY_RUN STOP"


class SerialControllerLink:
    def __init__(
        self,
        port: str,
        baud_rate: int = 57600,
        timeout: float = 2.0,
        ack_timeout: float = 8.0,
        open_delay: float = 3.0,
    ):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required for hardware serial mode") from exc

        self._serial = serial.Serial(port=port, baudrate=baud_rate, timeout=timeout)
        self._ack_timeout = ack_timeout
        if open_delay > 0:
            time.sleep(open_delay)
        reset_input_buffer = getattr(self._serial, "reset_input_buffer", None)
        if reset_input_buffer is not None:
            reset_input_buffer()

    def send_start_attempt(self, starter: str) -> str:
        command = f"START {starter}"
        self._send_line(command)
        return self._read_until(command, ("BUSY START",))

    def send_reset(self) -> str:
        self._send_line("RESET")
        return self._read_until("RESET", ("BUSY RESET",))

    def send_stop(self, reason: str) -> str:
        command = f"STOP {reason}"
        self._send_line(command)
        return self._read_until(command, ("STOPPED",))

    def exchange_command(self, command: str) -> str:
        self._send_line(command)
        return self._read_until(command, ())

    def close(self) -> None:
        self._serial.close()

    def _send_line(self, line: str) -> None:
        self._serial.write((line.strip() + "\n").encode("ascii"))
        self._serial.flush()

    def _read_until(self, command: str, expected_prefixes: tuple[str, ...]) -> str:
        deadline = time.monotonic() + self._ack_timeout
        while time.monotonic() < deadline:
            raw_line = self._serial.readline()
            if not raw_line:
                continue
            line = raw_line.decode("ascii", errors="replace").strip()
            if not line:
                continue
            if line.startswith("ERR"):
                raise RuntimeError(f"controller rejected {command}: {line}")
            if not expected_prefixes or any(line.startswith(prefix) for prefix in expected_prefixes):
                return line

        expected = ", ".join(expected_prefixes) if expected_prefixes else "any response"
        raise RuntimeError(f"controller did not acknowledge {command}; expected {expected}")
