from typing import List, Type
from .base import Capability
from ..protocols.base import Protocol

class Composite(Capability):
    """Composite capability for multi-function devices."""

    def __init__(self, protocol: Protocol, device_id: str, capabilities: List[Type[Capability]]):
        super().__init__(protocol, device_id)
        self._capabilities = {cap.__name__: cap(protocol, device_id) for cap in capabilities}

    def get_capability(self, name: str) -> Capability:
        """Get a sub-capability by name."""
        if name not in self._capabilities:
            raise ValueError(f"Capability {name} not available")
        return self._capabilities[name]

    async def list_capabilities(self) -> List[str]:
        """List available sub-capabilities."""
        return list(self._capabilities.keys())