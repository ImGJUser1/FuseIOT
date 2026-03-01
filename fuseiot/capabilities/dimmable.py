from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..types import Brightness
from ..logging_config import get_logger

logger = get_logger("capabilities.dimmable")


class Dimmable(Capability):
    """
    Brightness control (0-100%).
    
    Extends switchable with brightness level.
    """
    
    def __init__(
        self,
        protocol,
        cache,
        config=None,
        min_brightness: Brightness = 0,
        max_brightness: Brightness = 100,
        **kwargs
    ):
        super().__init__(protocol, cache, config, **kwargs)
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
    
    @property
    def category(self) -> str:
        return "dimmable"
    
    def _clamp_brightness(self, value: Brightness) -> int:
        """Clamp brightness to valid range."""
        if isinstance(value, float):
            value = int(value * 100)  # Convert 0.0-1.0 to 0-100
        return max(self.min_brightness, min(self.max_brightness, int(value)))
    
    def read_state(self) -> Dict[str, Any]:
        """Read power and brightness state."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/state"})
            state = {
                "power": response.get("power", response.get("state", False)),
                "brightness": response.get("brightness", 0),
                "brightness_percent": response.get("brightness_percent", 0)
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {"power": False, "brightness": 0}
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def on(
        self,
        brightness: Optional[Brightness] = None,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """
        Turn on with optional brightness.
        
        Args:
            brightness: Brightness level (0-100 or 0.0-1.0)
            confirm: Wait for confirmation
            timeout: Max seconds to wait
        """
        payload = {"_method": "POST", "_path": "/on", "power": True}
        expected = {"power": True}
        
        if brightness is not None:
            clamped = self._clamp_brightness(brightness)
            payload["brightness"] = clamped
            expected["brightness"] = clamped
        
        result = self._send_and_confirm(
            command_payload=payload,
            expected_state=expected,
            timeout=timeout,
            command_name="on"
        )
        
        return result
    
    def off(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Turn off."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/off", "power": False},
            expected_state={"power": False, "brightness": 0},
            timeout=timeout,
            command_name="off"
        )
    
    def set_brightness(
        self,
        brightness: Brightness,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set brightness without changing power state."""
        clamped = self._clamp_brightness(brightness)
        
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/brightness",
                "brightness": clamped
            },
            expected_state={"brightness": clamped},
            timeout=timeout,
            command_name="set_brightness"
        )
    
    def fade_to(
        self,
        brightness: Brightness,
        duration_ms: int = 1000,
        confirm: Optional[bool] = None
    ) -> CommandResult:
        """Fade to brightness over time."""
        clamped = self._clamp_brightness(brightness)
        
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/fade",
                "brightness": clamped,
                "duration_ms": duration_ms
            },
            expected_state={"brightness": clamped},
            command_name="fade_to"
        )
    
    @property
    def brightness(self) -> int:
        """Current brightness (0-100)."""
        return self.read_state().get("brightness", 0)
    
    @property
    def is_on(self) -> bool:
        """Current power state."""
        return self.read_state().get("power", False)