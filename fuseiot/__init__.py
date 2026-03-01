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
from fuseiot.protocols.websocket import WebSocket, WebSocketConfig
from fuseiot.protocols.serial import Serial, SerialConfig

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

# Cloud connectors
from fuseiot.cloud.base import CloudConnector
from fuseiot.cloud.aws_iot import AWSIoT
from fuseiot.cloud.azure_iot import AzureIoT
from fuseiot.cloud.gcp_iot import GCPIoT

# Edge computing
from fuseiot.edge.rules import RuleEngine, Rule, Condition, Action, Trigger

# Discovery
from fuseiot.discovery.mdns import MDNSDiscovery, DiscoveryResult

# Monitoring
from fuseiot.monitoring.metrics import MetricsCollector, PrometheusMetrics
from fuseiot.monitoring.health import HealthServer, HealthStatus as ServerHealth

# Simulation
from fuseiot.simulation.virtual_device import VirtualDevice, VirtualDeviceConfig

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