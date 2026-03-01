import time
import asyncio
from typing import Dict, Any, Optional, List, Type, Union, Iterator, Callable, Tuple
from threading import Lock, RLock
from dataclasses import dataclass, field

from fuseiot.protocols.base import Protocol, AsyncProtocol
from fuseiot.capabilities.base import Capability, CapabilityConfig, AsyncCapability
from fuseiot.state.cache import StateCache
from fuseiot.state.persistence import PersistenceBackend, SQLiteBackend
from fuseiot.state.events import EventBus, StateChangeEvent
from fuseiot.result import CommandResult, CommandStatus, BatchResult
from fuseiot.exceptions import ConfigurationError, DeviceError, TimeoutError
from fuseiot.logging_config import get_logger
from fuseiot.__version__ import __version__
from fuseiot.config import Config

logger = get_logger("hub")


@dataclass
class HubConfig:
    """Hub configuration."""
    default_ttl: float = 5.0
    max_devices: int = 1000
    persistence: Optional[PersistenceBackend] = None
    enable_events: bool = True
    metrics_enabled: bool = False


class Hub:
    """
    Central registry for device capabilities.
    
    Enhanced features:
    - Async/await support
    - Event bus for state changes
    - Persistence backend
    - Batch operations
    - Metrics collection
    - Auto-discovery integration
    """
    
    def __init__(
        self,
        config: Optional[Union[HubConfig, Config]] = None,
        default_ttl: float = None
    ):
        if config is None:
            config = HubConfig(default_ttl=default_ttl or 5.0)
        elif isinstance(config, Config):
            config = HubConfig(
                default_ttl=config.default_ttl,
                persistence=SQLiteBackend(config.persistence_path) if config.persistence_enabled else None,
                enable_events=True,
                metrics_enabled=config.metrics_enabled
            )
        
        self._config = config
        self._devices: Dict[str, Capability] = {}
        self._cache = StateCache(
            default_ttl=config.default_ttl,
            persistence=config.persistence
        )
        self._event_bus = EventBus() if config.enable_events else None
        self._metadata = {
            "version": __version__,
            "created_at": time.time(),
            "devices_registered": 0,
            "devices_removed": 0,
        }
        self._lock = RLock()
        self._metrics = {
            "commands_total": 0,
            "commands_success": 0,
            "commands_failed": 0,
        }
        
        logger.info("hub_initialized", 
                   version=__version__,
                   persistence_enabled=config.persistence is not None,
                   events_enabled=config.enable_events)
    
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
        """
        # Verify protocol connection
        if not protocol.is_connected:
            if not protocol.connect():
                raise ConfigurationError(
                    f"Cannot connect to protocol: {protocol.endpoint}. "
                    "Check network and device availability."
                )
        
        # Inject event bus if capability supports it
        if self._event_bus and "event_bus" not in capability_kwargs:
            capability_kwargs["event_bus"] = self._event_bus
        
        # Create capability instance
        try:
            capability = capability_class(
                protocol=protocol,
                cache=self._cache,
                config=config,
                **capability_kwargs
            )
        except Exception as e:
            logger.error("capability_creation_failed", error=str(e))
            raise ConfigurationError(
                f"Failed to create capability {capability_class.__name__}: {e}"
            )
        
        # Determine device ID
        final_id = device_id or capability.id
        
        with self._lock:
            if len(self._devices) >= self._config.max_devices:
                raise ConfigurationError(f"Max devices reached: {self._config.max_devices}")
            
            if final_id in self._devices:
                raise ConfigurationError(
                    f"Device ID already exists: {final_id}. "
                    "Use unique identifiers or remove existing device first."
                )
            
            self._devices[final_id] = capability
            self._metadata["devices_registered"] += 1
        
        logger.info("device_registered", 
                   device_id=final_id,
                   category=capability.category,
                   protocol=protocol.name)
        
        return capability
    
    def get(self, device_id: str) -> Capability:
        """Retrieve device capability by ID."""
        with self._lock:
            if device_id not in self._devices:
                raise DeviceError(f"Device not found: {device_id}")
            return self._devices[device_id]
    
    def find(self, **criteria) -> List[Capability]:
        """Find devices matching criteria."""
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
        """List registered device IDs."""
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
        """Unregister a device."""
        with self._lock:
            if device_id in self._devices:
                device = self._devices[device_id]
                del self._devices[device_id]
                self._metadata["devices_removed"] += 1
                self._cache.invalidate(device_id)
                
                # Disconnect protocol
                try:
                    device.protocol.disconnect()
                except Exception as e:
                    logger.warning("protocol_disconnect_failed", 
                                 device_id=device_id, error=str(e))
                
                logger.info("device_removed", device_id=device_id)
                return True
            return False
    
    def clear(self) -> None:
        """Remove all devices and clear cache."""
        with self._lock:
            for device_id, device in list(self._devices.items()):
                try:
                    device.protocol.disconnect()
                except:
                    pass
            
            self._devices.clear()
            self._cache.invalidate_all()
            self._metadata["devices_removed"] = self._metadata["devices_registered"]
            logger.info("hub_cleared")
    
    async def batch(
        self,
        operations: List[Tuple[Capability, str, Dict[str, Any]]],
        max_concurrent: int = 10,
        continue_on_error: bool = True
    ) -> BatchResult:
        """
        Execute multiple operations concurrently.
        
        Args:
            operations: List of (capability, method_name, kwargs)
            max_concurrent: Max parallel operations
            continue_on_error: Don't stop on first failure
        
        Returns:
            BatchResult with all results
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results: List[CommandResult] = []
        
        async def execute_one(cap, method, kwargs):
            async with semaphore:
                try:
                    if isinstance(cap, AsyncCapability):
                        method_func = getattr(cap, f"{method}_async", None) or getattr(cap, method)
                        return await method_func(**kwargs)
                    else:
                        # Run sync method in thread pool
                        loop = asyncio.get_event_loop()
                        return await loop.run_in_executor(
                            None, 
                            lambda: getattr(cap, method)(**kwargs)
                        )
                except Exception as e:
                    return CommandResult(
                        success=False,
                        confirmed=False,
                        status=CommandStatus.FAILED,
                        device_id=cap.id,
                        command=method,
                        error=str(e)
                    )
        
        start = time.time()
        tasks = [execute_one(cap, method, kwargs) for cap, method, kwargs in operations]
        
        if continue_on_error:
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            for result in completed:
                if isinstance(result, Exception):
                    results.append(CommandResult(
                        success=False,
                        confirmed=False,
                        status=CommandStatus.FAILED,
                        error=str(result)
                    ))
                else:
                    results.append(result)
        else:
            # Stop on first failure
            for task in asyncio.as_completed(tasks):
                result = await task
                results.append(result)
                if not result.success:
                    break
        
        total_latency = (time.time() - start) * 1000
        
        successful = sum(1 for r in results if r.success)
        confirmed = sum(1 for r in results if r.confirmed)
        
        return BatchResult(
            results=results,
            total=len(operations),
            successful=successful,
            failed=len(results) - successful,
            confirmed=confirmed,
            total_latency_ms=total_latency
        )
    
    def on_state_change(
        self,
        callback: Callable[[StateChangeEvent], None],
        device_id: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> Callable:
        """
        Subscribe to state changes.
        
        Returns unsubscribe function.
        """
        if not self._event_bus:
            raise ConfigurationError("Event bus not enabled")
        
        if device_id:
            return self._event_bus.subscribe(device_id, callback)
        elif pattern:
            return self._event_bus.subscribe_pattern(pattern, callback)
        else:
            return self._event_bus.subscribe_all(callback)
    
    def stats(self) -> Dict[str, Any]:
        """Get Hub runtime statistics."""
        with self._lock:
            uptime = time.time() - self._metadata["created_at"]
            
            return {
                "version": self._metadata["version"],
                "devices_active": len(self._devices),
                "devices_registered_total": self._metadata["devices_registered"],
                "devices_removed_total": self._metadata["devices_removed"],
                "cache_stats": self._cache.stats(),
                "event_stats": self._event_bus.stats() if self._event_bus else None,
                "uptime_seconds": round(uptime, 2),
                "metrics": self._metrics if self._config.metrics_enabled else None,
            }
    
    def __getitem__(self, device_id: str) -> Capability:
        return self.get(device_id)
    
    def __contains__(self, device_id: str) -> bool:
        with self._lock:
            return device_id in self._devices
    
    def __len__(self) -> int:
        with self._lock:
            return len(self._devices)
    
    def __iter__(self) -> Iterator[str]:
        with self._lock:
            return iter(list(self._devices.keys()))
    
    def __repr__(self) -> str:
        return f"<Hub devices={len(self)} version={self._metadata['version']}>"
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        """Async context manager exit."""
        self.clear()