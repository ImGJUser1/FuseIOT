from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from fuseiot.result import CommandResult


class FuseIoTError(Exception):
    """
    Base for all FuseIoT errors.
    
    All exceptions carry:
    - message: Human-readable description
    - details: Structured context for programmatic handling
    """
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (details: {self.details})"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for logging/API responses."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }


# Device-level errors

class DeviceError(FuseIoTError):
    """
    Base for device-related errors.
    
    Covers: connection, command execution, state reading.
    """
    pass


class ProtocolError(DeviceError):
    """
    Transport layer failure.
    
    Raised when HTTP/MQTT/serial communication fails.
    """
    
    def __init__(
        self,
        message: str,
        protocol: str,
        endpoint: str,
        original_error: Optional[Exception] = None
    ):
        super().__init__(
            message,
            details={
                "protocol": protocol,
                "endpoint": endpoint,
                "original_error": str(original_error) if original_error else None,
            }
        )
        self.protocol = protocol
        self.endpoint = endpoint
        self.original_error = original_error


class CommandError(DeviceError):
    """
    Command execution failed.
    
    Command reached device but failed, or never got confirmation.
    """
    
    def __init__(
        self,
        message: str,
        device_id: str,
        command: str,
        result: Optional["CommandResult"] = None
    ):
        super().__init__(
            message,
            details={
                "device_id": device_id,
                "command": command,
                "result": result.to_dict() if result else None,
            }
        )
        self.device_id = device_id
        self.command = command
        self.result = result


class ConfirmationError(CommandError):
    """
    Command sent but state change not verified.
    
    Special case: device received command but final state doesn't match.
    Could be: device failed, network partition, or external interference.
    """
    pass


class StateError(DeviceError):
    """
    State inconsistent or unreadable.
    
    Device state doesn't make sense, or can't be determined.
    """
    pass


class CacheError(StateError):
    """
    State cache operation failed.
    """
    pass


# Configuration errors

class ConfigurationError(FuseIoTError):
    """
    Setup or configuration mistake.
    
    Wrong parameters, missing dependencies, invalid setup.
    """
    pass


class ValidationError(ConfigurationError):
    """
    Parameter validation failed.
    """
    pass


# Runtime errors

class TimeoutError(FuseIoTError):
    """
    Operation exceeded time limit.
    
    Distinct from CommandError(timeout) - this is system-level.
    """
    
    def __init__(
        self,
        message: str,
        operation: str,
        timeout_seconds: float
    ):
        super().__init__(
            message,
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
            }
        )
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class ConcurrencyError(FuseIoTError):
    """
    Threading/async conflict.
    """
    pass


class ResourceExhaustedError(FuseIoTError):
    """
    Out of memory, file handles, connections, etc.
    """
    pass