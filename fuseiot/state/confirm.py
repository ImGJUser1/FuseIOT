import time
from typing import Dict, Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocols.base import Protocol


class ConfirmationEngine:
    """
    Polls device until state matches expectation or timeout.
    
    Simple, deterministic, no ML.
    """
    
    def __init__(
        self,
        poll_interval: float = 0.1,
        max_attempts: int = 20
    ):
        self.poll_interval = poll_interval
        self.max_attempts = max_attempts
    
    def confirm(
        self,
        protocol: "Protocol",
        expected_state: Dict[str, Any],
        timeout: float = 2.0,
        state_reader: Optional[Callable[[Any], Dict[str, Any]]] = None
    ) -> tuple[bool, Optional[Dict[str, Any]], float]:
        """
        Poll device until state matches or timeout.
        
        Args:
            protocol: Transport to use for polling
            expected_state: Key-value pairs that must match
            timeout: Maximum seconds to wait
            state_reader: Function to extract state from response
            
        Returns:
            (confirmed, actual_state_or_none, elapsed_ms)
        """
        start = time.monotonic()
        deadline = start + timeout
        attempts = 0
        
        while time.monotonic() < deadline and attempts < self.max_attempts:
            attempts += 1
            
            try:
                # Poll current state
                response = protocol.send({"read_state": True})
                
                # Extract state dict
                if state_reader:
                    actual = state_reader(response)
                else:
                    actual = response if isinstance(response, dict) else {}
                
                # Check match
                if all(actual.get(k) == v for k, v in expected_state.items()):
                    elapsed = (time.monotonic() - start) * 1000
                    return True, actual, elapsed
                
                # Wait before retry
                time.sleep(self.poll_interval)
                
            except Exception:
                # Poll failed, retry
                time.sleep(self.poll_interval)
        
        # Timeout
        elapsed = (time.monotonic() - start) * 1000
        return False, None, elapsed


# Module-level convenience function
_default_engine = ConfirmationEngine()


def confirm_state(
    protocol: "Protocol",
    expected: Dict[str, Any],
    timeout: float = 2.0
) -> tuple[bool, Optional[Dict[str, Any]], float]:
    """Convenience: use default engine."""
    return _default_engine.confirm(protocol, expected, timeout)