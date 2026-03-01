import zeroconf
from typing import List, Dict
from ..hub import Hub

class MDNSDiscovery:
    """mDNS (Zeroconf) device discovery."""

    def __init__(self, hub: Hub, service_type: str = "_iot._tcp.local."):
        self._hub = hub
        self._service_type = service_type
        self._zc = zeroconf.Zeroconf()
        self._listener = self._MDNSListener()

    class _MDNSListener(zeroconf.ServiceListener):
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name)
            # Add to hub: self._hub.add_device_from_info(info)

        def remove_service(self, zc, type_, name):
            pass

        def update_service(self, zc, type_, name):
            pass

    def start(self) -> None:
        """Start discovery."""
        self._zc.add_service_listener(self._service_type, self._listener)

    def stop(self) -> None:
        """Stop discovery."""
        self._zc.remove_service_listener(self._listener)
        self._zc.close()