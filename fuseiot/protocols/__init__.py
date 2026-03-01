# fuseiot/protocols/__init__.py
"""Protocol implementations for FuseIoT."""

from fuseiot.protocols.base import Protocol, ProtocolConfig, AsyncProtocol, ConnectionState
from fuseiot.protocols.http import HTTP, HTTPConfig
from fuseiot.protocols.https import HTTPS, HTTPSConfig
from fuseiot.protocols.mqtt import MQTT, MQTTConfig
from fuseiot.protocols.mqtts import MQTTS, MQTTSConfig

# Try to import optional protocols
try:
    from fuseiot.protocols.web_socket import WebSocket, WebSocketConfig
except ImportError:
    WebSocket = None
    WebSocketConfig = None

try:
    from fuseiot.protocols.serial import Serial, SerialConfig
except ImportError:
    Serial = None
    SerialConfig = None

__all__ = [
    "Protocol",
    "ProtocolConfig",
    "AsyncProtocol",
    "ConnectionState",
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
]