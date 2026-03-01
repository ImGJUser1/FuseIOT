from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass

from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..logging_config import get_logger

logger = get_logger("capabilities.thermostat")


class ThermostatMode(Enum):
    OFF = "off"
    HEAT = "heat"
    COOL = "cool"
    AUTO = "auto"
    FAN_ONLY = "fan_only"


@dataclass
class ThermostatConfig(CapabilityConfig):
    min_temp: float = 10.0
    max_temp: float = 30.0
    hysteresis: float = 0.5


class Thermostat(Capability):
    """
    Temperature control with heating/cooling.
    
    Commands: set_temperature, set_mode, fan_on, fan_off
    State: temperature, target_temp, mode, fan_running
    """
    
    def __init__(
        self,
        protocol,
        cache,
        config=None,
        min_temp: float = 10.0,
        max_temp: float = 30.0,
        hysteresis: float = 0.5,
        event_bus=None,
        **kwargs
    ):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.hysteresis = hysteresis
    
    @property
    def category(self) -> str:
        return "thermostat"
    
    def read_state(self) -> Dict[str, Any]:
        """Read thermostat state."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/status"})
            state = {
                "temperature": response.get("temperature", 20.0),
                "target_temperature": response.get("target_temperature", 22.0),
                "mode": response.get("mode", "off"),
                "fan_running": response.get("fan_running", False),
                "heating": response.get("heating", False),
                "cooling": response.get("cooling", False)
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {
                "temperature": 20.0,
                "target_temperature": 22.0,
                "mode": "off",
                "fan_running": False
            }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def set_temperature(
        self,
        temperature: float,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set target temperature."""
        clamped = max(self.min_temp, min(self.max_temp, temperature))
        
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/target",
                "temperature": clamped
            },
            expected_state={"target_temperature": clamped},
            timeout=timeout,
            command_name="set_temperature"
        )
    
    def set_mode(
        self,
        mode: ThermostatMode,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Set operating mode."""
        return self._send_and_confirm(
            command_payload={
                "_method": "POST",
                "_path": "/mode",
                "mode": mode.value
            },
            expected_state={"mode": mode.value},
            timeout=timeout,
            command_name="set_mode"
        )
    
    def fan_on(self, confirm: Optional[bool] = None) -> CommandResult:
        """Turn fan on."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/fan", "on": True},
            expected_state={"fan_running": True},
            command_name="fan_on"
        )
    
    def fan_off(self, confirm: Optional[bool] = None) -> CommandResult:
        """Turn fan off."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/fan", "on": False},
            expected_state={"fan_running": False},
            command_name="fan_off"
        )
    
    @property
    def temperature(self) -> float:
        """Current temperature."""
        return self.read_state().get("temperature", 20.0)
    
    @property
    def target_temperature(self) -> float:
        """Target temperature."""
        return self.read_state().get("target_temperature", 22.0)
    
    @property
    def mode(self) -> str:
        """Current mode."""
        return self.read_state().get("mode", "off")
    
    @property
    def is_heating(self) -> bool:
        """Is actively heating."""
        return self.read_state().get("heating", False)
    
    @property
    def is_cooling(self) -> bool:
        """Is actively cooling."""
        return self.read_state().get("cooling", False)