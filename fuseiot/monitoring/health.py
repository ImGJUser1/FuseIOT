import json
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..logging_config import get_logger
from ..hub import Hub

logger = get_logger("monitoring.health")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Health check result."""
    status: HealthStatus
    message: str
    details: Dict[str, Any]


class HealthServer:
    """HTTP health check server."""
    
    def __init__(self, hub: Hub, port: int = 8080):
        self.hub = hub
        self.port = port
        self._server = None
        self._checks: Dict[str, callable] = {}
    
    def add_check(self, name: str, check_func: callable) -> None:
        """Add custom health check."""
        self._checks[name] = check_func
    
    def check(self) -> HealthCheck:
        """Run all health checks."""
        try:
            stats = self.hub.stats()
            
            # Check devices
            if stats["devices_active"] == 0:
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    message="No active devices",
                    details=stats
                )
            
            # Check cache
            cache_stats = stats.get("cache_stats", {})
            if cache_stats.get("stale_entries", 0) > cache_stats.get("valid_entries", 0):
                return HealthCheck(
                    status=HealthStatus.DEGRADED,
                    message="Most cache entries are stale",
                    details=stats
                )
            
            # Run custom checks
            for name, check in self._checks.items():
                result = check()
                if not result:
                    return HealthCheck(
                        status=HealthStatus.UNHEALTHY,
                        message=f"Custom check failed: {name}",
                        details=stats
                    )
            
            return HealthCheck(
                status=HealthStatus.HEALTHY,
                message="All systems operational",
                details=stats
            )
            
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                details={}
            )
    
    def start(self) -> None:
        """Start health check HTTP server."""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            hub = self.hub  # Capture for handler
            
            class Handler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == "/health":
                        health = hub.stats()  # Simplified
                        status = 200 if health["devices_active"] > 0 else 503
                        
                        self.send_response(status)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        
                        response = json.dumps({
                            "status": "healthy" if status == 200 else "unhealthy",
                            "hub": health
                        }).encode()
                        self.wfile.write(response)
                    
                    elif self.path == "/ready":
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(b"OK")
                    
                    else:
                        self.send_response(404)
                        self.end_headers()
                
                def log_message(self, format, *args):
                    logger.debug("health_request", message=args[0])
            
            self._server = HTTPServer(("0.0.0.0", self.port), Handler)
            logger.info("health_server_started", port=self.port)
            
            import threading
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            
        except Exception as e:
            logger.error("health_server_failed", error=str(e))
            raise
    
    def stop(self) -> None:
        """Stop health server."""
        if self._server:
            self._server.shutdown()
            logger.info("health_server_stopped")