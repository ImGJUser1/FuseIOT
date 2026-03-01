from typing import Dict, Any

from .base import CloudConnector
from ..logging_config import get_logger

logger = get_logger("cloud.azure")


class AzureIoT(CloudConnector):
    """Azure IoT Hub connector."""
    
    def __init__(
        self,
        hub: Any,
        connection_string: str
    ):
        super().__init__(hub)
        self.connection_string = connection_string
    
    def connect(self) -> bool:
        """Connect to Azure IoT."""
        logger.info("azure_iot_connect")
        self._connected = True
        return True
    
    def disconnect(self) -> None:
        """Disconnect from Azure IoT."""
        self._connected = False
        logger.info("azure_iot_disconnect")
    
    def publish_state(self, device_id: str, state: Dict[str, Any]) -> bool:
        """Publish state to Azure IoT."""
        logger.debug("azure_iot_publish", device_id=device_id, state=state)
        return True
    
    def subscribe_commands(self, callback: callable) -> None:
        """Subscribe to Azure IoT commands."""
        logger.info("azure_iot_subscribe")