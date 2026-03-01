
import asyncio
import sys
from fuseiot import Hub, HTTP, Switchable, Sensor


async def control_multiple_devices():
    """Control several devices concurrently."""
    hub = Hub()
    
    # Setup devices (synchronous setup, then async operation)
    light1 = hub.add_device(
        HTTP("http://192.168.1.45"),
        Switchable,
        device_id="light_01"
    )
    light2 = hub.add_device(
        HTTP("http://192.168.1.46"),
        Switchable,
        device_id="light_02"
    )
    temp = hub.add_device(
        HTTP("http://192.168.1.47"),
        Sensor,
        device_id="temp_sensor"
    )
    
    # Concurrent operations
    print("Turning on all lights concurrently...")
    
    results = await asyncio.gather(
        light1.on(confirm=True),
        light2.on(confirm=True),
        temp.read(fresh=True),
        return_exceptions=True
    )
    
    light1_result, light2_result, temp_result = results
    
    print(f"Light 1: {'OK' if light1_result else 'FAILED'}")
    print(f"Light 2: {'OK' if light2_result else 'FAILED'}")
    
    if not isinstance(temp_result, Exception):
        print(f"Temperature: {temp_result['value']}°C")
    
    # Sequential with delay
    print("\nSequential off with 1s delay...")
    await light1.off(confirm=True)
    await asyncio.sleep(1.0)
    await light2.off(confirm=True)
    
    print("All operations complete")


async def polling_loop():
    """Continuous sensor polling with async sleep."""
    hub = Hub()
    
    sensor = hub.add_device(
        HTTP("http://192.168.1.50"),
        Sensor,
        unit="celsius",
        device_id="env_sensor"
    )
    
    print("Starting polling loop (Ctrl+C to exit)...")
    
    try:
        while True:
            reading = await sensor.read_async(fresh=True)
            print(f"Temperature: {reading['value']:.1f}°C "
                  f"(age: {reading['age_seconds']:.1f}s)")
            
            # Async sleep doesn't block other tasks
            await asyncio.sleep(5.0)
            
    except asyncio.CancelledError:
        print("\nPolling cancelled")


# Helper method for async sensor read (would be added to Sensor class)
async def sensor_read_async(self, fresh=False):
    """Async wrapper for sensor read."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.read, fresh)


# Monkey-patch for demo
Sensor.read_async = sensor_read_async


def main():
    """Run async examples."""
    if len(sys.argv) < 2:
        print("Usage: python async_example.py [concurrent|polling]")
        return 1
    
    command = sys.argv[1]
    
    try:
        if command == "concurrent":
            asyncio.run(control_multiple_devices())
        elif command == "polling":
            asyncio.run(polling_loop())
        else:
            print(f"Unknown command: {command}")
            return 1
    except KeyboardInterrupt:
        print("\nExiting...")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())