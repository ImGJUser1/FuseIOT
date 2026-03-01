# fuseiot/protocols/serial.py
"""Serial/USB protocol support."""

import json
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

from .base import Protocol, ProtocolConfig, ConnectionState
from ..exceptions import ProtocolError
from ..logging_config import get_logger

logger = get_logger("protocols.serial")


@dataclass
class SerialConfig(ProtocolConfig):
    """Serial-specific configuration."""
    port: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1


class Serial(Protocol):
    """Serial/USB protocol for direct hardware connection."""
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 9600,
        timeout: float = 5.0,
        config: Optional[SerialConfig] = None
    ):
        if not SERIAL_AVAILABLE:
            raise ImportError("pyserial required: pip install pyserial")
        
        super().__init__(config or SerialConfig())
        self.port = port
        self.baudrate = baudrate
        self._serial = None
    
    @property
    def endpoint(self) -> str:
        return f"serial:{self.port}"
    
    def connect(self) -> bool:
        """Open serial connection."""
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.config.timeout
            )
            self._update_state(ConnectionState.CONNECTED)
            return True
            
        except Exception as e:
            self._update_state(ConnectionState.FAILED, str(e))
            return False
    
    def disconnect(self) -> None:
        """Close serial connection."""
        if self._serial:
            self._serial.close()
            self._serial = None
        self._update_state(ConnectionState.DISCONNECTED)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send command via serial."""
        if not self._serial:
            raise ProtocolError("Not connected", "serial", self.port)
        
        try:
            # Send JSON line
            message = json.dumps(payload) + "\n"
            self._serial.write(message.encode("utf-8"))
            
            # Read response
            response_line = self._serial.readline().decode("utf-8").strip()
            if response_line:
                return json.loads(response_line)
            
            return {"sent": True}
            
        except json.JSONDecodeError as e:
            raise ProtocolError(f"Invalid JSON response: {e}", "serial", self.port)
        except Exception as e:
            raise ProtocolError(f"Serial error: {e}", "serial", self.port, e)
    
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper - runs in thread pool."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, payload)