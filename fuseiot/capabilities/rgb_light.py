from typing import Dict, Any, Optional, Tuple
from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..types import Color, Brightness
from ..logging_config import get_logger

logger = get_logger("capabilities.rgb_light")


class ColorMode:
    RGB = "rgb"
    HSV = "hsv"
    TEMPERATURE = "temperature"
    EFFECT = "effect"


class RGBLight(Capability):
    """
    RGB color and brightness control.
    
    Supports RGB, HSV, color temperature, and effects.
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
        return "rgb_light"
    
    def _clamp_brightness(self, value: Brightness) -> int:
        """Clamp brightness to valid range."""
        if isinstance(value, float):
            value = int(value * 100)
        return max(self.min_brightness, min(self.max_brightness, int(value)))
    
    def read_state(self) -> Dict[str, Any]:
        """Read color and power state."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/state"})
            state = {
                "power": response.get("power", False),
                "brightness": response.get("brightness", 100),
                "color": Color(
                    response.get("r", 255),
                    response.get("g", 255),
                    response.get("b", 255)
                ),
                "color_mode": response.get("color_mode", ColorMode.RGB),
                "effect": response.get("effect", "none")
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {
                "power": False,
                "brightness": 100,
                "color": Color(255, 255, 255),
                "color_mode": ColorMode.RGB
            }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def set_color(
        self,
        color: Color,
        brightness: Optional[Brightness] = None,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set RGB color."""
        payload = {
            "_method": "POST",
            "_path": "/color",
            "r": color.r,
            "g": color.g,
            "b": color.b,
            "color_mode": ColorMode.RGB
        }
        expected = {
            "r": color.r,
            "g": color.g,
            "b": color.b
        }
        
        if brightness is not None:
            clamped = self._clamp_brightness(brightness)
            payload["brightness"] = clamped
            expected["brightness"] = clamped
        
        return self._send_and_confirm(
            command_payload=payload,
            expected_state=expected,
            timeout=timeout,
            command_name="set_color"
        )
    
    def set_hsv(
        self,
        h: float,  # 0-360
        s: float,  # 0-1
        v: float,  # 0-1
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set HSV color."""
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/hsv",
                "h": h,
                "s": s,
                "v": v,
                "color_mode": ColorMode.HSV
            },
            expected_state={"h": h, "s": s, "v": v},
            timeout=timeout,
            command_name="set_hsv"
        )
    
    def set_brightness(
        self,
        brightness: Brightness,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set brightness only."""
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
    
    def on(
        self,
        color: Optional[Color] = None,
        brightness: Optional[Brightness] = None,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Turn on with optional color/brightness."""
        payload = {"_method": "POST", "_path": "/on", "power": True}
        expected = {"power": True}
        
        if color:
            payload.update({"r": color.r, "g": color.g, "b": color.b})
            expected.update({"r": color.r, "g": color.g, "b": color.b})
        
        if brightness is not None:
            clamped = self._clamp_brightness(brightness)
            payload["brightness"] = clamped
            expected["brightness"] = clamped
        
        return self._send_and_confirm(
            command_payload=payload,
            expected_state=expected,
            timeout=timeout,
            command_name="on"
        )
    
    def off(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Turn off."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/off", "power": False},
            expected_state={"power": False},
            timeout=timeout,
            command_name="off"
        )
    
    def set_effect(
        self,
        effect: str,  # "rainbow", "pulse", "breathe", etc.
        speed: int = 50,
        confirm: Optional[bool] = None
    ) -> CommandResult:
        """Set lighting effect."""
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/effect",
                "effect": effect,
                "speed": speed
            },
            expected_state={"effect": effect},
            command_name="set_effect"
        )
    
    @property
    def color(self) -> Color:
        """Current color."""
        state = self.read_state()
        return state.get("color", Color(255, 255, 255))
    
    @property
    def brightness(self) -> int:
        """Current brightness."""
        return self.read_state().get("brightness", 100)
    
    @property
    def is_on(self) -> bool:
        """Power state."""
        return self.read_state().get("power", False)