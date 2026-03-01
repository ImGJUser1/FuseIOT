from fuseiot import (
    Hub, MQTT, Motor, Sensor, EnergyMonitor,
    CircuitBreaker, CapabilityConfig,
    configure_logging, get_logger
)

logger = get_logger("industrial")


class ConveyorSystem:
    """Industrial conveyor belt control."""
    
    def __init__(self):
        self.hub = Hub()
        
        # Circuit breaker for safety
        self.breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60.0
        )
        
        self._setup_devices()
    
    def _setup_devices(self):
        """Setup conveyor motors and sensors."""
        # Main conveyor motor
        self.conveyor_motor = self.hub.add_device(
            MQTT("192.168.1.100", topic_prefix="conveyor/main"),
            Motor,
            position_range=(0, 10000),
            device_id="main_conveyor",
            config=CapabilityConfig(circuit_breaker=self.breaker)
        )
        
        # Position sensor
        self.position_sensor = self.hub.add_device(
            MQTT("192.168.1.100", topic_prefix="sensors/position"),
            Sensor,
            device_id="position_sensor"
        )
        
        # Energy monitor
        self.energy = self.hub.add_device(
            HTTP("http://192.168.1.101"),
            EnergyMonitor,
            cost_per_kwh=0.12,
            device_id="conveyor_power"
        )
        
        # Emergency stop button
        self.e_stop = self.hub.add_device(
            MQTT("192.168.1.100", topic_prefix="safety/e-stop"),
            Switchable,
            device_id="emergency_stop"
        )
    
    def run_conveyor(self, speed: float, duration_seconds: float):
        """Run conveyor at specified speed."""
        # Check emergency stop
        if self.e_stop.is_on:
            logger.error("emergency_stop_active")
            return False
        
        # Set speed
        result = self.conveyor_motor.set_speed(speed)
        if not result.success:
            logger.error("speed_set_failed", error=result.error)
            return False
        
        # Monitor energy
        start_energy = self.energy.energy_kwh
        
        # Run for duration
        import time
        start_time = time.time()
        
        while time.time() - start_time < duration_seconds:
            # Check position
            pos = self.position_sensor.value
            
            # Check energy consumption
            current_energy = self.energy.energy_kwh
            energy_used = current_energy - start_energy
            
            logger.info("conveyor_running",
                       position=pos,
                       speed=speed,
                       energy_kwh=energy_used,
                       cost=self.energy.calculate_cost(energy_used))
            
            time.sleep(1)
        
        # Stop
        self.conveyor_motor.stop()
        return True
    
    def emergency_stop(self):
        """Trigger emergency stop."""
        logger.critical("emergency_stop_triggered")
        self.conveyor_motor.stop()
        self.e_stop.on(confirm=False)


if __name__ == "__main__":
    configure_logging(level="INFO")
    
    conveyor = ConveyorSystem()
    conveyor.run_conveyor(speed=50.0, duration_seconds=60.0)