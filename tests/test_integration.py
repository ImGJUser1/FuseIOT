# tests/test_integration.py
"""Integration tests."""

import pytest
import responses
import time

from fuseiot import Hub, HTTP, Switchable, Sensor, Motor


@pytest.mark.integration
def test_thermostat_scenario(responses_mock):
    """Complete thermostat: sensor controls heater."""
    # Mock temperature sensor
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 18.5, "unit": "celsius", "timestamp": time.time()},
        status=200
    )
    
    # Mock heater (initially off)
    responses_mock.add(
        responses.GET,
        "http://heater.local/api/state",
        json={"power": False},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://heater.local/api/on",
        json={"power": True, "status": "ok"},
        status=200
    )
    # Confirmation poll
    responses_mock.add(
        responses.GET,
        "http://heater.local/api/state",
        json={"power": True},
        status=200
    )
    
    hub = Hub()
    
    # Setup devices
    temp_sensor = hub.add_device(
        HTTP("http://sensor.local/api"),
        Sensor,
        unit="celsius",
        device_id="room_temp"
    )
    
    heater = hub.add_device(
        HTTP("http://heater.local/api"),
        Switchable,
        device_id="heater"
    )
    
    # Read temperature
    reading = temp_sensor.read(fresh=True)
    assert reading["value"] == 18.5
    
    # Control logic: if cold, turn on heater
    if reading["value"] < 20.0:
        result = heater.on(confirm=True)
        assert result.success
        assert result.confirmed
    
    assert heater.is_on


@pytest.mark.integration
def test_multi_device_hub(responses_mock):
    """Multiple devices in single hub."""
    # Device 1: Light
    responses_mock.add(
        responses.GET,
        "http://light1.local/api/state",
        json={"power": False},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://light1.local/api/on",
        json={"power": True},
        status=200
    )
    
    # Device 2: Fan
    responses_mock.add(
        responses.GET,
        "http://fan1.local/api/state",
        json={"power": False},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://fan1.local/api/on",
        json={"power": True},
        status=200
    )
    
    # Device 3: Sensor
    responses_mock.add(
        responses.GET,
        "http://temp.local/api/reading",
        json={"value": 22.0},
        status=200
    )
    
    hub = Hub()
    
    # Add all devices
    light = hub.add_device(
        HTTP("http://light1.local/api"),
        Switchable,
        device_id="living_room_light"
    )
    fan = hub.add_device(
        HTTP("http://fan1.local/api"),
        Switchable,
        device_id="bedroom_fan"
    )
    temp = hub.add_device(
        HTTP("http://temp.local/api"),
        Sensor,
        device_id="ambient_temp"
    )
    
    # Verify all registered
    assert len(hub) == 3
    assert "living_room_light" in hub
    assert "bedroom_fan" in hub
    assert "ambient_temp" in hub
    
    # Control multiple
    light.on(confirm=False)
    fan.on(confirm=False)
    
    # Read sensor
    reading = temp.read()
    assert reading["value"] == 22.0
    
    # Hub stats
    stats = hub.stats()
    assert stats["devices_active"] == 3


@pytest.mark.integration
def test_device_categories_filtering(responses_mock):
    """Filter devices by category."""
    # Setup mocks for 2 switches and 1 sensor
    for i in range(2):
        responses_mock.add(
            responses.GET,
            f"http://switch{i}.local/api/state",
            json={"power": False},
            status=200
        )
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 0.0},
        status=200
    )
    
    hub = Hub()
    
    hub.add_device(HTTP("http://switch0.local/api"), Switchable, device_id="s1")
    hub.add_device(HTTP("http://switch1.local/api"), Switchable, device_id="s2")
    hub.add_device(HTTP("http://sensor.local/api"), Sensor, device_id="t1")
    
    # Filter by category
    switches = hub.list_devices(category="switchable")
    assert len(switches) == 2
    assert "s1" in switches
    assert "s2" in switches
    
    sensors = hub.list_devices(category="sensor")
    assert len(sensors) == 1
    assert "t1" in sensors


@pytest.mark.integration
def test_error_recovery(responses_mock):
    """Command failure and retry."""
    # First call fails, second succeeds
    responses_mock.add(
        responses.POST,
        "http://device.local/api/on",
        status=503  # Service unavailable
    )
    responses_mock.add(
        responses.POST,
        "http://device.local/api/on",
        json={"power": True},
        status=200
    )
    responses_mock.add(
        responses.GET,
        "http://device.local/api/state",
        json={"power": True},
        status=200
    )
    
    hub = Hub()
    device = hub.add_device(
        HTTP("http://device.local/api"),
        Switchable,
        device_id="reliable_device"
    )
    
    # Should retry and succeed
    result = device.on(confirm=True)
    
    assert result.success
    # Verify retry happened (2 calls)
    assert len([c for c in responses_mock.calls if "/on" in c.request.url]) == 2


@pytest.mark.integration
def test_cache_invalidation_on_command(responses_mock):
    """State cache updates after command."""
    # Initial state
    responses_mock.add(
        responses.GET,
        "http://device.local/api/state",
        json={"power": False},
        status=200
    )
    # Command
    responses_mock.add(
        responses.POST,
        "http://device.local/api/on",
        json={"power": True},
        status=200
    )
    # Confirmation poll
    responses_mock.add(
        responses.GET,
        "http://device.local/api/state",
        json={"power": True},
        status=200
    )
    
    hub = Hub(default_ttl=60.0)  # Long TTL
    device = hub.add_device(
        HTTP("http://device.local/api"),
        Switchable,
        device_id="cached_device"
    )
    
    # Initial read (caches)
    state1 = device.read_state()
    assert state1["power"] is False
    
    # Command (should update cache via confirmation)
    device.on(confirm=True)
    
    # Read again (should be fresh from confirmation)
    state2 = device.read_state()
    assert state2["power"] is True