import asyncio
import signal
from datetime import datetime, time as dt_time
from fuseiot import (
    Hub, HTTP, Switchable, Sensor,
    auto_config, configure_logging, get_logger,
    RuleEngine, Condition, Action
)

logger = get_logger("advanced_thermostat")


class AdvancedThermostat:
    """Smart thermostat with rules and scheduling."""
    
    def __init__(self):
        self.hub = Hub(auto_config())
        self.rules = RuleEngine(self.hub)
        self.running = False
        
        # Setup devices
        self.sensor = self.hub.add_device(
            HTTP("http://192.168.1.46"),
            Sensor,
            unit="celsius",
            device_id="room_temp"
        )
        self.heater = self.hub.add_device(
            HTTP("http://192.168.1.47"),
            Switchable,
            device_id="heater"
        )
        self.fan = self.hub.add_device(
            HTTP("http://192.168.1.48"),
            Switchable,
            device_id="circulation_fan"
        )
        
        # Configuration
        self.target_temp = 22.0
        self.hysteresis = 0.5
        self.schedule = {
            "morning": (dt_time(6, 0), 22.0),
            "day": (dt_time(9, 0), 20.0),
            "evening": (dt_time(18, 0), 22.0),
            "night": (dt_time(23, 0), 18.0),
        }
        
        self._setup_rules()
    
    def _setup_rules(self):
        """Setup automation rules."""
        # Rule 1: Heat when cold
        self.rules.add(
            if_condition=Condition("room_temp", "value", "<", self.target_temp - self.hysteresis),
            then_actions=[Action("heater", "on")],
            else_actions=[Action("heater", "off")]
        )
        
        # Rule 2: Circulation fan when heating
        self.rules.add(
            if_condition=Condition("heater", "is_on", "==", True),
            then_actions=[Action("circulation_fan", "on")],
            else_actions=[Action("circulation_fan", "off", delay=300)]  # 5 min delay
        )
    
    async def run(self):
        """Main control loop."""
        self.running = True
        logger.info("thermostat_started", target=self.target_temp)
        
        # Setup signal handlers
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, self.stop)
        
        try:
            while self.running:
                # Read temperature
                reading = await self.sensor.read_async(fresh=True)
                current_temp = reading["value"]
                
                # Check schedule
                self._update_schedule()
                
                # Evaluate rules
                await self.rules.evaluate()
                
                # Log status
                heater_status = "ON" if self.heater.is_on else "OFF"
                logger.info(
                    "thermostat_status",
                    temperature=current_temp,
                    target=self.target_temp,
                    heater=heater_status,
                    mode=self._get_current_schedule()
                )
                
                await asyncio.sleep(30)  # 30 second loop
                
        except asyncio.CancelledError:
            logger.info("thermostat_cancelled")
        finally:
            await self.shutdown()
    
    def _update_schedule(self):
        """Update target temperature based on schedule."""
        now = datetime.now().time()
        
        current_target = None
        for period, (start_time, temp) in sorted(self.schedule.items(), key=lambda x: x[1][0]):
            if now >= start_time:
                current_target = temp
        
        if current_target and current_target != self.target_temp:
            logger.info("schedule_change", old_target=self.target_temp, new_target=current_target)
            self.target_temp = current_target
            # Update rules with new target
            self._setup_rules()
    
    def _get_current_schedule(self) -> str:
        """Get current schedule period."""
        now = datetime.now().time()
        current = "night"
        for period, (start_time, _) in self.schedule.items():
            if now >= start_time:
                current = period
        return current
    
    def stop(self):
        """Stop the thermostat."""
        logger.info("thermostat_stopping")
        self.running = False
    
    async def shutdown(self):
        """Cleanup."""
        logger.info("thermostat_shutdown")
        # Safe shutdown - turn off heater
        try:
            await self.heater.off_async(confirm=False)
        except:
            pass


async def main():
    configure_logging(level="INFO")
    thermostat = AdvancedThermostat()
    await thermostat.run()


if __name__ == "__main__":
    asyncio.run(main())