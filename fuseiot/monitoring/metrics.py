import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from ..logging_config import get_logger

logger = get_logger("monitoring.metrics")


@dataclass
class MetricValue:
    """Single metric value."""
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    """In-memory metrics collector."""
    
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, MetricValue] = {}
        self._histograms: Dict[str, list] = defaultdict(list)
        self._timers: Dict[str, list] = defaultdict(list)
    
    def increment(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter."""
        key = self._key(name, labels)
        self._counters[key] += value
    
    def gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge value."""
        key = self._key(name, labels)
        self._gauges[key] = MetricValue(value, time.time(), labels or {})
    
    def histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record histogram value."""
        key = self._key(name, labels)
        self._histograms[key].append(value)
    
    def timer(self, name: str, duration_ms: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Record timer value."""
        key = self._key(name, labels)
        self._timers[key].append(duration_ms)
    
    def _key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Create metric key from name and labels."""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all metrics."""
        return {
            "counters": dict(self._counters),
            "gauges": {k: v.value for k, v in self._gauges.items()},
            "histograms": {
                k: {"count": len(v), "sum": sum(v), "avg": sum(v)/len(v) if v else 0}
                for k, v in self._histograms.items()
            },
            "timers": {
                k: {
                    "count": len(v),
                    "avg_ms": sum(v)/len(v) if v else 0,
                    "min_ms": min(v) if v else 0,
                    "max_ms": max(v) if v else 0
                }
                for k, v in self._timers.items()
            }
        }


class PrometheusMetrics(MetricsCollector):
    """Prometheus-compatible metrics exporter."""
    
    def __init__(self, port: int = 9090):
        super().__init__()
        self.port = port
        self._server = None
    
    def start_server(self) -> None:
        """Start Prometheus HTTP server."""
        try:
            from prometheus_client import start_http_server, Counter, Gauge, Histogram
            
            start_http_server(self.port)
            logger.info("prometheus_server_started", port=self.port)
            
        except ImportError:
            logger.error("prometheus_client_not_installed")
            raise
    
    def export(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        
        # Counters
        for key, value in self._counters.items():
            name, labels = self._parse_key(key)
            lines.append(f"# TYPE {name} counter")
            if labels:
                lines.append(f'{name}{{{labels}}} {value}')
            else:
                lines.append(f'{name} {value}')
        
        # Gauges
        for key, metric in self._gauges.items():
            name, labels = self._parse_key(key)
            lines.append(f"# TYPE {name} gauge")
            label_str = labels if labels else ""
            if metric.labels:
                extra = ",".join(f'{k}="{v}"' for k, v in metric.labels.items())
                label_str = f"{label_str},{extra}" if label_str else extra
            if label_str:
                lines.append(f'{name}{{{label_str}}} {metric.value}')
            else:
                lines.append(f'{name} {metric.value}')
        
        return "\n".join(lines)
    
    def _parse_key(self, key: str) -> tuple:
        """Parse metric key into name and labels."""
        if "{" in key:
            name, labels_part = key.split("{", 1)
            labels = labels_part.rstrip("}")
            return name, labels
        return key, ""