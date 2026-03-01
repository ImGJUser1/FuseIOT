# tests/conftest.py
"""pytest configuration with standard library mocks only."""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
import responses

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
def responses_mock():
    """HTTP mocking fixture using responses library."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_http_relay(responses_mock):
    """Pre-configured mock HTTP relay endpoint."""
    base_url = "http://192.168.1.45/api"
    
    # State endpoint
    responses_mock.add(
        responses.GET,
        f"{base_url}/state",
        json={"power": False},
        status=200
    )
    
    # On endpoint
    responses_mock.add(
        responses.POST,
        f"{base_url}/on",
        json={"power": True, "status": "ok"},
        status=200
    )
    
    # Off endpoint
    responses_mock.add(
        responses.POST,
        f"{base_url}/off",
        json={"power": False, "status": "ok"},
        status=200
    )
    
    return base_url


@pytest.fixture
def mock_http_sensor(responses_mock):
    """Pre-configured mock HTTP sensor endpoint."""
    base_url = "http://192.168.1.46/api"
    
    responses_mock.add(
        responses.GET,
        f"{base_url}/reading",
        json={"value": 22.5, "unit": "celsius", "timestamp": 1234567890},
        status=200
    )
    
    return base_url


@pytest.fixture
def mock_http_motor(responses_mock):
    """Pre-configured mock HTTP motor endpoint."""
    base_url = "http://192.168.1.47/api"
    
    # Status endpoint
    responses_mock.add(
        responses.GET,
        f"{base_url}/status",
        json={"position": 0.0, "speed": 0.0, "moving": False, "homed": True},
        status=200
    )
    
    # Move endpoint
    responses_mock.add(
        responses.POST,
        f"{base_url}/move",
        json={"position": 90.0, "moving": False},
        status=200
    )
    
    # Home endpoint
    responses_mock.add(
        responses.POST,
        f"{base_url}/home",
        json={"position": 0.0, "homed": True},
        status=200
    )
    
    return base_url