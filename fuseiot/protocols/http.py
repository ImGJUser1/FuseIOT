import asyncio
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    import aiohttp
    import aiohttp.client_exceptions
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from .base import AsyncProtocol, ProtocolConfig, ConnectionState
from ..exceptions import ProtocolError, AuthenticationError
from ..logging_config import get_logger
from ..utils.retry import async_retry, AsyncRetryConfig

logger = get_logger("protocols.http")


@dataclass
class HTTPConfig(ProtocolConfig):
    """HTTP-specific configuration."""
    base_url: str = ""
    auth: Optional[Tuple[str, str]] = None
    bearer_token: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    verify_ssl: bool = True
    client_cert: Optional[Tuple[str, str]] = None
    connection_pool_size: int = 100
    keepalive_timeout: float = 30.0


class HTTP(AsyncProtocol):
    """
    Native async HTTP/REST protocol.
    
    Uses aiohttp for high-performance async operations.
    Falls back to requests for sync operations.
    """
    
    def __init__(
        self,
        base_url: str,
        auth: Optional[Tuple[str, str]] = None,
        bearer_token: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 5.0,
        verify_ssl: bool = True,
        client_cert: Optional[Tuple[str, str]] = None,
        config: Optional[HTTPConfig] = None
    ):
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp required: pip install aiohttp")
        
        super().__init__(config or HTTPConfig())
        self.base_url = base_url.rstrip("/")
        self.auth = auth
        self.bearer_token = bearer_token
        self.headers = headers or {}
        self.verify_ssl = verify_ssl
        self.client_cert = client_cert
        
        self._session: Optional[aiohttp.ClientSession] = None
        self._sync_session = None  # For sync fallback
    
    @property
    def endpoint(self) -> str:
        return f"http:{self.base_url}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Build request headers."""
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            **self.headers
        }
        if self.bearer_token:
            h["Authorization"] = f"Bearer {self.bearer_token}"
        return h
    
    async def connect_async(self) -> bool:
        """Async connection with aiohttp."""
        try:
            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=self._get_headers(),
            )
            
            # Test connection with HEAD request
            async with self._session.head(
                self.base_url,
                ssl=None if not self.verify_ssl else True,
            ) as response:
                if response.status < 500:
                    self._update_state(ConnectionState.CONNECTED)
                    return True
                else:
                    self._update_state(ConnectionState.FAILED, f"HTTP {response.status}")
                    return False
                    
        except aiohttp.ClientError as e:
            self._update_state(ConnectionState.FAILED, str(e))
            return False
    
    def connect(self) -> bool:
        """Sync connection (for compatibility)."""
        try:
            import requests
            self._sync_session = requests.Session()
            self._sync_session.headers.update(self._get_headers())
            if self.auth:
                self._sync_session.auth = self.auth
            
            response = self._sync_session.head(
                self.base_url,
                timeout=self.config.timeout,
                verify=self.verify_ssl,
                cert=self.client_cert
            )
            
            if response.ok:
                self._update_state(ConnectionState.CONNECTED)
                return True
            return False
            
        except Exception as e:
            self._update_state(ConnectionState.FAILED, str(e))
            return False
    
    def disconnect(self) -> None:
        """Sync disconnect."""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None
        self._update_state(ConnectionState.DISCONNECTED)
    
    async def disconnect_async(self) -> None:
        """Async disconnect."""
        if self._session:
            await self._session.close()
            self._session = None
        self._update_state(ConnectionState.DISCONNECTED)
    
    @async_retry(AsyncRetryConfig(max_attempts=3, base_delay=0.1))
    async def send_async(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Native async send."""
        if not self._session:
            raise ProtocolError("Not connected", "http", self.base_url)
        
        method = payload.get("_method", "POST").upper()
        path = payload.get("_path", "/")
        body = {k: v for k, v in payload.items() if not k.startswith("_")}
        
        url = f"{self.base_url}{path}"
        
        import time
        start = time.monotonic()
        
        try:
            ssl_ctx = None if not self.verify_ssl else True
            
            if method == "GET":
                async with self._session.get(
                    url,
                    params=body if body else None,
                    ssl=ssl_ctx
                ) as response:
                    data = await response.json() if response.content_type == "application/json" else {}
                    
            elif method == "POST":
                async with self._session.post(
                    url,
                    json=body,
                    ssl=ssl_ctx
                ) as response:
                    data = await response.json() if response.content_type == "application/json" else {}
                    
            elif method == "PUT":
                async with self._session.put(
                    url,
                    json=body,
                    ssl=ssl_ctx
                ) as response:
                    data = await response.json() if response.content_type == "application/json" else {}
                    
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Update metrics
            latency_ms = (time.monotonic() - start) * 1000
            self._metrics["messages_sent"] += 1
            self._metrics["messages_received"] += 1
            self._metrics["latency_ms_total"] += latency_ms
            
            if response.status >= 400:
                if response.status == 401:
                    raise AuthenticationError(f"Authentication failed: {data}")
                raise ProtocolError(
                    f"HTTP {response.status}: {data}",
                    "http",
                    url
                )
            
            return data
            
        except aiohttp.ClientError as e:
            self._metrics["errors"] += 1
            raise ProtocolError(f"HTTP request failed: {e}", "http", url, e)
    
    def send(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Sync send using requests."""
        if not self._sync_session:
            raise ProtocolError("Not connected", "http", self.base_url)
        
        method = payload.get("_method", "POST").upper()
        path = payload.get("_path", "/")
        body = {k: v for k, v in payload.items() if not k.startswith("_")}
        
        url = f"{self.base_url}{path}"
        
        try:
            if method == "GET":
                response = self._sync_session.get(
                    url,
                    params=body if body else None,
                    timeout=self.config.timeout,
                    verify=self.verify_ssl,
                    cert=self.client_cert
                )
            elif method == "POST":
                response = self._sync_session.post(
                    url,
                    json=body,
                    timeout=self.config.timeout,
                    verify=self.verify_ssl,
                    cert=self.client_cert
                )
            elif method == "PUT":
                response = self._sync_session.put(
                    url,
                    json=body,
                    timeout=self.config.timeout,
                    verify=self.verify_ssl,
                    cert=self.client_cert
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except Exception as e:
            self._metrics["errors"] += 1
            raise ProtocolError(f"HTTP request failed: {e}", "http", url, e)