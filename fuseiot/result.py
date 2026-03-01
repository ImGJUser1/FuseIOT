"""
Result types for device commands and batch operations.
This module defines the standard return types used throughout FuseIoT.
"""
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum, auto
import time


class CommandStatus(Enum):
    """
    Lifecycle states of a device command.
    
    PENDING -> SENT -> [ACKNOWLEDGED | FAILED]
    If confirm=True: ACKNOWLEDGED -> CONFIRMED | TIMEOUT
    """
    PENDING = auto()        # Queued, not yet sent
    SENT = auto()           # On wire, no response yet
    ACKNOWLEDGED = auto()   # Device received command
    CONFIRMED = auto()      # Device state matches intent
    FAILED = auto()         # Error during execution
    TIMEOUT = auto()        # No response in time
    CANCELLED = auto()      # Command aborted


@dataclass
class CommandResult:
    """
    Complete result of a device command execution.
    
    This is the primary return type for all capability commands.
    It provides certainty about what happened, not just hope.
    
    Attributes:
        success: True if command achieved intended effect
        confirmed: True if device state was verified to match
        status: Detailed lifecycle status
        state_before: Device state prior to command (if known)
        state_after: Device state after command (if confirmed)
        latency_ms: Total round-trip time including confirmation
        raw_response: Unparsed protocol response for debugging
        error: Human-readable error description if failed
        attempts: Number of transmission attempts made
        timestamp: When result was finalized
        
    Example:
        >>> result = relay.on(confirm=True)
        >>> if result.confirmed:
        ...     print(f"Light on! Took {result.latency_ms}ms")
        ... else:
        ...     print(f"Failed: {result.error}")
    """
    
    success: bool
    confirmed: bool
    status: CommandStatus
    state_before: Optional[Dict[str, Any]] = None
    state_after: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0
    raw_response: Optional[Union[Dict, str, bytes]] = None
    error: Optional[str] = None
    attempts: int = 1
    timestamp: Optional[float] = field(default=None)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
    
    def __bool__(self) -> bool:
        """
        Truthiness based on success.
        
        Allows: if result:  # True only if successful
        """
        return self.success
    
    @property
    def failed(self) -> bool:
        """Convenience: check if command failed."""
        return not self.success
    
    @property
    def state_changed(self) -> Optional[bool]:
        """
        Check if state actually changed.
        
        Returns:
            True if before/after differ
            False if same
            None if unknown (no state data)
        """
        if self.state_before is None or self.state_after is None:
            return None
        return self.state_before != self.state_after
    
    def raise_for_error(self) -> None:
        """
        Raise appropriate exception if command failed.
        
        Raises:
            CommandError: If success is False
            ConfirmationError: If confirmed is False but success is True
        """
        from fuseiot.exceptions import CommandError, ConfirmationError
        
        if not self.success:
            raise CommandError(
                message=self.error or "Command failed",
                device_id="unknown",
                command="unknown",
                result=self
            )
        
        if not self.confirmed and self.status != CommandStatus.ACKNOWLEDGED:
            raise ConfirmationError(
                message="Command not confirmed within timeout",
                device_id="unknown",
                command="unknown",
                result=self
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "confirmed": self.confirmed,
            "status": self.status.name,
            "state_before": self.state_before,
            "state_after": self.state_after,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "attempts": self.attempts,
            "timestamp": self.timestamp,
        }
    
    def __repr__(self) -> str:
        status_str = self.status.name
        if self.success and self.confirmed:
            return f"<CommandResult SUCCESS {status_str} {self.latency_ms:.1f}ms>"
        elif self.success:
            return f"<CommandResult UNCONFIRMED {status_str}>"
        else:
            return f"<CommandResult FAILED {status_str}: {self.error}>"


@dataclass
class BatchResult:
    """
    Result of batch operations.
    """
    results: List[CommandResult]
    total: int
    successful: int
    failed: int
    confirmed: int
    total_latency_ms: float