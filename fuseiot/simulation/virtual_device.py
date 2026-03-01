from typing import Dict, Any, Callable
from ..capabilities.base import Capability
from ..protocols.base import Protocol

class VirtualDevice(Protocol):
    """Simulates a virtual IoT device for testing."""

    def __init__(self, capabilities: Dict[str, Callable]):
        self._state: Dict[str, Any] = {}
        self._capabilities = capabilities

    async def send_command(self, command: str, payload: Dict[str, Any] = None) -> Result:
        """Simulate command execution."""
        if command in self._capabilities:
            result = self._capabilities[command](self._state, payload)
            self._state.update(result.get("state_update", {}))
            return Result(success=True, data=result.get("data"))
        return Result(success=False, error="Unknown command")