
import pytest
from fuseiot import Hub, HTTP, Switchable, Sensor
from fuseiot.exceptions import ConfigurationError, DeviceError


def test_hub_creation():
    """Hub initializes with empty registry."""
    hub = Hub()
    assert len(hub) == 0
    assert "test" not in hub


def test_add_device_success(hub, mock_protocol):
    """Device registration works."""
    device = hub.add_device(
        mock_protocol,
        Switchable,
        device_id="test_relay"
    )
    
    assert len(hub) == 1
    assert "test_relay" in hub
    assert hub["test_relay"] is device


def test_add_device_duplicate(hub, mock_protocol):
    """Duplicate device ID raises error."""
    hub.add_device(mock_protocol, Switchable, device_id="dup")
    
    with pytest.raises(ConfigurationError) as exc:
        hub.add_device(mock_protocol, Switchable, device_id="dup")
    
    assert "dup" in str(exc.value)


def test_get_device(hub, mock_protocol):
    """Device retrieval by ID."""
    hub.add_device(mock_protocol, Switchable, device_id="get_test")
    
    device = hub.get("get_test")
    assert device is not None
    assert device.category == "switchable"


def test_get_missing_device(hub):
    """Missing device raises DeviceError."""
    with pytest.raises(DeviceError) as exc:
        hub.get("missing")
    
    assert "missing" in str(exc.value)


def test_dict_access(hub, mock_protocol):
    """Dictionary-style access works."""
    hub.add_device(mock_protocol, Switchable, device_id="dict_test")
    
    # __getitem__
    device = hub["dict_test"]
    assert device.category == "switchable"
    
    # __contains__
    assert "dict_test" in hub
    assert "not_there" not in hub


def test_list_devices(hub, mock_protocol):
    """List devices with filtering."""
    hub.add_device(mock_protocol, Switchable, device_id="switch1")
    hub.add_device(mock_protocol, Sensor, device_id="sensor1")
    
    all_devices = hub.list_devices()
    assert len(all_devices) == 2
    assert "switch1" in all_devices
    assert "sensor1" in all_devices
    
    switches = hub.list_devices(category="switchable")
    assert len(switches) == 1
    assert "switch1" in switches


def test_find_devices(hub, mock_protocol):
    """Find devices by criteria."""
    hub.add_device(mock_protocol, Switchable, device_id="find_switch")
    hub.add_device(mock_protocol, Sensor, device_id="find_sensor")
    
    switches = hub.find(category="switchable")
    assert len(switches) == 1
    
    all_devs = hub.find()
    assert len(all_devs) == 2


def test_remove_device(hub, mock_protocol):
    """Device removal."""
    hub.add_device(mock_protocol, Switchable, device_id="removable")
    
    assert hub.remove("removable") is True
    assert len(hub) == 0
    assert "removable" not in hub
    
    # Second remove returns False
    assert hub.remove("removable") is False


def test_clear_hub(hub, mock_protocol):
    """Clear all devices."""
    hub.add_device(mock_protocol, Switchable, device_id="d1")
    hub.add_device(mock_protocol, Switchable, device_id="d2")
    
    assert len(hub) == 2
    
    hub.clear()
    
    assert len(hub) == 0
    assert "d1" not in hub
    assert "d2" not in hub


def test_hub_stats(hub, mock_protocol):
    """Statistics tracking."""
    stats = hub.stats()
    assert stats["version"] is not None
    assert stats["devices_active"] == 0
    
    hub.add_device(mock_protocol, Switchable, device_id="s1")
    hub.add_device(mock_protocol, Switchable, device_id="s2")
    hub.remove("s1")
    
    stats = hub.stats()
    assert stats["devices_active"] == 1
    assert stats["devices_registered_total"] == 2
    assert stats["devices_removed_total"] == 1


def test_hub_iteration(hub, mock_protocol):
    """Iteration over device IDs."""
    hub.add_device(mock_protocol, Switchable, device_id="iter1")
    hub.add_device(mock_protocol, Switchable, device_id="iter2")
    
    ids = list(hub)
    assert "iter1" in ids
    assert "iter2" in ids


def test_hub_repr(hub):
    """String representation."""
    assert "Hub" in repr(hub)
    assert "devices=0" in repr(hub)