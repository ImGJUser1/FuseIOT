from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..protocols.base import Protocol
    from ..state.cache import StateCache


@dataclass
class CapabilityConfig:
    """Common capability configuration."""
    
    name: Optional[str] = None
    timeout: float = 2.0
    confirm: bool = True


class Capability(ABC):
    """
    Abstract base for device capabilities.
    
    Responsibilities:
    - Define command vocabulary
    - Implement command semantics
    - Manage state interpretation
    - Handle confirmation logic
    
    NOT responsibilities:
    - Transport (delegated to protocol)
    - Caching (delegated to cache)
    - Retry (handled by protocol or caller)
    """
    
    def __init__(
        self,
        protocol: "Protocol",
        cache: "StateCache",
        config: Optional[CapabilityConfig] = None
    ):
        self.protocol = protocol
        self.cache = cache
        self.config = config or CapabilityConfig()
        self._capability_id = f"{self.__class__.__name__}_{id(self)}"
    
    @property
    def id(self) -> str:
        """Unique capability instance identifier."""
        return self._capability_id
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Capability type identifier."""
        raise NotImplementedError
    
    @abstractmethod
    def read_state(self) -> Dict[str, Any]:
        """Poll current state from device."""
        raise NotImplementedError
    
    def _send_and_confirm(
        self,
        command_payload: Dict[str, Any],
        expected_state: Dict[str, Any],
        timeout: Optional[float] = None
    ):
        """
        Send command and verify state change.
        
        Returns CommandResult with confirmation status.
        """
        from ..result import CommandResult, CommandStatus
        from ..state.confirm import confirm_state
        import time
        
        start = time.monotonic()
        timeout_val = timeout or self.config.timeout
        
        # Get pre-state
        try:
            state_before = self.read_state()
        except Exception:
            state_before = None
        
        # Send command
        try:
            raw_response = self.protocol.send(command_payload)
            status = CommandStatus.ACKNOWLEDGED
        except Exception as e:
            return CommandResult(
                success=False,
                confirmed=False,
                status=CommandStatus.FAILED,
                state_before=state_before,
                error=str(e)
            )
        
        # Confirm if requested
        if self.config.confirm:
            confirmed, state_after, confirm_ms = confirm_state(
                self.protocol,
                expected_state,
                timeout=timeout_val - (time.monotonic() - start)
            )
            
            elapsed = (time.monotonic() - start) * 1000
            
            return CommandResult(
                success=confirmed,
                confirmed=confirmed,
                status=CommandStatus.CONFIRMED if confirmed else CommandStatus.TIMEOUT,
                state_before=state_before,
                state_after=state_after,
                latency_ms=elapsed,
                raw_response=raw_response
            )
        else:
            # No confirmation, assume success
            elapsed = (time.monotonic() - start) * 1000
            return CommandResult(
                success=True,
                confirmed=False,
                status=CommandStatus.ACKNOWLEDGED,
                state_before=state_before,
                latency_ms=elapsed,
                raw_response=raw_response
            )