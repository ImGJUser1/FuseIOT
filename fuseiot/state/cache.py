import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class CacheEntry:
    """Single cached value with metadata."""
    
    value: Any
    timestamp: float
    ttl_seconds: float
    source: str  # "poll", "command", "event"
    
    @property
    def is_valid(self) -> bool:
        """Check if entry hasn't expired."""
        return (time.monotonic() - self.timestamp) < self.ttl_seconds
    
    @property
    def age_seconds(self) -> float:
        """How old is this entry."""
        return time.monotonic() - self.timestamp


class StateCache:
    """
    Thread-safe TTL cache for device state.
    
    Not a distributed cache. Local to Hub instance.
    Provides deterministic freshness guarantees.
    """
    
    def __init__(self, default_ttl: float = 5.0):
        self._default_ttl = default_ttl
        self._data: Dict[str, CacheEntry] = {}
        self._lock = Lock()
    
    def get(
        self,
        key: str,
        max_age: Optional[float] = None
    ) -> Optional[Any]:
        """
        Retrieve value if fresh enough.
        
        Args:
            key: Device identifier
            max_age: Maximum acceptable age (None = use TTL)
            
        Returns:
            Cached value or None if stale/missing
        """
        with self._lock:
            entry = self._data.get(key)
            
            if entry is None:
                return None
            
            age_limit = max_age or entry.ttl_seconds
            
            if entry.age_seconds > age_limit:
                return None
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        source: str = "poll"
    ) -> None:
        """
        Store value with freshness tracking.
        
        Args:
            key: Device identifier
            value: State data (must be immutable or copy)
            ttl: Time-to-live (None = use default)
            source: How this state was obtained
        """
        entry = CacheEntry(
            value=value,
            timestamp=time.monotonic(),
            ttl_seconds=ttl or self._default_ttl,
            source=source
        )
        
        with self._lock:
            self._data[key] = entry
    
    def invalidate(self, key: str) -> bool:
        """Remove key from cache. Returns True if existed."""
        with self._lock:
            existed = key in self._data
            self._data.pop(key, None)
            return existed
    
    def invalidate_all(self) -> None:
        """Clear entire cache."""
        with self._lock:
            self._data.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        with self._lock:
            total = len(self._data)
            valid = sum(1 for e in self._data.values() if e.is_valid)
            return {
                "total_entries": total,
                "valid_entries": valid,
                "stale_entries": total - valid,
            }