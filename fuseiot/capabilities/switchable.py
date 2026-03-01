from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from ..result import CommandResult


class Switchable(Capability):
    """
    Binary power control.
    
    Commands: on, off, toggle
    State: power (bool)
    """
    
    @property
    def category(self) -> str:
        return "switchable"
    
    def read_state(self) -> Dict[str, Any]:
        """Read current power state."""
        # Try cache first
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        # Poll from device
        response = self.protocol.send({"_method": "GET", "_path": "/state"})
        state = {"power": response.get("power", response.get("state", False))}
        
        # Cache result
        self.cache.set(self.id, state, source="poll")
        return state
    
    def on(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """
        Turn device on.
        
        Args:
            confirm: Override default confirmation (None = use config)
            timeout: Override default timeout
            
        Returns:
            CommandResult with confirmation status
        """
        use_confirm = confirm if confirm is not None else self.config.confirm
        
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/on", "power": True},
            expected_state={"power": True},
            timeout=timeout
        )
    
    def off(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Turn device off."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/off", "power": False},
            expected_state={"power": False},
            timeout=timeout
        )
    
    def toggle(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Toggle power state."""
        current = self.read_state().get("power", False)
        if current:
            return self.off(confirm=confirm, timeout=timeout)
        else:
            return self.on(confirm=confirm, timeout=timeout)
    
    @property
    def is_on(self) -> bool:
        """Convenience: current power state."""
        return self.read_state().get("power", False)