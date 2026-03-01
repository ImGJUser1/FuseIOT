from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from ..result import CommandResult


class Sensor(Capability):
    """
    Measurement reading.
    
    Commands: read, calibrate
    State: value (float), unit (str), timestamp
    """
    
    def __init__(self, protocol, cache, config=None, unit: str = "unknown"):
        super().__init__(protocol, cache, config)
        self.unit = unit
    
    @property
    def category(self) -> str:
        return "sensor"
    
    def read_state(self) -> Dict[str, Any]:
        """Read current measurement."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        response = self.protocol.send({"_method": "GET", "_path": "/reading"})
        
        state = {
            "value": response.get("value", response.get("reading", 0.0)),
            "unit": response.get("unit", self.unit),
            "timestamp": response.get("timestamp")
        }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def read(self, fresh: bool = False) -> Dict[str, Any]:
        """
        Get sensor reading.
        
        Args:
            fresh: Bypass cache, force new poll
            
        Returns:
            Dict with value, unit, timestamp, age_seconds
        """
        if fresh:
            self.cache.invalidate(self.id)
        
        state = self.read_state()
        
        # Calculate age
        import time
        timestamp = state.get("timestamp", time.time())
        age = time.time() - timestamp if timestamp else 0
        
        return {
            **state,
            "age_seconds": age,
            "fresh": fresh
        }
    
    @property
    def value(self) -> float:
        """Convenience: current value."""
        return self.read_state().get("value", 0.0)
    
    def calibrate(self, reference_value: float) -> CommandResult:
        """Send calibration command."""
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/calibrate",
                "reference": reference_value
            },
            expected_state={"calibrated": True}
        )