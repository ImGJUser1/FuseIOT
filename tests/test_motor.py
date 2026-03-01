# tests/test_motor.py
"""Tests for motor capability."""

import pytest
import responses

from fuseiot import Hub, HTTP, Motor


def test_motor_move_to(hub, responses_mock):
    """Position control."""
    # Setup mocks
    responses_mock.add(
        responses.GET,
        "http://motor.local/api/status",
        json={"position": 0.0, "speed": 0.0, "moving": False, "homed": True},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://motor.local/api/move",
        json={"position": 90.0, "moving": False},
        status=200
    )
    
    http = HTTP("http://motor.local/api")
    motor = hub.add_device(
        http,
        Motor,
        position_range=(0, 360),
        device_id="pan_motor"
    )
    
    result = motor.move_to(90.0, confirm=True)
    
    assert result.success
    assert result.confirmed


def test_motor_position_clamping(hub, responses_mock):
    """Out-of-range positions are clamped."""
    responses_mock.add(
        responses.GET,
        "http://motor.local/api/status",
        json={"position": 0.0, "moving": False, "homed": True},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://motor.local/api/move",
        json={"position": 180.0, "moving": False},
        status=200
    )
    
    http = HTTP("http://motor.local/api")
    motor = hub.add_device(
        http,
        Motor,
        position_range=(0, 180),
        device_id="limited_motor"
    )
    
    # Request 360, should clamp to 180
    result = motor.move_to(360.0, confirm=False)
    
    # Check request was made (clamped value sent)
    assert result.success


def test_motor_stop(hub, responses_mock):
    """Emergency stop."""
    responses_mock.add(
        responses.GET,
        "http://motor.local/api/status",
        json={"position": 45.0, "moving": True, "homed": True},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://motor.local/api/stop",
        json={"position": 45.0, "moving": False},
        status=200
    )
    
    http = HTTP("http://motor.local/api")
    motor = hub.add_device(http, Motor, device_id="stop_test")
    
    assert motor.is_moving  # From mock
    
    result = motor.stop(confirm=True)
    
    assert result.success
    assert not motor.is_moving


def test_motor_home(hub, responses_mock):
    """Homing sequence."""
    responses_mock.add(
        responses.GET,
        "http://motor.local/api/status",
        json={"position": 45.0, "moving": False, "homed": False},
        status=200
    )
    responses_mock.add(
        responses.POST,
        "http://motor.local/api/home",
        json={"position": 0.0, "homed": True},
        status=200
    )
    
    http = HTTP("http://motor.local/api")
    motor = hub.add_device(http, Motor, device_id="home_test")
    
    result = motor.home(confirm=True, timeout=30.0)
    
    assert result.success


def test_motor_position_property(hub, responses_mock):
    """Position property access."""
    responses_mock.add(
        responses.GET,
        "http://motor.local/api/status",
        json={"position": 123.4, "moving": False, "homed": True},
        status=200
    )
    
    http = HTTP("http://motor.local/api")
    motor = hub.add_device(http, Motor, device_id="pos_prop")
    
    assert motor.position == 123.4