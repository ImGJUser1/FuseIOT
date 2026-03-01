import ssl
from typing import Any, Dict, Optional
import paho.mqtt.client as mqtt
from .mqtt import MQTT  # Assuming MQTT is the base without TLS
from ..exceptions import ConnectionError

class MQTTS(MQTT):
    """MQTT protocol with TLS support."""

    def __init__(self, broker: str, port: int = 8883, client_id: Optional[str] = None,
                 ca_certs: Optional[str] = None, certfile: Optional[str] = None,
                 keyfile: Optional[str] = None):
        super().__init__(broker, port, client_id)
        self._ca_certs = ca_certs
        self._certfile = certfile
        self._keyfile = keyfile

    def connect(self) -> None:
        """Connect with TLS."""
        if not all([self._ca_certs, self._certfile, self._keyfile]):
            raise ConnectionError("TLS certificates required for MQTTS")
        self._client.tls_set(ca_certs=self._ca_certs, certfile=self._certfile, keyfile=self._keyfile,
                             cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        super().connect()

    async def send_command(self, command: str, payload: Optional[Dict[str, Any]] = None) -> Result:
        """Send command over MQTTS (inherits from MQTT)."""
        return await super().send_command(command, payload)