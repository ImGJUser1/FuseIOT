from typing import Dict
from ..hub import Hub

class Health:
    """Health checks for devices and hub."""

    def __init__(self, hub: Hub):
        self._hub = hub

    async def check_device(self, device_id: str) -> Dict[str, bool]:
        """Check device health."""
        try:
            status = await self._hub.get_device(device_id).get_status()
            return {"healthy": status.success, "details": status.data}
        except Exception:
            return {"healthy": False, "details": "Connection failed"}

    def check_hub(self) -> Dict[str, Any]:
        """Check overall hub health."""
        return {"devices_connected": len(self._hub.devices), "uptime": time.time() - self._hub.start_time}