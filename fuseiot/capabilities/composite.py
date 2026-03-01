from typing import Dict, Any, Optional
from .base import Capability, CapabilityConfig
from .switchable import Switchable
from .energy_monitor import EnergyMonitor
from ..logging_config import get_logger

logger = get_logger("capabilities.composite")


class CompositeCapability(Capability):
    """
    Base for devices with multiple capabilities.
    
    Example: Smart plug with power monitoring.
    """
    
    def __init__(self, protocol, cache, config=None, event_bus=None, **kwargs):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self._capabilities: Dict[str, Capability] = {}
    
    def add_capability(self, name: str, capability: Capability) -> None:
        """Add sub-capability."""
        self._capabilities[name] = capability
    
    def get_capability(self, name: str) -> Optional[Capability]:
        """Get sub-capability."""
        return self._capabilities.get(name)
    
    @property
    def category(self) -> str:
        return "composite"
    
    def read_state(self) -> Dict[str, Any]:
        """Read all sub-capability states."""
        state = {}
        for name, cap in self._capabilities.items():
            try:
                state[name] = cap.read_state()
            except Exception as e:
                logger.warning("sub_capability_read_failed", name=name, error=str(e))
                state[name] = {"error": str(e)}
        return state


class SmartPlug(CompositeCapability):
    """
    Smart plug with power monitoring.
    
    Combines Switchable + EnergyMonitor.
    """
    
    def __init__(self, protocol, cache, config=None, cost_per_kwh: float = 0.15, event_bus=None, **kwargs):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        
        # Create sub-capabilities
        self.switch = Switchable(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.energy = EnergyMonitor(protocol, cache, config, cost_per_kwh=cost_per_kwh, event_bus=event_bus, **kwargs)
        
        self.add_capability("switch", self.switch)
        self.add_capability("energy", self.energy)
    
    @property
    def category(self) -> str:
        return "smart_plug"
    
    def on(self, **kwargs):
        """Turn on."""
        return self.switch.on(**kwargs)
    
    def off(self, **kwargs):
        """Turn off."""
        return self.switch.off(**kwargs)
    
    @property
    def is_on(self) -> bool:
        """Power state."""
        return self.switch.is_on
    
    @property
    def power(self) -> float:
        """Current power draw."""
        return self.energy.power
    
    @property
    def today_cost(self) -> float:
        """Cost today."""
        return self.energy.today_cost