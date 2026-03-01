import serial
from typing import Any, Dict, Optional
from .base import Protocol
from ..result import Result
from ..exceptions import ConnectionError

class Serial(Protocol):
    """Serial protocol for USB/RS232 devices."""

    def __init__(self, port: str, baudrate: int = 9600, timeout: float = 1.0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser = None

    def connect(self) -> None:
        """Open serial connection."""
        try:
            self._ser = serial.Serial(self._port, self._baudrate, timeout=self._timeout)
        except serial.SerialException as e:
            raise ConnectionError(f"Serial connection failed: {e}")

    def send_command(self, command: str, payload: Optional[Dict[str, Any]] = None) -> Result:
        """Send command over serial (sync, as serial is blocking)."""
        if not self._ser:
            self.connect()
        message = f"{command}:{json.dumps(payload or {})}\n".encode()
        self._ser.write(message)
        response = self._ser.readline().decode().strip()
        try:
            data = json.loads(response)
            return Result(success=data.get("success", False), data=data.get("data"), error=data.get("error"))
        except json.JSONDecodeError:
            return Result(success=False, error="Invalid response")

    def disconnect(self) -> None:
        """Close serial connection."""
        if self._ser:
            self._ser.close()