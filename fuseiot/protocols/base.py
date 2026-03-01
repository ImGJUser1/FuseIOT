from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ProtocolConfig:
    """Common protocol configuration."""
    
    timeout: float = 5.0
    retry_attempts: int = 3
    connection_check_interval: Optional[float] = None


class Protocol(ABC):
    """
    Abstract base for all transport protocols.
    
    Responsibilities:
    - Connect/disconnect transport
    - Send/receive raw payloads
    - Handle transport-level errors
    - Provide connection health info
    
    NOT responsibilities:
    - Device state interpretation
    - Command semantics
    - Retry logic (handled by caller)
    """
    
    def __init__(self, config: Optional[ProtocolConfig] = None):
        self.config = config or ProtocolConfig()
        self._connected = False
        self._last_error: Optional[str] = None
    
    @property
    def name(self) -> str:
        """Protocol identifier."""
        return self.__class__.__name__.lower()
    
    @property
    def is_connected(self) -> bool:
        """Connection health."""
        return self._connected
    
    @property
    def last_error(self) -> Optional[str]:
        """Last recorded error message."""
        return self._last_error
    
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
        
        Args:
            payload: Command data (protocol-specific)
            
        Returns:
            Response data (protocol-specific)
            
        Raises:
            ProtocolError: Transport failure
        """
        raise NotImplementedError
    
    @abstractmethod
    async def send_async(self, payload: Dict[str, Any]) -> Any:
        """Async version of send."""
        raise NotImplementedError
    
    def health_check(self) -> Dict[str, Any]:
        """Return connection health metrics."""
        return {
            "connected": self._connected,
            "last_error": self._last_error,
            "protocol": self.name,
        }