
import sys
from fuseiot import Hub, HTTP, Switchable


def main():
    # Configuration
    RELAY_URL = "http://192.168.1.45"  # Change to your device
    
    # Initialize
    hub = Hub()
    
    try:
        # Create HTTP protocol
        http = HTTP(RELAY_URL, timeout=2.0)
        
        # Register relay
        relay = hub.add_device(
            http,
            Switchable,
            device_id="lab_relay"
        )
        
        print(f"Connected to relay at {RELAY_URL}")
        print(f"Current state: {'ON' if relay.is_on else 'OFF'}")
        
        # Control
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            
            if command == "on":
                print("Turning ON...")
                result = relay.on(confirm=True)
                print(f"Result: {'OK' if result else 'FAILED'}")
                
            elif command == "off":
                print("Turning OFF...")
                result = relay.off(confirm=True)
                print(f"Result: {'OK' if result else 'FAILED'}")
                
            elif command == "toggle":
                print("Toggling...")
                result = relay.toggle(confirm=True)
                print(f"Result: {'OK' if result else 'FAILED'}")
                
            else:
                print(f"Unknown command: {command}")
                print("Usage: python basic_relay.py [on|off|toggle]")
        else:
            # Just report status
            print("No command given. Use: on, off, toggle")
            
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())