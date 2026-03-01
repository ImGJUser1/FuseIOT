# tests/test_mqtt.py
"""Tests for MQTT protocol."""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock

# Skip all MQTT tests if paho not available
try:
    import paho.mqtt.client as mqtt
    PAHO_AVAILABLE = True
except ImportError:
    PAHO_AVAILABLE = False

pytestmark = pytest.mark.skipif(not PAHO_AVAILABLE, reason="paho-mqtt not installed")

from fuseiot.protocols.mqtt import MQTT
from fuseiot.exceptions import ProtocolError


@pytest.fixture
def mock_mqtt_client():
    """Mock paho client."""
    with patch('paho.mqtt.client.Client') as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        # Simulate successful connection
        def simulate_connect(host, port, keepalive):
            return 0
        
        mock_client.connect = simulate_connect
        mock_client.is_connected.return_value = True
        
        yield mock_client


def test_mqtt_creation():
    """MQTT protocol initialization."""
    mqtt_proto = MQTT(
        broker="192.168.1.46",
        port=1883,
        client_id="test_client",
        topic_prefix="lab/devices"
    )
    
    assert mqtt_proto.broker == "192.168.1.46"
    assert mqtt_proto.port == 1883
    assert mqtt_proto.topic_prefix == "lab/devices"


def test_mqtt_connect(mock_mqtt_client):
    """Connection establishment."""
    mqtt_proto = MQTT(broker="192.168.1.46")
    
    # Manually set connected state for test
    mqtt_proto._connected = True
    mqtt_proto._update_state(ConnectionState.CONNECTED)
    
    assert mqtt_proto.is_connected is True


def test_mqtt_send_publish(mock_mqtt_client):
    """Publish command."""
    mqtt_proto = MQTT(broker="192.168.1.46")
    mqtt_proto._client = mock_mqtt_client
    mqtt_proto._connected = True
    mqtt_proto._update_state(ConnectionState.CONNECTED)
    
    # Mock publish info
    mock_info = Mock()
    mock_info.wait_for_publish.return_value = True
    mock_mqtt_client.publish.return_value = mock_info
    
    result = mqtt_proto.send({
        "_topic": "relay01/cmd",
        "power": True
    })
    
    # Verify publish called
    mock_mqtt_client.publish.assert_called_once()
    call_args = mock_mqtt_client.publish.call_args
    
    # Check topic contains the command
    assert "relay01/cmd" in call_args[0][0]
    # Check payload is JSON
    payload = json.loads(call_args[0][1])
    assert payload["power"] is True


def test_mqtt_subscribe(mock_mqtt_client):
    """Topic subscription."""
    mqtt_proto = MQTT(broker="192.168.1.46")
    mqtt_proto._client = mock_mqtt_client
    mqtt_proto._connected = True
    
    handler = Mock()
    mqtt_proto.subscribe("sensors/temp", handler)
    
    # Should subscribe with full topic prefix
    mock_mqtt_client.subscribe.assert_called_once()
    call_args = mock_mqtt_client.subscribe.call_args
    assert "sensors/temp" in call_args[0][0]


def test_mqtt_not_connected():
    """Operations fail when not connected."""
    mqtt_proto = MQTT(broker="192.168.1.46")
    # Don't connect - _connected should be False by default
    
    with pytest.raises(ProtocolError) as exc:
        mqtt_proto.send({"_topic": "test"})
    
    assert "Not connected" in str(exc.value)


def test_mqtt_auth():
    """Authentication parameters."""
    mqtt_proto = MQTT(
        broker="192.168.1.46",
        username="device_user",
        password="secret"
    )
    
    # Just verify stored
    assert mqtt_proto.username == "device_user"
    assert mqtt_proto.password == "secret"