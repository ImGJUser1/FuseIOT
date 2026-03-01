import time
import socket
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ..logging_config import get_logger

logger = get_logger("discovery.mdns")


@dataclass
class DiscoveryResult:
    """Discovered device information."""
    name: str
    address: str
    port: int
    device_type: str
    protocol: str
    properties: Dict[str, str]
    hostname: Optional[str] = None


class MDNSDiscovery:
    """
    mDNS/Bonjour device discovery.
    
    Discovers IoT devices on local network.
    """
    
    def __init__(self):
        self._zeroconf = None
    
    def scan(
        self,
        service_type: Optional[str] = None,
        timeout: float = 5.0
    ) -> List[DiscoveryResult]:
        """
        Scan for devices.
        
        Args:
            service_type: mDNS service type (e.g., "_http._tcp.local.")
            timeout: Scan duration in seconds
        
        Returns:
            List of discovered devices
        """
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
            
            results = []
            
            class Listener(ServiceListener):
                def add_service(self, zc, type_, name):
                    info = zc.get_service_info(type_, name)
                    if info:
                        result = DiscoveryResult(
                            name=name,
                            address=socket.inet_ntoa(info.addresses[0]) if info.addresses else "",
                            port=info.port,
                            device_type=type_,
                            protocol="http",
                            properties={k.decode(): v.decode() if isinstance(v, bytes) else v 
                                       for k, v in info.properties.items()},
                            hostname=info.server
                        )
                        results.append(result)
                        logger.info("device_discovered", 
                                   name=name, 
                                   address=result.address,
                                   port=info.port)
            
            zc = Zeroconf()
            listener = Listener()
            
            # Common IoT service types
            service_types = [service_type] if service_type else [
                "_http._tcp.local.",
                "_hap._tcp.local.",  # HomeKit
                "_mqtt._tcp.local.",
                "_coap._udp.local.",
            ]
            
            browsers = [ServiceBrowser(zc, st, listener) for st in service_types]
            
            time.sleep(timeout)
            
            for browser in browsers:
                browser.cancel()
            zc.close()
            
            return results
            
        except ImportError:
            logger.warning("zeroconf_not_installed")
            return []
        except Exception as e:
            logger.error("discovery_failed", error=str(e))
            return []
    
    def find_by_name(self, name: str, timeout: float = 5.0) -> Optional[DiscoveryResult]:
        """Find specific device by name."""
        results = self.scan(timeout=timeout)
        for result in results:
            if name.lower() in result.name.lower():
                return result
        return None