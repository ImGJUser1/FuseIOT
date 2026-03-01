from typing import Optional
from dataclasses import dataclass

from .mqtt import MQTT, MQTTConfig
from ..logging_config import get_logger

logger = get_logger("protocols.mqtts")


@dataclass
class MQTTSConfig(MQTTConfig):
    """MQTTS-specific configuration."""
    tls_enabled: bool = True
    ca_certs: Optional[str] = None
    certfile: Optional[str] = None
    keyfile: Optional[str] = None


class MQTTS(MQTT):
    """
    MQTT over TLS/SSL.
    
    Extends MQTT with TLS support.
    """
    
    def __init__(
        self,
        broker: str,
        port: int = 8883,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        **kwargs
    ):
        super().__init__(broker=broker, port=port, **kwargs)
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
    
    @property
    def endpoint(self) -> str:
        return f"mqtts://{self.broker}:{self.port}/{self.topic_prefix}"
    
    def connect(self) -> bool:
        """Connect with TLS."""
        try:
            import ssl
            
            # Configure TLS
            if self.ca_certs:
                self._client.tls_set(
                    ca_certs=self.ca_certs,
                    certfile=self.certfile,
                    keyfile=self.keyfile,
                    tls_version=ssl.PROTOCOL_TLSv1_2
                )
            
            return super().connect()
            
        except Exception as e:
            logger.error("mqtts_tls_error", error=str(e))
            raise