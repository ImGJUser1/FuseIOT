
import time
from typing import Dict, Any, Optional, List, Type, Union, Iterator
from threading import Lock

from fuseiot.protocols.base import Protocol
from fuseiot.capabilities.base import Capability, CapabilityConfig
from fuseiot.state.cache import StateCache
from fuseiot.exceptions import ConfigurationError, DeviceError
from fuseiot.__version__ import __version__


class Hub:
    """
    Central registry for device capabilities.
    
    Thread-safe. Designed for single instance per application,
    but multiple instances can coexist for different control domains.
    
    Attributes:
        _devices: Mapping of device_id to Capability instances
        _cache: Shared StateCache for all registered devices
        _metadata: Runtime statistics and version info
        _lock: Thread safety for device registration
    """
    
    def __init__(self, default_ttl: float = 5.0):
        """
        Initialize new Hub instance.
        
        Args:
            default_ttl: Default cache time-to-live in seconds
        """
        self._devices: Dict[str, Capability] = {}
        self._cache = StateCache(default_ttl=default_ttl)
        self._metadata = {
            "version": __version__,
            "created_at": time.time(),
            "devices_registered": 0,
            "devices_removed": 0,
        }
        self._lock = Lock()
    
    def add_device(
        self,
        protocol: Protocol,
        capability_class: Type[Capability],
        device_id: Optional[str] = None,
        config: Optional[CapabilityConfig] = None,
        **capability_kwargs
    ) -> Capability:
        """
        Register a new device capability with the Hub.
        
        This is the primary method for adding controllable devices.
        The protocol must be connected before registration.
        
        Args:
            protocol: Transport protocol instance (HTTP, MQTT, etc.)
            capability_class: Capability type class (Switchable, Sensor, Motor)
            device_id: Optional custom identifier. If None, auto-generated
            config: Optional capability configuration
            **capability_kwargs: Additional capability-specific arguments
                (e.g., unit="celsius", position_range=(0, 360))
        
        Returns:
            Configured and registered Capability instance
            
        Raises:
            ConfigurationError: If protocol not connected or setup fails
            DeviceError: If device_id already exists
        
        Example:
            >>> hub = Hub()
            >>> http = HTTP("http://192.168.1.45")
            >>> relay = hub.add_device(http, Switchable, device_id="light_01")
        """
        # Verify protocol connection
        if not protocol.is_connected:
            if not protocol.connect():
                raise ConfigurationError(
                    f"Cannot connect to protocol: {protocol.endpoint}. "
                    "Check network and device availability."
                )
        
        # Create capability instance
        try:
            capability = capability_class(
                protocol=protocol,
                cache=self._cache,
                config=config,
                **capability_kwargs
            )
        except Exception as e:
            raise ConfigurationError(
                f"Failed to create capability {capability_class.__name__}: {e}"
            )
        
        # Determine device ID
        final_id = device_id or capability.id
        
        with self._lock:
            # Check for duplicates
            if final_id in self._devices:
                raise ConfigurationError(
                    f"Device ID already exists: {final_id}. "
                    "Use unique identifiers or remove existing device first."
                )
            
            # Register
            self._devices[final_id] = capability
            self._metadata["devices_registered"] += 1
        
        return capability
    
    def get(self, device_id: str) -> Capability:
        """
        Retrieve device capability by ID.
        
        Args:
            device_id: Registered device identifier
            
        Returns:
            Capability instance
            
        Raises:
            DeviceError: If device not found
            
        Example:
            >>> relay = hub.get("light_01")
            >>> relay.on()
        """
        with self._lock:
            if device_id not in self._devices:
                raise DeviceError(f"Device not found: {device_id}")
            return self._devices[device_id]
    
    def find(self, **criteria) -> List[Capability]:
        """
        Find devices matching criteria.
        
        Args:
            **criteria: Filter by capability attributes
                - category: str - Capability category name
                - protocol: str - Protocol name
                
        Returns:
            List of matching Capability instances
            
        Example:
            >>> switches = hub.find(category="switchable")
            >>> http_devices = hub.find(protocol="http")
        """
        results = []
        
        with self._lock:
            for device in self._devices.values():
                match = True
                
                if "category" in criteria:
                    if device.category != criteria["category"]:
                        match = False
                
                if "protocol" in criteria:
                    if device.protocol.name != criteria["protocol"]:
                        match = False
                
                if match:
                    results.append(device)
        
        return results
    
    def list_devices(
        self,
        category: Optional[str] = None,
        as_dict: bool = False
    ) -> Union[List[str], Dict[str, str]]:
        """
        List registered device IDs.
        
        Args:
            category: Optional filter by capability category
            as_dict: If True, return {id: category} mapping
            
        Returns:
            List of device IDs, or dict if as_dict=True
            
        Example:
            >>> hub.list_devices()
            ['light_01', 'temp_sensor', 'motor_01']
            >>> hub.list_devices(category="switchable")
            ['light_01']
        """
        with self._lock:
            if category:
                items = [
                    (did, dev.category) 
                    for did, dev in self._devices.items()
                    if dev.category == category
                ]
            else:
                items = [
                    (did, dev.category) 
                    for did, dev in self._devices.items()
                ]
        
        if as_dict:
            return dict(items)
        return [did for did, _ in items]
    
    def remove(self, device_id: str) -> bool:
        """
        Unregister a device.
        
        Args:
            device_id: Device to remove
            
        Returns:
            True if device existed and was removed, False otherwise
            
        Example:
            >>> hub.remove("light_01")
            True
        """
        with self._lock:
            if device_id in self._devices:
                del self._devices[device_id]
                self._metadata["devices_removed"] += 1
                # Invalidate cache entries for this device
                self._cache.invalidate(device_id)
                return True
            return False
    
    def clear(self) -> None:
        """
        Remove all devices and clear cache.
        
        Example:
            >>> hub.clear()  # Clean slate
        """
        with self._lock:
            self._devices.clear()
            self._cache.invalidate_all()
            self._metadata["devices_removed"] = self._metadata["devices_registered"]
    
    def stats(self) -> Dict[str, Any]:
        """
        Get Hub runtime statistics.
        
        Returns:
            Dict with version, device counts, cache stats, uptime
            
        Example:
            >>> hub.stats()
            {
                'version': '0.1.0',
                'devices_active': 3,
                'devices_registered_total': 5,
                'cache_entries': 3,
                'uptime_seconds': 3600
            }
        """
        with self._lock:
            uptime = time.time() - self._metadata["created_at"]
            
            return {
                "version": self._metadata["version"],
                "devices_active": len(self._devices),
                "devices_registered_total": self._metadata["devices_registered"],
                "devices_removed_total": self._metadata["devices_removed"],
                "cache_stats": self._cache.stats(),
                "uptime_seconds": round(uptime, 2),
            }
    
    def __getitem__(self, device_id: str) -> Capability:
        """Dictionary-style access: hub["device_id"]"""
        return self.get(device_id)
    
    def __contains__(self, device_id: str) -> bool:
        """Membership test: "device_id" in hub"""
        with self._lock:
            return device_id in self._devices
    
    def __len__(self) -> int:
        """Number of registered devices: len(hub)"""
        with self._lock:
            return len(self._devices)
    
    def __iter__(self) -> Iterator[str]:
        """Iterate over device IDs: for device_id in hub"""
        with self._lock:
            return iter(list(self._devices.keys()))
    
    def __repr__(self) -> str:
        return f"<Hub devices={len(self)} version={self._metadata['version']}>"