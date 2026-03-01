from typing import Dict, Any, Optional
from enum import Enum

from .base import Capability, CapabilityConfig
from ..result import CommandResult
from ..logging_config import get_logger

logger = get_logger("capabilities.lock")


class LockState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    JAMMED = "jammed"
    UNKNOWN = "unknown"


class Lock(Capability):
    """
    Smart lock control.
    
    Commands: lock, unlock
    State: lock_state, battery_level, last_user
    """
    
    def __init__(
        self,
        protocol,
        cache,
        config=None,
        auto_lock_delay: Optional[int] = None,
        event_bus=None,
        **kwargs
    ):
        super().__init__(protocol, cache, config, event_bus=event_bus, **kwargs)
        self.auto_lock_delay = auto_lock_delay
    
    @property
    def category(self) -> str:
        return "lock"
    
    def read_state(self) -> Dict[str, Any]:
        """Read lock state."""
        cached = self.cache.get(self.id)
        if cached is not None:
            return cached
        
        try:
            response = self.protocol.send({"_method": "GET", "_path": "/status"})
            state = {
                "lock_state": response.get("lock_state", "unknown"),
                "battery_level": response.get("battery_level", 100),
                "last_user": response.get("last_user"),
                "door_open": response.get("door_open", False)
            }
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state = {
                "lock_state": "unknown",
                "battery_level": 0,
                "door_open": False
            }
        
        self.cache.set(self.id, state, source="poll")
        return state
    
    def lock(self, confirm: Optional[bool] = None, timeout: Optional[float] = None) -> CommandResult:
        """Lock the device."""
        return self._send_and_confirm(
            command_payload={"_method": "POST", "_path": "/lock", "action": "lock"},
            expected_state={"lock_state": "locked"},
            timeout=timeout,
            command_name="lock"
        )
    
    def unlock(
        self,
        user_code: Optional[str] = None,
        confirm: Optional[bool] = None,
        timeout: Optional[float] = None
    ) -> CommandResult:
        """Unlock the device."""
        payload = {"_method": "POST", "_path": "/lock", "action": "unlock"}
        if user_code:
            payload["user_code"] = user_code
        
        return self._send_and_confirm(
            command_payload=payload,
            expected_state={"lock_state": "unlocked"},
            timeout=timeout,
            command_name="unlock"
        )
    
    @property
    def is_locked(self) -> bool:
        """Lock status."""
        return self.read_state().get("lock_state") == "locked"
    
    @property
    def battery_level(self) -> int:
        """Battery percentage."""
        return self.read_state().get("battery_level", 0)