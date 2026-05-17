from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class ControllerLink(Protocol):
    def send_start_attempt(self, starter: str) -> None: ...

    def send_reset(self) -> None: ...

    def send_stop(self, reason: str) -> None: ...


@dataclass
class DryRunControllerLink:
    commands: list[str] = field(default_factory=list)

    def send_start_attempt(self, starter: str) -> None:
        self.commands.append(f"START {starter}")

    def send_reset(self) -> None:
        self.commands.append("RESET")

    def send_stop(self, reason: str) -> None:
        self.commands.append(f"STOP {reason}")


class SerialControllerLink:
    def __init__(self, port: str, baud_rate: int = 57600, timeout: float = 2.0):
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("pyserial is required for hardware serial mode") from exc

        self._serial = serial.Serial(port=port, baudrate=baud_rate, timeout=timeout)

    def send_start_attempt(self, starter: str) -> None:
        self._send_line(f"START {starter}")

    def send_reset(self) -> None:
        self._send_line("RESET")

    def send_stop(self, reason: str) -> None:
        self._send_line(f"STOP {reason}")

    def close(self) -> None:
        self._serial.close()

    def _send_line(self, line: str) -> None:
        self._serial.write((line.strip() + "\n").encode("ascii"))
        self._serial.flush()
