from typing import (
    Dict,
    Any,
    Optional,
    Callable,
    Union,
    Protocol,
    runtime_checkable,
    TypeVar,
    NewType,
)
from dataclasses import dataclass
from enum import Enum, auto


# Primitive type aliases
DeviceID = NewType("DeviceID", str)
Payload = Dict[str, Any]
Handler = Callable[..., Any]
T = TypeVar("T")


class CommandStatus(Enum):
    """
    Command lifecycle states.
    
    See fuseiot.result.CommandStatus for full version.
    This is lightweight alias for type hints.
    """
    PENDING = auto()
    SENT = auto()
    ACKNOWLEDGED = auto()
    CONFIRMED = auto()
    FAILED = auto()
    TIMEOUT = auto()


@dataclass(frozen=True)
class StateVector:
    """
    Immutable snapshot of device state.
    
    Frozen dataclass ensures state snapshots don't change
    after capture—essential for reliable comparison.
    
    Attributes:
        values: State key-value pairs
        timestamp: Monotonic clock when captured
        source: How state was obtained
        confidence: 0.0-1.0 reliability estimate
    """
    
    values: Dict[str, Any]
    timestamp: float
    source: str  # "command", "poll", "event", "cache", "inferred"
    confidence: float  # 0.0 to 1.0
    
    def get(self, key: str, default: Any = None) -> Any:
        """Safe value access."""
        return self.values.get(key, default)
    
    def __contains__(self, key: str) -> bool:
        """Key membership."""
        return key in self.values


# Runtime-checkable protocols

@runtime_checkable
class Readable(Protocol):
    """
    Protocol for readable capabilities.
    
    Any capability that can be read implements this.
    """
    
    def read(self, fresh: bool = False) -> StateVector:
        """
        Read current state.
        
        Args:
            fresh: If True, bypass cache and poll device
            
        Returns:
            StateVector with current values
        """
        ...


@runtime_checkable
class SwitchableProtocol(Protocol):
    """
    Protocol for on/off control.
    
    Minimal interface for binary actuators.
    """
    
    def on(self, confirm: bool = True, timeout: float = 2.0) -> Any:
        """Turn device on."""
        ...
    
    def off(self, confirm: bool = True, timeout: float = 2.0) -> Any:
        """Turn device off."""
        ...
    
    def toggle(self, confirm: bool = True, timeout: float = 2.0) -> Any:
        """Toggle current state."""
        ...
    
    @property
    def is_on(self) -> bool:
        """Current power state."""
        ...


@runtime_checkable
class SensorProtocol(Protocol):
    """
    Protocol for sensor readings.
    """
    
    def read(self, fresh: bool = False) -> Dict[str, Any]:
        """Read measurement."""
        ...
    
    @property
    def value(self) -> float:
        """Current value."""
        ...


@runtime_checkable
class MotorProtocol(Protocol):
    """
    Protocol for position/speed control.
    """
    
    def move_to(self, position: float, **kwargs) -> Any:
        """Move to absolute position."""
        ...
    
    def set_speed(self, speed: float) -> Any:
        """Set movement speed."""
        ...
    
    def stop(self) -> Any:
        """Emergency stop."""
        ...
    
    @property
    def position(self) -> float:
        """Current position."""
        ...
    
    @property
    def is_moving(self) -> bool:
        """Movement status."""
        ...


# Utility types

class HealthStatus(Enum):
    """Device health enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class DeviceInfo:
    """
    Static device information.
    """
    device_id: DeviceID
    category: str
    protocol: str
    endpoint: str
    capabilities: list[str]
    health: HealthStatus = HealthStatus.UNKNOWN