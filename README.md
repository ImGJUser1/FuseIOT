# FuseIoT

**Deterministic device control SDK for Python.**

Control relays, sensors, and motors with guaranteed command confirmation and state consistency. No platform lock-in. No cloud required. Just reliable hardware control.

```python
from fuseiot import Hub, HTTP, Switchable

hub = Hub()
relay = hub.add_device(HTTP("http://192.168.1.45"), Switchable)

relay.on(confirm=True)  # True only if device confirms