
from fuseiot.__version__ import __version__, __version_info__

# Core classes
from fuseiot.hub import Hub, HubConfig
from fuseiot.result import CommandResult, CommandStatus, BatchResult
from fuseiot.state.cache import StateCache, CacheEntry
from fuseiot.state.persistence import PersistenceBackend, SQLiteBackend, RedisBackend
from fuseiot.state.events import EventBus, StateChangeEvent
from fuseiot.config import Config, from_yaml, from_json, from_env
from fuseiot.logging_config import configure_logging, get_logger

# Exceptions
from fuseiot.exceptions import (
    FuseIoTError,
    DeviceError,
    ProtocolError,
    CommandError,
    ConfirmationError,
    StateError,
    CacheError,
    ConfigurationError,
    ValidationError,
    TimeoutError,
    ConcurrencyError,
    ResourceExhaustedError,
    CircuitOpenError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
    DiscoveryError,
    CloudError,
)

# Types
from fuseiot.types import (
    StateVector,
    CommandStatus as CommandStatusEnum,
    DeviceID,
    Payload,
    Handler,
    Readable,
    SwitchableProtocol,
    SensorProtocol,
    MotorProtocol,
    DimmableProtocol,
    LockProtocol,
    RGBLightProtocol,
    HealthStatus,
    DeviceInfo,
    CapabilityType,
    ProtocolType,
    Color,
    Position,
    Brightness,
)

# Protocols
from fuseiot.protocols.base import Protocol, ProtocolConfig, AsyncProtocol
from fuseiot.protocols.http import HTTP, HTTPConfig
from fuseiot.protocols.https import HTTPS, HTTPSConfig
from fuseiot.protocols.mqtt import MQTT, MQTTConfig
from fuseiot.protocols.mqtts import MQTTS, MQTTSConfig

# Optional protocols - may raise ImportError if dependencies not installed
try:
    from fuseiot.protocols.web_socket import WebSocket, WebSocketConfig
except ImportError:
    WebSocket = None  # type: ignore
    WebSocketConfig = None  # type: ignore

try:
    from fuseiot.protocols.serial import Serial, SerialConfig
except ImportError:
    Serial = None  # type: ignore
    SerialConfig = None  # type: ignore

# Capabilities
from fuseiot.capabilities.base import Capability, CapabilityConfig, AsyncCapability
from fuseiot.capabilities.switchable import Switchable
from fuseiot.capabilities.dimmable import Dimmable
from fuseiot.capabilities.sensor import Sensor
from fuseiot.capabilities.motor import Motor
from fuseiot.capabilities.thermostat import Thermostat, ThermostatMode
from fuseiot.capabilities.lock import Lock, LockState
from fuseiot.capabilities.rgb_light import RGBLight, ColorMode
from fuseiot.capabilities.energy_monitor import EnergyMonitor
from fuseiot.capabilities.composite import CompositeCapability, SmartPlug

# Utilities
from fuseiot.utils.retry import retry, RetryConfig, async_retry, AsyncRetryConfig
from fuseiot.utils.async_tools import run_sync, run_async, AsyncLock, create_task_safely
from fuseiot.utils.circuit_breaker import CircuitBreaker, CircuitState
from fuseiot.utils.rate_limiter import RateLimiter, TokenBucket
from fuseiot.utils.validation import DeviceModel, CommandModel, StateModel

# Cloud connectors - optional
try:
    from fuseiot.cloud.base import CloudConnector
    from fuseiot.cloud.aws_iot import AWSIoT
    from fuseiot.cloud.azure_iot import AzureIoT
    from fuseiot.cloud.gcp_iot import GCPIoT
except ImportError:
    CloudConnector = None  # type: ignore
    AWSIoT = None  # type: ignore
    AzureIoT = None  # type: ignore
    GCPIoT = None  # type: ignore

# Edge computing
try:
    from fuseiot.edge.rules import RuleEngine, Rule, Condition, Action, Trigger
except ImportError:
    RuleEngine = None  # type: ignore
    Rule = None  # type: ignore
    Condition = None  # type: ignore
    Action = None  # type: ignore
    Trigger = None  # type: ignore

# Discovery
try:
    from fuseiot.discovery.mdns import MDNSDiscovery, DiscoveryResult
except ImportError:
    MDNSDiscovery = None  # type: ignore
    DiscoveryResult = None  # type: ignore

# Monitoring
try:
    from fuseiot.monitoring.metrics import MetricsCollector, PrometheusMetrics
    from fuseiot.monitoring.health import HealthServer, HealthStatus as ServerHealth
except ImportError:
    MetricsCollector = None  # type: ignore
    PrometheusMetrics = None  # type: ignore
    HealthServer = None  # type: ignore
    ServerHealth = None  # type: ignore

# Simulation
try:
    from fuseiot.simulation.virtual_device import VirtualDevice, VirtualDeviceConfig
except ImportError:
    VirtualDevice = None  # type: ignore
    VirtualDeviceConfig = None  # type: ignore

__all__ = [
    # Version
    "__version__",
    "__version_info__",
    
    # Core
    "Hub",
    "HubConfig",
    "CommandResult",
    "CommandStatus",
    "CommandStatusEnum",
    "BatchResult",
    "StateCache",
    "CacheEntry",
    "PersistenceBackend",
    "SQLiteBackend",
    "RedisBackend",
    "EventBus",
    "StateChangeEvent",
    "Config",
    "from_yaml",
    "from_json",
    "from_env",
    "configure_logging",
    "get_logger",
    
    # Exceptions
    "FuseIoTError",
    "DeviceError",
    "ProtocolError",
    "CommandError",
    "ConfirmationError",
    "StateError",
    "CacheError",
    "ConfigurationError",
    "ValidationError",
    "TimeoutError",
    "ConcurrencyError",
    "ResourceExhaustedError",
    "CircuitOpenError",
    "RateLimitError",
    "AuthenticationError",
    "AuthorizationError",
    "DiscoveryError",
    "CloudError",
    
    # Types
    "StateVector",
    "DeviceID",
    "Payload",
    "Handler",
    "Readable",
    "SwitchableProtocol",
    "SensorProtocol",
    "MotorProtocol",
    "DimmableProtocol",
    "LockProtocol",
    "RGBLightProtocol",
    "HealthStatus",
    "DeviceInfo",
    "CapabilityType",
    "ProtocolType",
    "Color",
    "Position",
    "Brightness",
    
    # Protocols
    "Protocol",
    "AsyncProtocol",
    "ProtocolConfig",
    "HTTP",
    "HTTPConfig",
    "HTTPS",
    "HTTPSConfig",
    "MQTT",
    "MQTTConfig",
    "MQTTS",
    "MQTTSConfig",
    "WebSocket",
    "WebSocketConfig",
    "Serial",
    "SerialConfig",
    
    # Capabilities
    "Capability",
    "AsyncCapability",
    "CapabilityConfig",
    "Switchable",
    "Dimmable",
    "Sensor",
    "Motor",
    "Thermostat",
    "ThermostatMode",
    "Lock",
    "LockState",
    "RGBLight",
    "ColorMode",
    "EnergyMonitor",
    "CompositeCapability",
    "SmartPlug",
    
    # Utilities
    "retry",
    "RetryConfig",
    "async_retry",
    "AsyncRetryConfig",
    "run_sync",
    "run_async",
    "AsyncLock",
    "create_task_safely",
    "CircuitBreaker",
    "CircuitState",
    "RateLimiter",
    "TokenBucket",
    "DeviceModel",
    "CommandModel",
    "StateModel",
    
    # Cloud
    "CloudConnector",
    "AWSIoT",
    "AzureIoT",
    "GCPIoT",
    
    # Edge
    "RuleEngine",
    "Rule",
    "Condition",
    "Action",
    "Trigger",
    
    # Discovery
    "MDNSDiscovery",
    "DiscoveryResult",
    
    # Monitoring
    "MetricsCollector",
    "PrometheusMetrics",
    "HealthServer",
    "ServerHealth",
    
    # Simulation
    "VirtualDevice",
    "VirtualDeviceConfig",
]