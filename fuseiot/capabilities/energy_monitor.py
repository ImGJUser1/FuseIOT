from .base import Capability
from ..protocols.base import Protocol
from ..result import Result

class EnergyMonitor(Capability):
    """Capability for energy monitoring devices."""

    async def get_power_usage(self, period: str = "current") -> Result:
        """Get power usage data."""
        valid_periods = ["current", "daily", "monthly"]
        if period not in valid_periods:
            raise ValueError(f"Invalid period: {period}")
        payload = {"period": period}
        return await self._protocol.send_command("get_power", payload)

    async def get_voltage(self) -> Result:
        """Get current voltage."""
        return await self._protocol.send_command("get_voltage")

    async def get_current(self) -> Result:
        """Get current amperage."""
        return await self._protocol.send_command("get_current")