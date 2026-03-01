from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum, auto
import time


class CommandStatus(Enum):
    """Lifecycle states of a device command."""
    PENDING = auto()
    SENT = auto()
    ACKNOWLEDGED = auto()
    CONFIRMED = auto()
    FAILED = auto()
    TIMEOUT = auto()
    CANCELLED = auto()
    RATE_LIMITED = auto()
    CIRCUIT_OPEN = auto()
    RETRYING = auto()


@dataclass
class CommandResult:
    """Complete result of a device command execution."""
    
    success: bool
    confirmed: bool
    status: CommandStatus
    device_id: Optional[str] = None
    command: Optional[str] = None
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    network_latency_ms: Optional[float] = None
    confirmation_latency_ms: Optional[float] = None
    raw_response: Optional[Union[Dict, str, bytes]] = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    attempts: int = 1
    retries: int = 0
    timestamp: Optional[float] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def __bool__(self) -> bool:
        """Truthiness based on success."""
        return self.success
    
    @property
    def failed(self) -> bool:
        """Convenience: check if command failed."""
        return not self.success
    
    @property
    def state_changed(self) -> Optional[bool]:
        """Check if state actually changed."""
        if self.state_before is None or self.state_after is None:
            return None
        return self.state_before != self.state_after
    
    def raise_for_error(self) -> None:
        """Raise appropriate exception if command failed."""
        from fuseiot.exceptions import CommandError, ConfirmationError, RateLimitError, CircuitOpenError
        
        if self.status == CommandStatus.RATE_LIMITED:
            raise RateLimitError(
                message=self.error or "Rate limited",
                limit=0, window_seconds=0, retry_after=0
            )
        
        if self.status == CommandStatus.CIRCUIT_OPEN:
            from fuseiot.utils.circuit_breaker import CircuitBreaker
            raise CircuitOpenError(
                device_id=self.device_id or "unknown",
                open_until=time.time() + 30
            )
        
        if not self.success:
            raise CommandError(
                message=self.error or "Command failed",
                device_id=self.device_id or "unknown",
                command=self.command or "unknown",
                result=self
            )
        
        if not self.confirmed and self.status != CommandStatus.ACKNOWLEDGED:
            raise ConfirmationError(
                message="Command not confirmed within timeout",
                device_id=self.device_id or "unknown",
                command=self.command or "unknown",
                result=self
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "confirmed": self.confirmed,
            "status": self.status.name,
            "device_id": self.device_id,
            "command": self.command,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "latency_ms": self.latency_ms,
            "network_latency_ms": self.network_latency_ms,
            "confirmation_latency_ms": self.confirmation_latency_ms,
            "error": self.error,
            "error_code": self.error_code,
            "attempts": self.attempts,
            "retries": self.retries,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    def __repr__(self) -> str:
        status_str = self.status.name
        device = self.device_id or "unknown"
        if self.success and self.confirmed:
            return f"<CommandResult {device} SUCCESS {status_str} {self.latency_ms:.1f}ms>"
        elif self.success:
            return f"<CommandResult {device} UNCONFIRMED {status_str}>"
        else:
            return f"<CommandResult {device} FAILED {status_str}: {self.error}>"


@dataclass
class BatchResult:
    """Results from batch operations."""
    
    results: List[CommandResult]
    total: int
    successful: int
    failed: int
    confirmed: int
    total_latency_ms: float
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = time.time()
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful commands."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100
    
    @property
    def all_succeeded(self) -> bool:
        """Check if all commands succeeded."""
        return self.failed == 0
    
    @property
    def any_failed(self) -> bool:
        """Check if any command failed."""
        return self.failed > 0
    
    def get_failures(self) -> List[CommandResult]:
        """Get only failed results."""
        return [r for r in self.results if not r.success]
    
    def get_by_device(self, device_id: str) -> Optional[CommandResult]:
        """Get result for specific device."""
        for result in self.results:
            if result.device_id == device_id:
                return result
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "confirmed": self.confirmed,
            "success_rate": self.success_rate,
            "total_latency_ms": self.total_latency_ms,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": [r.to_dict() for r in self.results],
        }
    
    def __repr__(self) -> str:
        return f"<BatchResult {self.successful}/{self.total} succeeded ({self.success_rate:.1f}%)>"