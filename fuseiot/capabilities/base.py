from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING, Union
from dataclasses import dataclass, field
import time

if TYPE_CHECKING:
    from ..protocols.base import Protocol, AsyncProtocol
    from ..state.cache import StateCache
    from ..result import CommandResult

from ..logging_config import get_logger
from ..result import CommandResult, CommandStatus
from ..state.confirm import confirm_state
from ..exceptions import CommandError, CircuitOpenError, RateLimitError
from ..utils.circuit_breaker import CircuitBreaker
from ..utils.rate_limiter import RateLimiter

logger = get_logger("capabilities.base")


@dataclass
class CapabilityConfig:
    """Common capability configuration."""
    
    name: Optional[str] = None
    timeout: float = 2.0
    confirm: bool = True
    retry_attempts: int = 3
    circuit_breaker: Optional[CircuitBreaker] = None
    rate_limiter: Optional[RateLimiter] = None
    metrics_enabled: bool = False


class Capability(ABC):
    """
    Abstract base for device capabilities.
    
    Enhanced with:
    - Circuit breaker support
    - Rate limiting
    - Metrics collection
    - Event emission
    """
    
    def __init__(
        self,
        protocol: "Protocol",
        cache: "StateCache",
        config: Optional[CapabilityConfig] = None,
        event_bus: Optional[Any] = None,
        **kwargs
    ):
        self.protocol = protocol
        self.cache = cache
        self.config = config or CapabilityConfig()
        self.event_bus = event_bus
        self._capability_id = f"{self.__class__.__name__}_{id(self)}"
        self._metrics: Dict[str, Any] = {
            "commands_total": 0,
            "commands_success": 0,
            "commands_failed": 0,
            "confirmation_failures": 0,
            "avg_latency_ms": 0.0,
        }
        
        # Apply resilience wrappers if configured
        if self.config.circuit_breaker:
            self._send_and_confirm = self.config.circuit_breaker(self._send_and_confirm)
    
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
    
    async def read_state_async(self) -> Dict[str, Any]:
        """Async state read."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.read_state)
    
    def _emit_event(self, old_state: Optional[Dict], new_state: Dict, source: str = "command") -> None:
        """Emit state change event."""
        if self.event_bus:
            from ..state.events import StateChangeEvent
            event = StateChangeEvent(
                device_id=self.id,
                timestamp=time.time(),
                old_state=old_state,
                new_state=new_state,
                source=source
            )
            self.event_bus.emit(event)
    
    def _update_metrics(self, result: CommandResult) -> None:
        """Update internal metrics."""
        if not self.config.metrics_enabled:
            return
        
        self._metrics["commands_total"] += 1
        
        if result.success:
            self._metrics["commands_success"] += 1
        else:
            self._metrics["commands_failed"] += 1
            if not result.confirmed:
                self._metrics["confirmation_failures"] += 1
        
        # Update average latency
        total = self._metrics["commands_total"]
        current_avg = self._metrics["avg_latency_ms"]
        self._metrics["avg_latency_ms"] = (
            (current_avg * (total - 1) + result.latency_ms) / total
        )
    
    def _send_and_confirm(
        self,
        command_payload: Dict[str, Any],
        expected_state: Dict[str, Any],
        timeout: Optional[float] = None,
        command_name: Optional[str] = None
    ) -> CommandResult:
        """
        Send command and verify state change.
        
        Returns CommandResult with full lifecycle tracking.
        """
        start = time.monotonic()
        timeout_val = timeout or self.config.timeout
        
        # Check rate limit
        if self.config.rate_limiter and not self.config.rate_limiter.allow():
            raise RateLimitError(
                limit=self.config.rate_limiter.rate,
                window_seconds=self.config.rate_limiter.window,
                retry_after=self.config.rate_limiter.time_until_next()
            )
        
        # Get pre-state
        try:
            state_before = self.read_state()
        except Exception as e:
            logger.warning("read_state_failed", device=self.id, error=str(e))
            state_before = None
        
        # Send command
        try:
            raw_response = self.protocol.send(command_payload)
            status = CommandStatus.ACKNOWLEDGED
        except CircuitOpenError:
            raise
        except Exception as e:
            result = CommandResult(
                success=False,
                confirmed=False,
                status=CommandStatus.FAILED,
                device_id=self.id,
                command=command_name,
                state_before=state_before,
                error=str(e),
                latency_ms=(time.monotonic() - start) * 1000
            )
            self._update_metrics(result)
            return result
        
        # Confirm if requested
        if self.config.confirm:
            confirm_timeout = timeout_val - (time.monotonic() - start)
            if confirm_timeout <= 0:
                result = CommandResult(
                    success=True,
                    confirmed=False,
                    status=CommandStatus.TIMEOUT,
                    device_id=self.id,
                    command=command_name,
                    state_before=state_before,
                    raw_response=raw_response,
                    error="Confirmation timeout (command took too long)",
                    latency_ms=(time.monotonic() - start) * 1000
                )
                self._update_metrics(result)
                return result
            
            confirmed, state_after, confirm_ms = confirm_state(
                self.protocol,
                expected_state,
                timeout=confirm_timeout
            )
            
            elapsed = (time.monotonic() - start) * 1000
            
            result = CommandResult(
                success=confirmed,
                confirmed=confirmed,
                status=CommandStatus.CONFIRMED if confirmed else CommandStatus.TIMEOUT,
                device_id=self.id,
                command=command_name,
                state_before=state_before,
                state_after=state_after,
                latency_ms=elapsed,
                confirmation_latency_ms=confirm_ms,
                raw_response=raw_response
            )
            
            if confirmed:
                self._emit_event(state_before, state_after, "command")
                # Update cache with confirmed state
                self.cache.set(self.id, state_after, source="command")
            
            self._update_metrics(result)
            return result
            
        else:
            # No confirmation, assume success
            elapsed = (time.monotonic() - start) * 1000
            result = CommandResult(
                success=True,
                confirmed=False,
                status=CommandStatus.ACKNOWLEDGED,
                device_id=self.id,
                command=command_name,
                state_before=state_before,
                latency_ms=elapsed,
                raw_response=raw_response
            )
            self._update_metrics(result)
            return result
    
    async def _send_and_confirm_async(
        self,
        command_payload: Dict[str, Any],
        expected_state: Dict[str, Any],
        timeout: Optional[float] = None,
        command_name: Optional[str] = None
    ) -> CommandResult:
        """Async version of send and confirm."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._send_and_confirm,
            command_payload,
            expected_state,
            timeout,
            command_name
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get capability metrics."""
        return self._metrics.copy()


class AsyncCapability(Capability, ABC):
    """Native async capability base."""
    
    async def read_state_async(self) -> Dict[str, Any]:
        """Override for native async implementation."""
        return self.read_state()
    
    @abstractmethod
    async def _send_and_confirm_async(
        self,
        command_payload: Dict[str, Any],
        expected_state: Dict[str, Any],
        timeout: Optional[float] = None,
        command_name: Optional[str] = None
    ) -> CommandResult:
        """Native async implementation required."""
        raise NotImplementedError