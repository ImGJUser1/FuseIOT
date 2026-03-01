import random
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from ..protocols.base import Protocol, ProtocolConfig, ConnectionState
from ..logging_config import get_logger

logger = get_logger("simulation")


@dataclass
class VirtualDeviceConfig:
    """Virtual device configuration."""
    initial_state: Dict[str, Any] = None
    latency_ms: float = 50.0
    failure_rate: float = 0.0  # 0-1 probability of failure
    jitter_ms: float = 10.0  # Random latency variation
    protocol: str = "http"


class VirtualDevice(Protocol):
    """
    Simulated device for testing.
    
    Mimics real device behavior without actual hardware.
    """
    
    def __init__(
        self,
        device_type: str = "switchable",
        config: Optional[VirtualDeviceConfig] = None,
        **kwargs
    ):
        super().__init__(ProtocolConfig())
        self.device_type = device_type
        self.config = config or VirtualDeviceConfig()
        self._state = self.config.initial_state or {"power": False}
        self._handlers: Dict[str, Callable] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default command handlers."""
        if self.device_type == "switchable":
            self._handlers["/on"] = self._handle_on
            self._handlers["/off"] = self._handle_off
            self._handlers["/state"] = self._handle_state_read
        elif self.device_type == "sensor":
            self._handlers["/reading"] = self._handle_sensor_read
        elif self.device_type == "motor":
            self._handlers["/status"] = self._handle_motor_status
            self._handlers["/move"] = self._handle_motor_move
    
    @property
    def endpoint(self) -> str:
        return f"virtual:{self.device_type}"
    
    def connect(self) -> bool:
        """Simulate connection."""
        self._update_state(ConnectionState.CONNECTED)
        logger.info("virtual_device_connected", type=self.device_type)
        return True
    
    def disconnect(self) -> None:
        """Simulate disconnection."""
        self._update_state(ConnectionState.DISCONNECTED)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate command processing."""
        # Simulate latency
        actual_latency = self.config.latency_ms + random.uniform(
            -self.config.jitter_ms, 
            self.config.jitter_ms
        )
        time.sleep(max(0, actual_latency / 1000))
        
        # Simulate failure
        if random.random() < self.config.failure_rate:
            raise Exception("Simulated device failure")
        
        # Route to handler
        path = payload.get("_path", "/")
        handler = self._handlers.get(path)
        
        if handler:
            return handler(payload)
        
        return {"error": "Unknown command", "path": path}
    
    def _handle_on(self, payload: Dict) -> Dict[str, Any]:
        self._state["power"] = True
        return {"power": True, "status": "ok"}
    
    def _handle_off(self, payload: Dict) -> Dict[str, Any]:
        self._state["power"] = False
        return {"power": False, "status": "ok"}
    
    def _handle_state_read(self, payload: Dict) -> Dict[str, Any]:
        return self._state
    
    def _handle_sensor_read(self, payload: Dict) -> Dict[str, Any]:
        # Simulate sensor drift
        base_value = self._state.get("value", 20.0)
        drift = random.uniform(-0.5, 0.5)
        return {
            "value": base_value + drift,
            "unit": self._state.get("unit", "celsius"),
            "timestamp": time.time()
        }
    
    def _handle_motor_status(self, payload: Dict) -> Dict[str, Any]:
        return {
            "position": self._state.get("position", 0.0),
            "speed": 0.0,
            "moving": False,
            "homed": self._state.get("homed", True)
        }
    
    def _handle_motor_move(self, payload: Dict) -> Dict[str, Any]:
        target = payload.get("position", 0.0)
        self._state["position"] = target
        return {"position": target, "moving": False}
    
    def set_state(self, state: Dict[str, Any]) -> None:
        """Manually set device state."""
        self._state.update(state)
    
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, payload)