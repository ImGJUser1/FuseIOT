

import pytest
from fuseiot import Hub, HTTP, Switchable
from fuseiot.exceptions import CommandError


def test_switchable_on_off(hub, requests_mock):
    """Test basic on/off with confirmation."""
    # Setup mock
    requests_mock.post("http://test.local/api/on", json={"power": True})
    requests_mock.post("http://test.local/api/off", json={"power": False})
    requests_mock.get("http://test.local/api/state", json={"power": False})
    
    # Create device
    http = HTTP("http://test.local/api")
    relay = hub.add_device(http, Switchable, device_id="test_relay")
    
    # Test off (already off)
    result = relay.off(confirm=True)
    assert result.success
    assert result.confirmed
    
    # Test on
    requests_mock.get("http://test.local/api/state", json={"power": True})
    result = relay.on(confirm=True)
    assert result.success
    assert result.confirmed
    assert relay.is_on


def test_switchable_toggle(hub, requests_mock):
    """Test toggle switches state."""
    requests_mock.post("http://test.local/api/on", json={"power": True})
    requests_mock.post("http://test.local/api/off", json={"power": False})
    requests_mock.get("http://test.local/api/state", [
        {"json": {"power": False}},  # First call
        {"json": {"power": True}},   # After toggle
    ])
    
    http = HTTP("http://test.local/api")
    relay = hub.add_device(http, Switchable)
    
    # Toggle from off to on
    result = relay.toggle(confirm=True)
    assert result.success