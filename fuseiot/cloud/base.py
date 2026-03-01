from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class CloudConnector(ABC):
    """Abstract base for cloud IoT connectors."""
    
    def __init__(self, hub: Any):
        self.hub = hub
        self._connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish cloud connection."""
        raise NotImplementedError
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from cloud."""
        raise NotImplementedError
    
    @abstractmethod
    def publish_state(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Publish device state to cloud."""
        raise NotImplementedError
    
    @abstractmethod
    def subscribe_commands(self, callback: callable) -> None:
        """Subscribe to cloud commands."""
        raise NotImplementedError
    
    @property
    def is_connected(self) -> bool:
        return self._connected