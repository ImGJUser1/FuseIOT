# tests/test_switchable.py
"""Tests for switchable capability."""

import pytest
import responses

from fuseiot import Hub, HTTP, Switchable
from fuseiot.exceptions import CommandError


def test_switchable_on_off(hub, responses_mock):
    """Test basic on/off with confirmation."""
    # Setup mock
    responses_mock.post("http://test.local/api/on", json={"power": True})
    responses_mock.post("http://test.local/api/off", json={"power": False})
    responses_mock.get("http://test.local/api/state", json={"power": False})
    
    # Create device
    http = HTTP("http://test.local/api")
    relay = hub.add_device(http, Switchable, device_id="test_relay")
    
    # Test off (already off)
    result = relay.off(confirm=True)
    assert result.success
    assert result.confirmed
    
    # Test on
    responses_mock.get("http://test.local/api/state", json={"power": True})
    result = relay.on(confirm=True)
    assert result.success
    assert result.confirmed
    assert relay.is_on


def test_switchable_toggle(hub, responses_mock):
    """Test toggle switches state."""
    responses_mock.post("http://test.local/api/on", json={"power": True})
    responses_mock.post("http://test.local/api/off", json={"power": False})
    
    # First call returns off, second returns on
    responses_mock.add(
        responses.GET,
        "http://test.local/api/state",
        json={"power": False},
        status=200
    )
    responses_mock.add(
        responses.GET,
        "http://test.local/api/state",
        json={"power": True},
        status=200
    )
    
    http = HTTP("http://test.local/api")
    relay = hub.add_device(http, Switchable, device_id="toggle_test")
    
    # Toggle from off to on
    result = relay.toggle(confirm=True)
    assert result.success