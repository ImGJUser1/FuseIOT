from typing import Optional
from .base import Capability
from ..protocols.base import Protocol
from ..result import Result
from ..exceptions import CommandError
import asyncio

class Thermostat(Capability):
    """Capability for thermostat devices, supporting temperature control and modes."""

    def __init__(self, protocol: Protocol, device_id: str):
        super().__init__(protocol, device_id)
        self._supported_modes = ["off", "heat", "cool", "auto"]

    async def set_temperature(self, temperature: float, confirm: bool = True) -> Result:
        """Set the target temperature."""
        if not 10 <= temperature <= 35:
            raise CommandError("Temperature out of range (10-35°C)")
        payload = {"target_temp": temperature}
        result = await self._protocol.send_command("set_temp", payload)
        if confirm:
            await self._confirm_state({"target_temp": temperature})
        return result

    async def get_temperature(self) -> Result:
        """Get current temperature readings."""
        return await self._protocol.send_command("get_temp")

    async def set_mode(self, mode: str, confirm: bool = True) -> Result:
        """Set thermostat mode."""
        if mode not in self._supported_modes:
            raise CommandError(f"Unsupported mode: {mode}")
        payload = {"mode": mode}
        result = await self._protocol.send_command("set_mode", payload)
        if confirm:
            await self._confirm_state({"mode": mode})
        return result

    async def _confirm_state(self, expected: dict) -> None:
        """Confirm state change with polling."""
        for _ in range(5):
            current = (await self.get_temperature()).data
            if all(current.get(k) == v for k, v in expected.items()):
                return
            await asyncio.sleep(1)
        raise CommandError("State confirmation failed")