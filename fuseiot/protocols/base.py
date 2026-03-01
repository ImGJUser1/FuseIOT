from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import time
import asyncio

from fuseiot.logging_config import get_logger

logger = get_logger("protocols.base")


class ConnectionState(Enum):
    """Protocol connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ProtocolConfig:
    """Common protocol configuration."""
    
    timeout: float = 5.0
    retry_attempts: int = 3
    connection_check_interval: Optional[float] = None
    keepalive: bool = True
    keepalive_interval: float = 30.0
    auto_reconnect: bool = True
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 60.0
    compression: bool = False
    metrics_enabled: bool = False


class Protocol(ABC):
    """
    Abstract base for all transport protocols.
    
    Supports both sync and async operations.
    """
    
    def __init__(self, config: Optional[ProtocolConfig] = None):
        self.config = config or ProtocolConfig()
        self._state = ConnectionState.DISCONNECTED
        self._last_error: Optional[str] = None
        self._connection_time: Optional[float] = None
        self._metrics: Dict[str, Any] = {
            "messages_sent": 0,
            "messages_received": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "errors": 0,
            "latency_ms_total": 0.0,
        }
    
    @property
    def name(self) -> str:
        """Protocol identifier."""
        return self.__class__.__name__.lower()
    
    @property
    def is_connected(self) -> bool:
        """Connection health."""
        return self._state == ConnectionState.CONNECTED
    
    @property
    def connection_state(self) -> ConnectionState:
        """Detailed connection state."""
        return self._state
    
    @property
    def last_error(self) -> Optional[str]:
        """Last recorded error message."""
        return self._last_error
    
    @property
    def uptime_seconds(self) -> Optional[float]:
        """Connection uptime if connected."""
        if self._connection_time and self.is_connected:
            return time.time() - self._connection_time
        return None
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish transport connection."""
        raise NotImplementedError
    
    @abstractmethod
    def disconnect(self) -> None:
        """Clean disconnection."""
        raise NotImplementedError
    
    @abstractmethod
    def send(self, payload: Dict[str, Any]) -> Any:
        """
        Send payload and return response.
        
        Synchronous. Blocking. Raises on failure.
        """
        raise NotImplementedError
    
    def health_check(self) -> Dict[str, Any]:
        """Return connection health metrics."""
        return {
            "connected": self.is_connected,
            "state": self._state.value,
            "last_error": self._last_error,
            "protocol": self.name,
            "uptime_seconds": self.uptime_seconds,
            "metrics": self._metrics.copy() if self.config.metrics_enabled else None,
        }
    
    def _update_state(self, new_state: ConnectionState, error: Optional[str] = None) -> None:
        """Update connection state with logging."""
        old_state = self._state
        self._state = new_state
        
        if error:
            self._last_error = error
            self._metrics["errors"] += 1
        
        if new_state == ConnectionState.CONNECTED and old_state != ConnectionState.CONNECTED:
            self._connection_time = time.time()
            logger.info("protocol_connected", protocol=self.name)
        elif old_state == ConnectionState.CONNECTED and new_state != ConnectionState.CONNECTED:
            logger.warning("protocol_disconnected", 
                         protocol=self.name, 
                         new_state=new_state.value,
                         error=error)
        else:
            logger.debug("protocol_state_change",
                        protocol=self.name,
                        old=old_state.value,
                        new=new_state.value)


class AsyncProtocol(Protocol, ABC):
    """
    Async-native protocol base.
    
    Provides both sync and async interfaces.
    """
    
    async def connect_async(self) -> bool:
        """Async connection."""
        # Default: run sync in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.connect)
    
    async def disconnect_async(self) -> None:
        """Async disconnection."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.disconnect)
    
    @abstractmethod
    async def send_async(self, payload: Dict[str, Any]) -> Any:
        """Native async send."""
        raise NotImplementedError