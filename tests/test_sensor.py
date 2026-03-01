# tests/test_sensor.py
"""Tests for sensor capability."""

import pytest
import responses

from fuseiot import Hub, HTTP, Sensor
from fuseiot.exceptions import StateError


def test_sensor_reading(hub, responses_mock):
    """Basic sensor reading."""
    # Setup mock
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 25.5, "unit": "celsius"},
        status=200
    )
    
    http = HTTP("http://sensor.local/api")
    temp = hub.add_device(http, Sensor, unit="celsius", device_id="temp1")
    
    reading = temp.read(fresh=True)
    
    assert reading["value"] == 25.5
    assert reading["unit"] == "celsius"


def test_sensor_caching(hub, responses_mock):
    """Cache reduces polling."""
    # First call hits network
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 20.0},
        status=200
    )
    
    http = HTTP("http://sensor.local/api")
    sensor = hub.add_device(http, Sensor, device_id="cached_sensor")
    
    # First read - network
    r1 = sensor.read(fresh=False)
    assert r1["value"] == 20.0
    
    # Second read - cache (no new mock needed)
    r2 = sensor.read(fresh=False)
    assert r2["value"] == 20.0
    
    # Fresh read bypasses cache
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 21.0},
        status=200
    )
    r3 = sensor.read(fresh=True)
    assert r3["value"] == 21.0


def test_sensor_value_property(hub, responses_mock):
    """Convenience value property."""
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 42.0},
        status=200
    )
    
    http = HTTP("http://sensor.local/api")
    sensor = hub.add_device(http, Sensor, device_id="prop_test")
    
    assert sensor.value == 42.0


def test_sensor_calibrate(hub, responses_mock):
    """Calibration command."""
    responses_mock.add(
        responses.GET,
        "http://sensor.local/api/reading",
        json={"value": 0.0},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://sensor.local/api/calibrate",
        json={"calibrated": True},
        status=200
    )
    
    http = HTTP("http://sensor.local/api")
    sensor = hub.add_device(http, Sensor, device_id="cal_sensor")
    
    result = sensor.calibrate(reference_value=100.0)
    
    assert result.success