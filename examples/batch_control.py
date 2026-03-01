import asyncio
from fuseiot import Hub, HTTP, Switchable, configure_logging

configure_logging(level="INFO")


async def control_all_lights():
    """Control multiple lights simultaneously."""
    hub = Hub()
    
    # Add multiple lights
    lights = []
    for i in range(1, 5):
        light = hub.add_device(
            HTTP(f"http://192.168.1.{40 + i}"),
            Switchable,
            device_id=f"light_{i:02d}"
        )
        lights.append(light)
    
    # Turn all on concurrently
    print("Turning all lights on...")
    results = await asyncio.gather(*[
        light.on_async(confirm=True) for light in lights
    ])
    
    success_count = sum(1 for r in results if r.success)
    confirmed_count = sum(1 for r in results if r.confirmed)
    print(f"Success: {success_count}/{len(lights)}, Confirmed: {confirmed_count}/{len(lights)}")
    
    # Batch turn off using Hub batch method
    print("\nTurning all lights off (batched)...")
    batch_result = await hub.batch(
        [(light, "off", {"confirm": True}) for light in lights],
        max_concurrent=2  # Limit concurrency
    )
    
    print(f"Batch result: {batch_result}")
    
    # Cleanup
    hub.clear()


if __name__ == "__main__":
    asyncio.run(control_all_lights())