import asyncio
from typing import Any, Dict, Optional
import websockets
from .base import Protocol
from ..result import Result
from ..exceptions import ConnectionError

class WebSocket(Protocol):
    """WebSocket protocol for real-time communication."""

    def __init__(self, uri: str):
        self._uri = uri
        self._websocket = None

    async def connect(self) -> None:
        """Establish WebSocket connection."""
        try:
            self._websocket = await websockets.connect(self._uri)
        except Exception as e:
            raise ConnectionError(f"WebSocket connection failed: {e}")

    async def send_command(self, command: str, payload: Optional[Dict[str, Any]] = None) -> Result:
        """Send command over WebSocket."""
        if not self._websocket:
            await self.connect()
        message = {"command": command, "payload": payload or {}}
        await self._websocket.send(json.dumps(message))
        response = await self._websocket.recv()
        data = json.loads(response)
        return Result(success=data.get("success", False), data=data.get("data"), error=data.get("error"))

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._websocket:
            await self._websocket.close()