# fuseiot/capabilities/sensor.py
"""Measurement reading capability."""

from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..logging_config import get_logger

logger = get_logger("capabilities.sensor")


class Sensor(Capability):
    """
    Measurement reading.
    
    Commands: read, calibrate
    State: value (float), unit (str), timestamp
    """
    
    def __init__(
        self, 
        protocol, 
        cache, 
        config=None, 
        unit: str = "unknown",
        event_bus=None,  # ADD THIS PARAMETER
        **kwargs
    ):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.unit = unit
    
    @property
    def category(self) -> str:
        return "sensor"
    
    def read_state(self) -> Dict[str, Any]:
        """Read current measurement."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/reading"})
            
            state = {
                "value": response.get("value", response.get("reading", 0.0)),
                "unit": response.get("unit", self.unit),
                "timestamp": response.get("timestamp")
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            import time
            state = {
                "value": 0.0,
                "unit": self.unit,
                "timestamp": time.time(),
                "error": str(e)
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
    
    async def read_async(self, fresh: bool = False) -> Dict[str, Any]:
        """Async sensor read."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read, fresh)
    
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
            expected_state={"calibrated": True},
            command_name="calibrate"
        )