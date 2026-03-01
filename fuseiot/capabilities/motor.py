# fuseiot/capabilities/motor.py
"""Position and speed control capability."""

from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..logging_config import get_logger

logger = get_logger("capabilities.motor")


class Motor(Capability):
    """
    Position and speed control.
    
    Commands: move_to, set_speed, stop, home
    State: position, speed, moving, homed
    """
    
    def __init__(
        self,
        protocol,
        cache,
        config=None,
        position_range: tuple = (0, 360),
        speed_range: tuple = (0, 100),
        event_bus=None,  # ADD THIS PARAMETER
        **kwargs
    ):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.position_min, self.position_max = position_range
        self.speed_min, self.speed_max = speed_range
    
    @property
    def category(self) -> str:
        return "motor"
    
    def read_state(self) -> Dict[str, Any]:
        """Read current position and status."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/status"})
            
            state = {
                "position": response.get("position", 0.0),
                "speed": response.get("speed", 0.0),
                "moving": response.get("moving", False),
                "homed": response.get("homed", False)
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {
                "position": 0.0,
                "speed": 0.0,
                "moving": False,
                "homed": False,
                "error": str(e)
            }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def move_to(
        self,
        position: float,
        speed: Optional[float] = None,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """
        Move to absolute position.
        
        Args:
            position: Target position (clamped to range)
            speed: Movement speed (optional)
            confirm: Wait for position reached
            timeout: Max seconds to wait
        """
        # Clamp to range
        target = max(self.position_min, min(self.position_max, position))
        
        payload = {
            "_method": "POST",
            "_path": "/move",
            "position": target
        }
        if speed is not None:
            payload["speed"] = max(self.speed_min, min(self.speed_max, speed))
        
        return self._send_and_confirm(
            command_payload=payload,
            expected_state={"position": target, "moving": False},
            timeout=timeout,
            command_name="move_to"
        )
    
    def set_speed(self, speed: float) -> CommandResult:
        """Set movement speed."""
        clamped = max(self.speed_min, min(self.speed_max, speed))
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/speed",
                "speed": clamped
            },
            expected_state={"speed": clamped},
            command_name="set_speed"
        )
    
    def stop(self, confirm: Optional[bool] = None) -> CommandResult:
        """Emergency stop."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/stop", "stop": True},
            expected_state={"moving": False},
            timeout=1.0,  # Short timeout for emergency
            command_name="stop"
        )
    
    def home(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Return to home position."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/home"},
            expected_state={"position": 0.0, "homed": True},
            timeout=timeout or 30.0,  # Homing can be slow
            command_name="home"
        )
    
    @property
    def position(self) -> float:
        """Current position."""
        return self.read_state().get("position", 0.0)
    
    @property
    def is_moving(self) -> bool:
        """True if currently moving."""
        return self.read_state().get("moving", False)
    
    async def move_to_async(self, position: float, **kwargs) -> CommandResult:
        """Async move."""
        return await self._send_and_confirm_async(
            command_payload={
                "_method": "POST",
                "_path": "/move",
                "position": max(self.position_min, min(self.position_max, position))
            },
            expected_state={"position": position, "moving": False},
            command_name="move_to"
        )