import json
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from .base import AsyncProtocol, ProtocolConfig, ConnectionState
from ..exceptions import ProtocolError
from ..logging_config import get_logger

logger = get_logger("protocols.websocket")


@dataclass
class WebSocketConfig(ProtocolConfig):
    """WebSocket-specific configuration."""
    uri: str = ""
    ping_interval: float = 20.0
    ping_timeout: float = 10.0


class WebSocket(AsyncProtocol):
    """WebSocket protocol for real-time communication."""
    
    def __init__(
        self,
        uri: str,
        ping_interval: float = 20.0,
        ping_timeout: float = 10.0,
        config: Optional[WebSocketConfig] = None
    ):
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets required: pip install websockets")
        
        super().__init__(config or WebSocketConfig())
        self.uri = uri
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self._websocket = None
        self._message_queue = asyncio.Queue()
    
    @property
    def endpoint(self) -> str:
        return self.uri
    
    async def connect_async(self) -> bool:
        """Async WebSocket connection."""
        try:
            self._websocket = await websockets.connect(
                self.uri,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout
            )
            self._update_state(ConnectionState.CONNECTED)
            
            # Start message handler
            asyncio.create_task(self._message_handler())
            
            return True
            
        except Exception as e:
            self._update_state(ConnectionState.FAILED, str(e))
            return False
    
    def connect(self) -> bool:
        """Sync connection - runs async in event loop."""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.connect_async())
        except RuntimeError:
            # No event loop running
            return asyncio.run(self.connect_async())
    
    async def disconnect_async(self) -> None:
        """Async disconnect."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        self._update_state(ConnectionState.DISCONNECTED)
    
    def disconnect(self) -> None:
        """Sync disconnect."""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.disconnect_async())
        except RuntimeError:
            asyncio.run(self.disconnect_async())
    
    async def _message_handler(self):
        """Handle incoming messages."""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._message_queue.put(data)
                except json.JSONDecodeError:
                    logger.warning("websocket_invalid_json", message=message[:100])
        except Exception:
            self._update_state(ConnectionState.DISCONNECTED)
    
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send via WebSocket."""
        if not self._websocket:
            raise ProtocolError("Not connected", "websocket", self.uri)
        
        try:
            await self._websocket.send(json.dumps(payload))
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=self.config.timeout
                )
                return response
            except asyncio.TimeoutError:
                raise ProtocolError("Response timeout", "websocket", self.uri)
                
        except Exception as e:
            raise ProtocolError(f"WebSocket send failed: {e}", "websocket", self.uri, e)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sync send."""
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.send_async(payload))
        except RuntimeError:
            return asyncio.run(self.send_async(payload))