
import time
import sys
from fuseiot import Hub, HTTP, Switchable, Sensor


def main():
    # Device URLs
    SENSOR_URL = "http://192.168.1.46"
    HEATER_URL = "http://192.168.1.47"
    
    # Control parameters
    TARGET_TEMP = 22.0
    HYSTERESIS = 0.5  # Don't toggle too frequently
    
    hub = Hub()
    
    try:
        # Setup temperature sensor
        temp_protocol = HTTP(SENSOR_URL, timeout=2.0)
        temp_sensor = hub.add_device(
            temp_protocol,
            Sensor,
            unit="celsius",
            device_id="room_temp"
        )
        
        # Setup heater relay
        heater_protocol = HTTP(HEATER_URL, timeout=2.0)
        heater = hub.add_device(
            heater_protocol,
            Switchable,
            device_id="heater"
        )
        
        print(f"Thermostat active: target={TARGET_TEMP}°C, hysteresis={HYSTERESIS}°C")
        print("Press Ctrl+C to exit")
        
        heater_on = False
        
        while True:
            # Read temperature (force fresh reading)
            reading = temp_sensor.read(fresh=True)
            current = reading["value"]
            age = reading["age_seconds"]
            
            print(f"Temperature: {current:.1f}°C (reading age: {age:.1f}s)")
            
            # Control logic with hysteresis
            if not heater_on and current < (TARGET_TEMP - HYSTERESIS):
                print("Below target - turning heater ON")
                result = heater.on(confirm=True)
                if result:
                    heater_on = True
                else:
                    print("WARNING: Heater command failed")
                    
            elif heater_on and current > (TARGET_TEMP + HYSTERESIS):
                print("Above target - turning heater OFF")
                result = heater.off(confirm=True)
                if result:
                    heater_on = False
                else:
                    print("WARNING: Heater command failed")
            
            # Status
            status = "HEATING" if heater_on else "IDLE"
            print(f"Status: {status} | Heater: {'ON' if heater.is_on else 'OFF'}")
            print("-" * 40)
            
            # Wait before next cycle
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        if heater.is_on:
            print("Turning heater off...")
            heater.off(confirm=False)  # Don't wait for confirmation on shutdown
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())