import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from queue import Queue, Empty

from .base import Protocol, ProtocolConfig, ConnectionState
from ..exceptions import ProtocolError
from ..logging_config import get_logger

logger = get_logger("protocols.mqtt")

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False
    mqtt = None


@dataclass
class MQTTConfig(ProtocolConfig):
    """MQTT-specific configuration."""
    broker: str = "localhost"
    port: int = 1883
    client_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    topic_prefix: str = "device"
    qos: int = 1


class MQTT(Protocol):
    """
    MQTT device communication.
    
    Supports:
    - QoS 0, 1, 2
    - Last will and testament
    - Retained messages
    - Subscribe/publish patterns
    """
    
    def __init__(
        self,
        broker: str,
        port: int = 1883,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        topic_prefix: str = "device",
        qos: int = 1,
        timeout: float = 5.0,
        config: Optional[ProtocolConfig] = None
    ):
        if not PAHO_AVAILABLE:
            raise ImportError("paho-mqtt required: pip install paho-mqtt")
        
        super().__init__(config)
        self.broker = broker
        self.port = port
        self.client_id = client_id or f"fuseiot_{int(time.time())}"
        self.username = username
        self.password = password
        self.topic_prefix = topic_prefix.strip("/")
        self.qos = qos
        self.timeout = timeout
        
        # Internal state
        self._client: Optional[mqtt.Client] = None
        self._response_queue: Queue = Queue()
        self._subscriptions: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._connected = False
    
    @property
    def endpoint(self) -> str:
        return f"mqtt://{self.broker}:{self.port}/{self.topic_prefix}"
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Connection callback."""
        if rc == 0:
            self._connected = True
            self._update_state(ConnectionState.CONNECTED)
            for topic in self._subscriptions:
                client.subscribe(topic, qos=self.qos)
        else:
            self._connected = False
            self._update_state(ConnectionState.FAILED, f"MQTT connect failed: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Disconnection callback."""
        self._connected = False
        self._update_state(ConnectionState.DISCONNECTED)
        if rc != 0:
            self._last_error = f"Unexpected disconnect: {rc}"
    
    def _on_message(self, client, userdata, msg):
        """Incoming message handler."""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}
        
        with self._lock:
            self._response_queue.put({
                "topic": topic,
                "payload": payload,
                "timestamp": time.time()
            })
        
        handler = self._subscriptions.get(topic)
        if handler:
            try:
                handler(topic, payload)
            except Exception as e:
                logger.error("mqtt_handler_error", topic=topic, error=str(e))
    
    def connect(self) -> bool:
        """Establish MQTT connection."""
        try:
            self._client = mqtt.Client(client_id=self.client_id)
            
            if self.username and self.password:
                self._client.username_pw_set(self.username, self.password)
            
            self._client.on_connect = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_message = self._on_message
            
            self._update_state(ConnectionState.CONNECTING)
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            
            start = time.time()
            while not self._connected and time.time() - start < self.timeout:
                time.sleep(0.1)
            
            return self._connected
            
        except Exception as e:
            self._update_state(ConnectionState.FAILED, str(e))
            return False
    
    def disconnect(self) -> None:
        """Clean disconnect."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._connected = False
        self._update_state(ConnectionState.DISCONNECTED)
    
    def subscribe(self, topic: str, handler: Callable[[str, Any], None]) -> None:
        """Subscribe to topic with handler."""
        full_topic = f"{self.topic_prefix}/{topic}"
        self._subscriptions[full_topic] = handler
        if self._connected and self._client:
            self._client.subscribe(full_topic, qos=self.qos)
            logger.debug("mqtt_subscribed", topic=full_topic)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Publish command and wait for response."""
        if not self._connected or not self._client:
            raise ProtocolError(
                "Not connected",
                protocol="mqtt",
                endpoint=self.endpoint
            )
        
        topic = payload.get("_topic", "cmd")
        response_topic = payload.get("_response_topic")
        full_topic = f"{self.topic_prefix}/{topic}"
        
        body = {k: v for k, v in payload.items() if not k.startswith("_")}
        
        try:
            info = self._client.publish(
                full_topic,
                json.dumps(body),
                qos=self.qos
            )
            info.wait_for_publish(timeout=self.timeout)
            
            if response_topic:
                return self._wait_for_response(response_topic)
            
            return {"published": True, "topic": full_topic}
            
        except Exception as e:
            self._last_error = str(e)
            raise ProtocolError(
                message=f"MQTT publish failed: {e}",
                protocol="mqtt",
                endpoint=full_topic,
                original_error=e
            )
    
    def _wait_for_response(self, response_topic: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Block until response received on topic."""
        full_response_topic = f"{self.topic_prefix}/{response_topic}"
        deadline = time.time() + (timeout or self.timeout)
        
        self._client.subscribe(full_response_topic, qos=self.qos)
        
        try:
            while time.time() < deadline:
                try:
                    msg = self._response_queue.get(timeout=0.1)
                    if msg["topic"] == full_response_topic:
                        return msg["payload"]
                except Empty:
                    continue
            
            raise TimeoutError(f"No response on {full_response_topic}")
            
        finally:
            self._client.unsubscribe(full_response_topic)
    
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, payload)