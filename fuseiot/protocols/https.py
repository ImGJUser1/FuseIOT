from typing import Optional, Tuple
from dataclasses import dataclass

from .http import HTTP, HTTPConfig
from ..logging_config import get_logger

logger = get_logger("protocols.https")


@dataclass
class HTTPSConfig(HTTPConfig):
    """HTTPS-specific configuration."""
    verify_ssl: bool = True
    ca_bundle: Optional[str] = None
    client_cert: Optional[Tuple[str, str]] = None
    client_key: Optional[str] = None


class HTTPS(HTTP):
    """
    HTTPS protocol with TLS support.
    
    Extends HTTP with TLS-specific configuration.
    """
    
    def __init__(
        self,
        base_url: str,
        verify_ssl: bool = True,
        ca_bundle: Optional[str] = None,
        client_cert: Optional[Tuple[str, str]] = None,
        client_key: Optional[str] = None,
        **kwargs
    ):
        # Ensure URL uses https
        if not base_url.startswith("https://"):
            base_url = "https://" + base_url.replace("http://", "")
        
        super().__init__(
            base_url=base_url,
            verify_ssl=verify_ssl,
            client_cert=client_cert,
            **kwargs
        )
        self.ca_bundle = ca_bundle
        self.client_key = client_key
    
    @property
    def endpoint(self) -> str:
        return f"https:{self.base_url}"