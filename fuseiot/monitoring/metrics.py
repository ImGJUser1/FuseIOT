from prometheus_client import Counter, Gauge, start_http_server
from ..hub import Hub

class Metrics:
    """Prometheus metrics for observability."""

    def __init__(self, hub: Hub, port: int = 8000):
        self._hub = hub
        self._command_counter = Counter('commands_total', 'Total commands sent', ['device', 'status'])
        self._state_gauge = Gauge('device_state', 'Current device state', ['device'])
        start_http_server(port)

    def log_command(self, device_id: str, success: bool) -> None:
        """Log a command metric."""
        status = 'success' if success else 'failure'
        self._command_counter.labels(device=device_id, status=status).inc()

    def update_state(self, device_id: str, value: float) -> None:
        """Update state gauge."""
        self._state_gauge.labels(device=device_id).set(value)