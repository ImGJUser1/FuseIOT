import pytest
import asyncio
from unittest.mock import Mock, MagicMock

from fuseiot import Hub, HTTP, Switchable, Sensor, Motor
from fuseiot.protocols.base import Protocol
from fuseiot.state.persistence import PersistenceBackend


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def hub():
    """Fresh Hub instance."""
    return Hub(default_ttl=0.1)


@pytest.fixture
def mock_protocol():
    """Mock protocol."""
    protocol = Mock(spec=Protocol)
    protocol.name = "mock"
    protocol.is_connected = True
    protocol.endpoint = "mock://test"
    protocol.send.return_value = {"status": "ok"}
    protocol.send_async = Mock()
    return protocol


@pytest.fixture
def mock_persistence():
    """Mock persistence backend."""
    persistence = Mock(spec=PersistenceBackend)
    persistence.get.return_value = None
    return persistence


@pytest.fixture
def mock_http_relay():
    """Mock HTTP relay responses."""
    import responses
    
    with responses.RequestsMock() as rsps:
        base_url = "http://192.168.1.45/api"
        
        rsps.add(responses.GET, f"{base_url}/state", json={"power": False}, status=200)
        rsps.add(responses.POST, f"{base_url}/on", json={"power": True}, status=200)
        rsps.add(responses.POST, f"{base_url}/off", json={"power": False}, status=200)
        
        yield base_url