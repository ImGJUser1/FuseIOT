# FuseIoT

**Deterministic device control SDK for Python.**  
Control relays, sensors, motors, and smart devices with guaranteed command confirmation and state consistency. No platform lock-in, no cloud required – just reliable hardware control.

---

## Features

- ✅ **Deterministic Control** – Every command confirmed with state verification (optional confirmation polling).
- ✅ **Multiple Protocols** – HTTP/REST, MQTT, MQTTS, WebSocket, Serial (RS232/RS485).
- ✅ **Async Support** – Native asyncio for high‑performance concurrent operations.
- ✅ **Resilience** – Circuit breakers, rate limiting, automatic retries, exponential backoff.
- ✅ **Security** – TLS/SSL, username/password authentication, certificate‑based auth.
- ✅ **Observability** – Structured logging (structlog), Prometheus metrics, health check endpoints.
- ✅ **Persistence** – SQLite/Redis state caching and history.
- ✅ **Event System** – Real‑time state change notifications with in‑memory event bus.
- ✅ **Batch Operations** – Control dozens of devices concurrently with configurable concurrency limits.
- ✅ **Cloud Ready** – Connectors for AWS IoT, Azure IoT, and Google Cloud IoT (optional).
- ✅ **Simulation** – Virtual devices for testing without hardware.

---

## Quick Start

### Installation

```bash
# Minimal install (HTTP only)
pip install fuseiot

# With all features (recommended)
pip install "fuseiot[all]"

# Development install (from source)
git clone https://github.com/fuseiot/fuseiot.git
cd fuseiot
pip install -e ".[all]"
```

### Basic Usage

```python
from fuseiot import Hub, HTTP, Switchable

# Create a hub
hub = Hub()

# Add a smart plug (switchable)
plug = hub.add_device(
    HTTP("http://192.168.1.45/api"),
    Switchable,
    device_id="living_room_light"
)

# Turn on with confirmation
result = plug.on(confirm=True)
if result.confirmed:
    print(f"✓ Light is ON (verified in {result.latency_ms:.1f}ms)")
else:
    print(f"✗ Command failed: {result.error}")

# Check state (cached)
print(f"Current state: {'ON' if plug.is_on else 'OFF'}")

# Turn off
plug.off()
```

### Async Usage

```python
import asyncio
from fuseiot import Hub, HTTP, Switchable

async def control_multiple():
    hub = Hub()
    
    # Add several lights
    lights = []
    for i in range(1, 5):
        light = hub.add_device(
            HTTP(f"http://192.168.1.{40+i}/api"),
            Switchable,
            device_id=f"light_{i:02d}"
        )
        lights.append(light)
    
    # Turn all on concurrently
    results = await asyncio.gather(*[
        light.on_async(confirm=True) for light in lights
    ])
    
    success = sum(1 for r in results if r.success)
    print(f"Controlled {success}/{len(lights)} lights")

asyncio.run(control_multiple())
```

### Configuration File

```yaml
# config.yaml
default_ttl: 5.0
persistence_enabled: true
persistence_backend: sqlite
log_level: INFO

# Resilience
circuit_breaker_enabled: true
rate_limit_enabled: true
```

```python
from fuseiot import Hub, from_yaml

config = from_yaml("config.yaml")
hub = Hub(config)
```

### CLI Usage

```bash
# Discover devices on the network (mDNS)
fuseiot discover

# Control a device
fuseiot on living_room_light --confirm
fuseiot off living_room_light

# Get status
fuseiot status living_room_light
fuseiot stats
```

---

## Advanced Features

### Event Handling

```python
def on_state_change(event):
    print(f"{event.device_id}: {event.old_state} -> {event.new_state}")

# Listen to a specific device
hub.on_state_change(on_state_change, device_id="light_01")

# Listen to all devices
hub.on_state_change(on_state_change)
```

### Batch Operations

```python
# Control 100 devices with limited concurrency
results = await hub.batch(
    [(light, "on", {"confirm": True}) for light in lights],
    max_concurrent=10
)
print(f"Success rate: {results.success_rate:.1f}%")
```

### Circuit Breaker

```python
from fuseiot.utils.circuit_breaker import CircuitBreaker

breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30)

light = hub.add_device(
    HTTP("http://unstable-device/api"),
    Switchable,
    device_id="fragile",
    config=CapabilityConfig(circuit_breaker=breaker)
)

# After 5 failures the circuit opens; commands will fail fast for 30 seconds.
```

### RGB Light Control

```python
from fuseiot import RGBLight, Color

light = hub.add_device(
    HTTP("http://192.168.1.50/api"),
    RGBLight,
    device_id="color_bulb"
)

# Set RGB color
light.set_color(Color(255, 0, 128), brightness=80)

# Set HSV
light.set_hsv(h=120, s=1.0, v=0.8)  # Green

# Effects
light.set_effect("rainbow", speed=50)
```

### Custom Protocols & Capabilities

FuseIoT is designed to be extended. You can implement your own `Protocol` or `Capability` by subclassing the base classes. See the [documentation](https://fuseiot.dev/docs) for details.

---

## Testing

```bash
# Install test dependencies
pip install pytest pytest-cov responses requests-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=fuseiot --cov-report=html

# Run integration tests only
pytest -m integration

# Run a specific test file
pytest tests/test_hub.py -v
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│           Application Layer             │
│    (CLI, Scripts, Applications)         │
├─────────────────────────────────────────┤
│              Hub (Registry)              │
│    - Device management                   │
│    - Event bus                          │
│    - Batch operations                    │
├─────────────────────────────────────────┤
│         Capabilities (Devices)           │
│  Switchable, Sensor, Motor, RGBLight,…  │
├─────────────────────────────────────────┤
│         Protocols (Transport)            │
│    HTTP, MQTT, WebSocket, Serial,…      │
├─────────────────────────────────────────┤
│         State Management                 │
│    Cache, Persistence, Events           │
├─────────────────────────────────────────┤
│         Resilience                       │
│    Circuit Breaker, Rate Limiter, Retry │
└─────────────────────────────────────────┘
```

---

## Documentation

- [Full Documentation](https://fuseiot.dev/docs)
- [API Reference](https://fuseiot.dev/api)
- [Examples](https://github.com/fuseiot/fuseiot/tree/main/examples)

---

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing`).
5. Open a Pull Request.

Please ensure all tests pass and code coverage does not decrease.

---

## License

MIT License – see the [LICENSE](LICENSE) file for details.

---

## Support

- **Issues**: [github.com/fuseiot/fuseiot/issues](https://github.com/fuseiot/fuseiot/issues)
- **Discussions**: [github.com/fuseiot/fuseiot/discussions](https://github.com/fuseiot/fuseiot/discussions)
- **Email**: team@fuseiot.dev

---

*Built with ❤️ for reliable device automation.*