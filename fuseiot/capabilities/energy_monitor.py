from typing import Dict, Any, Optional
from dataclasses import dataclass

from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..logging_config import get_logger

logger = get_logger("capabilities.energy_monitor")


@dataclass
class EnergyReading:
    power_watts: float
    voltage: float
    current_amps: float
    energy_kwh: float
    frequency_hz: Optional[float] = None
    power_factor: Optional[float] = None


class EnergyMonitor(Capability):
    """
    Power and energy monitoring.
    
    Commands: read, reset_counter, calibrate
    State: power, voltage, current, energy, cost
    """
    
    def __init__(
        self,
        protocol,
        cache,
        config=None,
        cost_per_kwh: float = 0.15,
        currency: str = "USD",
        event_bus=None,
        **kwargs
    ):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.cost_per_kwh = cost_per_kwh
        self.currency = currency
    
    @property
    def category(self) -> str:
        return "energy_monitor"
    
    def read_state(self) -> Dict[str, Any]:
        """Read energy data."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/energy"})
            state = {
                "power_watts": response.get("power", 0.0),
                "voltage": response.get("voltage", 0.0),
                "current_amps": response.get("current", 0.0),
                "energy_kwh": response.get("energy", 0.0),
                "frequency_hz": response.get("frequency"),
                "power_factor": response.get("power_factor"),
                "cost_today": response.get("cost_today", 0.0)
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {
                "power_watts": 0.0,
                "voltage": 0.0,
                "current_amps": 0.0,
                "energy_kwh": 0.0
            }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def read(self, fresh: bool = False) -> EnergyReading:
        """Get energy reading."""
        if fresh:
            self.cache.invalidate(self.id)
        
        state = self.read_state()
        return EnergyReading(
            power_watts=state.get("power_watts", 0.0),
            voltage=state.get("voltage", 0.0),
            current_amps=state.get("current_amps", 0.0),
            energy_kwh=state.get("energy_kwh", 0.0),
            frequency_hz=state.get("frequency_hz"),
            power_factor=state.get("power_factor")
        )
    
    def reset_counter(self, confirm: Optional[bool] = None) -> CommandResult:
        """Reset energy counter."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/reset", "counter": "energy"},
            expected_state={"energy_kwh": 0.0},
            command_name="reset_counter"
        )
    
    @property
    def power(self) -> float:
        """Current power in watts."""
        return self.read_state().get("power_watts", 0.0)
    
    @property
    def today_cost(self) -> float:
        """Estimated cost today."""
        return self.read_state().get("cost_today", 0.0)
    
    def calculate_cost(self, kwh: float) -> float:
        """Calculate cost for given energy."""
        return kwh * self.cost_per_kwh