
import asyncio
from fuseiot import (
    Hub, HTTP, Switchable, Sensor, RGBLight, Thermostat,
    auto_config, configure_logging, get_logger
)

logger = get_logger("smart_home")


class SmartHome:
    """Complete smart home controller."""
    
    def __init__(self):
        self.hub = Hub(auto_config())
        self._setup_devices()
    
    def _setup_devices(self):
        """Initialize all devices."""
        # Living room
        self.living_light = self.hub.add_device(
            HTTP("http://192.168.1.45"),
            RGBLight,
            device_id="living_room_light"
        )
        
        # Bedroom
        self.bedroom_light = self.hub.add_device(
            HTTP("http://192.168.1.46"),
            Dimmable,
            device_id="bedroom_light"
        )
        
        # Climate
        self.thermostat = self.hub.add_device(
            HTTP("http://192.168.1.47"),
            Thermostat,
            device_id="main_thermostat"
        )
        
        # Sensors
        self.temp_sensor = self.hub.add_device(
            HTTP("http://192.168.1.48"),
            Sensor,
            unit="celsius",
            device_id="indoor_temp"
        )
        
        # Outdoor
        self.outdoor_light = self.hub.add_device(
            HTTP("http://192.168.1.49"),
            Switchable,
            device_id="outdoor_light"
        )
        
        logger.info("smart_home_initialized", devices=len(self.hub))
    
    async def evening_mode(self):
        """Activate evening scene."""
        logger.info("activating_evening_mode")
        
        # Dim living room, warm color
        await self.living_light.on_async(
            color=Color(255, 147, 41),  # Warm white
            brightness=60
        )
        
        # Bedroom dimmed
        await self.bedroom_light.on_async(brightness=40)
        
        # Outdoor on
        await self.outdoor_light.on_async()
        
        # Temperature comfortable
        await self.thermostat.set_temperature_async(22.0)
        await self.thermostat.set_mode_async(ThermostatMode.AUTO)
    
    async def sleep_mode(self):
        """Activate sleep scene."""
        logger.info("activating_sleep_mode")
        
        # All lights off
        await self.hub.batch([
            (self.living_light, "off", {}),
            (self.bedroom_light, "off", {}),
            (self.outdoor_light, "off", {}),
        ])
        
        # Night temperature
        await self.thermostat.set_temperature_async(18.0)
    
    async def run(self):
        """Main loop."""
        await self.evening_mode()
        
        # Monitor for 1 hour
        for _ in range(12):  # 5 min intervals
            temp = self.temp_sensor.read(fresh=True)
            logger.info("status", 
                       temperature=temp["value"],
                       thermostat=self.thermostat.temperature)
            await asyncio.sleep(300)
        
        await self.sleep_mode()


if __name__ == "__main__":
    configure_logging(level="INFO")
    
    home = SmartHome()
    asyncio.run(home.run())