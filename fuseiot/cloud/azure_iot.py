from .base import CloudConnector
from azure.iot.device import IoTHubDeviceClient
from typing import Dict, Any

class AzureIoT(CloudConnector):
    """Connector for Azure IoT Hub."""

    def __init__(self, hub, connection_string: str):
        super().__init__(hub)
        self._client = IoTHubDeviceClient.create_from_connection_string(connection_string)

    def sync_device(self, device_id: str) -> None:
        """Report device state to Azure."""
        state = self._hub.get_device_state(device_id)
        self._client.send_message(json.dumps(state))

    async def receive_commands(self) -> Dict[str, Any]:
        """Receive method (async listener setup)."""
        # Setup listener in init for production
        message = await self._client.receive_message()  # Assuming async patch or loop
        return json.loads(message.data)