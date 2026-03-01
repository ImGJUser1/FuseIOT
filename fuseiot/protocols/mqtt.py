import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from queue import Queue, Empty
from .base import Protocol, ProtocolConfig
from ..exceptions import ProtocolError

try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False


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
    
    @property
    def endpoint(self) -> str:
        return f"mqtt://{self.broker}:{self.port}/{self.topic_prefix}"
    
    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: dict,
        rc: int,
        properties: Any = None
    ) -> None:
        """Connection callback."""
        if rc == 0:
            self._connected = True
            # Resubscribe to previous topics
            for topic in self._subscriptions:
                client.subscribe(topic, qos=self.qos)
        else:
            self._connected = False
            self._last_error = f"MQTT connect failed: {rc}"
    
    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int
    ) -> None:
        """Disconnection callback."""
        self._connected = False
        if rc != 0:
            self._last_error = f"Unexpected disconnect: {rc}"
    
    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        msg: mqtt.MQTTMessage
    ) -> None:
        """Incoming message handler."""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}
        
        # Check for response correlation
        with self._lock:
            self._response_queue.put({
                "topic": topic,
                "payload": payload,
                "timestamp": time.time()
            })
        
        # Call user handler if registered
        handler = self._subscriptions.get(topic)
        if handler:
            handler(topic, payload)
    
    def connect(self) -> bool:
        """Establish MQTT connection."""
        self._client = mqtt.Client(client_id=self.client_id)
        
        if self.username and self.password:
            self._client.username_pw_set(self.username, self.password)
        
        # Callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        
        try:
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            
            # Wait for connection
            start = time.time()
            while not self._connected and time.time() - start < self.timeout:
                time.sleep(0.1)
            
            return self._connected
            
        except Exception as e:
            self._last_error = str(e)
            return False
    
    def disconnect(self) -> None:
        """Clean disconnect."""
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None
        self._connected = False
    
    def subscribe(self, topic: str, handler: Callable[[str, Any], None]) -> None:
        """Subscribe to topic with handler."""
        full_topic = f"{self.topic_prefix}/{topic}"
        self._subscriptions[full_topic] = handler
        if self._connected and self._client:
            self._client.subscribe(full_topic, qos=self.qos)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish command and wait for response.
        
        Args:
            payload: Must contain '_topic' for publish target
                    May contain '_response_topic' to wait for reply
        """
        if not self._connected or not self._client:
            raise ProtocolError(
                "Not connected",
                protocol="mqtt",
                endpoint=self.endpoint
            )
        
        topic = payload.get("_topic", "cmd")
        response_topic = payload.get("_response_topic")
        full_topic = f"{self.topic_prefix}/{topic}"
        
        # Prepare payload
        body = {k: v for k, v in payload.items() if not k.startswith("_")}
        
        try:
            # Publish
            info = self._client.publish(
                full_topic,
                json.dumps(body),
                qos=self.qos
            )
            info.wait_for_publish(timeout=self.timeout)
            
            # Wait for response if specified
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
        
        # Subscribe temporarily
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