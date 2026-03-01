from .base import Capability
from ..protocols.base import Protocol
from ..result import Result
from ..exceptions import CommandError

class Lock(Capability):
    """Capability for smart lock devices."""

    async def lock(self, confirm: bool = True) -> Result:
        """Lock the device."""
        result = await self._protocol.send_command("lock")
        if confirm:
            await self._confirm_state("locked")
        return result

    async def unlock(self, confirm: bool = True) -> Result:
        """Unlock the device."""
        result = await self._protocol.send_command("unlock")
        if confirm:
            await self._confirm_state("unlocked")
        return result

    async def get_status(self) -> Result:
        """Get lock status."""
        return await self._protocol.send_command("status")

    async def _confirm_state(self, expected_state: str) -> None:
        """Confirm lock state."""
        for _ in range(3):
            status = (await self.get_status()).data.get("state")
            if status == expected_state:
                return
            await asyncio.sleep(0.5)
        raise CommandError("State confirmation failed")