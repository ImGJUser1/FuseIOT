from .base import CloudConnector
import google.cloud.iot_v1 as iot_v1
from typing import Dict, Any

class GCPIoT(CloudConnector):
    """Connector for Google Cloud IoT Core."""

    def __init__(self, hub, project_id: str, registry_id: str, device_id: str):
        super().__init__(hub)
        self._client = iot_v1.DeviceManagerClient()
        self._device_path = self._client.device_path(project_id, 'us-central1', registry_id, device_id)

    def sync_device(self, device_id: str) -> None:
        """Update device config in GCP."""
        state = self._hub.get_device_state(device_id)
        config = iot_v1.DeviceConfig()
        config.binary_data = json.dumps(state).encode()
        self._client.modify_cloud_to_device_config(request={"name": self._device_path, "binary_data": config.binary_data})

    async def receive_commands(self) -> Dict[str, Any]:
        """Get latest config (polling)."""
        config = self._client.get_device_config(name=self._device_path)
        return json.loads(config.binary_data.decode())