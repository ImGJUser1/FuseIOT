import requests
import json
from typing import Dict, Any, Optional, Tuple
from .base import Protocol, ProtocolConfig
from ..exceptions import ProtocolError
from ..utils.retry import retry, RetryConfig


class HTTP(Protocol):
    """
    HTTP/REST device communication.
    
    Supports:
    - GET/POST/PUT methods
    - Basic/Digest/Bearer auth
    - JSON payloads
    - Connection pooling
    """
    
    def __init__(
        self,
        base_url: str,
        auth: Optional[Tuple[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 2.0,
        config: Optional[ProtocolConfig] = None
    ):
        super().__init__(config)
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.headers = headers or {}
        self.timeout = timeout
        
        # Session for connection pooling
        self._session = requests.Session()
        if auth:
            self._session.auth = auth
        self._session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.headers
        })
    
    @property
    def endpoint(self) -> str:
        """Human-readable endpoint identifier."""
        return f"http:{self.base_url}"
    
    def connect(self) -> bool:
        """HTTP is stateless; verify with HEAD request."""
        try:
            response = self._session.head(
                self.base_url,
                timeout=self.timeout
            )
            self._connected = response.ok
            return self._connected
        except Exception as e:
            self._connected = False
            self._last_error = str(e)
            return False
    
    def disconnect(self) -> None:
        """Close session."""
        self._session.close()
        self._connected = False
    
    @retry(RetryConfig(max_attempts=3, base_delay=0.1))
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send JSON payload via POST.
        
        Args:
            payload: Must contain 'method' and 'path' or use defaults
            
        Returns:
            Parsed JSON response
        """
        # Extract method/path or use defaults
        method = payload.get("_method", "POST").upper()
        path = payload.get("_path", "/")
        body = {k: v for k, v in payload.items() if not k.startswith("_")}
        
        url = f"{self.base_url}{path}"
        
        try:
            if method == "GET":
                response = self._session.get(
                    url,
                    params=body if body else None,
                    timeout=self.timeout
                )
            elif method == "POST":
                response = self._session.post(
                    url,
                    json=body,
                    timeout=self.timeout
                )
            elif method == "PUT":
                response = self._session.put(
                    url,
                    json=body,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Parse response
            if response.content:
                return response.json()
            return {}
            
        except requests.HTTPError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text}"
            raise ProtocolError(
                message=self._last_error,
                protocol="http",
                endpoint=url,
                original_error=e
            )
        except requests.RequestException as e:
            self._last_error = str(e)
            raise ProtocolError(
                message=f"HTTP request failed: {e}",
                protocol="http",
                endpoint=url,
                original_error=e
            )
        except json.JSONDecodeError as e:
            self._last_error = f"Invalid JSON: {e}"
            raise ProtocolError(
                message=self._last_error,
                protocol="http",
                endpoint=url,
                original_error=e
            )
    
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Async wrapper using thread pool.
        
        For true async, use aiohttp in production.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.send, payload)