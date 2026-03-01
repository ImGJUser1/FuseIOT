from abc import ABC, abstractmethod
from typing import Dict, Any
from ..hub import Hub

class CloudConnector(ABC):
    """Base class for cloud IoT connectors."""

    def __init__(self, hub: Hub):
        self._hub = hub

    @abstractmethod
    def sync_device(self, device_id: str) -> None:
        """Sync a device to the cloud."""
        pass

    @abstractmethod
    async def receive_commands(self) -> Dict[str, Any]:
        """Receive commands from the cloud."""
        pass