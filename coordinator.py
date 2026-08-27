"""Data update coordinator for the HondaLink integration."""

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HondaLinkAPI, HondaLinkCommandError, HondaLinkError
from .const import CONF_SCAN_INTERVAL, CONF_VIN, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class HondaLinkDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """HondaLink data update coordinator."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: HondaLinkAPI
    ) -> None:
        """Initialize."""
        self.api = api
        self.vin = entry.data[CONF_VIN]
        interval = int(entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        super().__init__(
            hass,
            logging.getLogger(__name__),
            name=f"{DOMAIN}-{self.vin}",
            update_interval=timedelta(minutes=interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.api.async_get_dashboard_latest(self.vin)
        except HondaLinkError as err:
            raise UpdateFailed(str(err)) from err

    async def async_force_refresh(self) -> None:
        """Async force refresh."""
        try:
            await self.api.async_request_dashboard_update(self.vin)
        except HondaLinkCommandError as err:
            _LOGGER.warning("HondaLink live dashboard refresh request failed: %s", err)
        except HondaLinkError as err:
            _LOGGER.warning("HondaLink live dashboard refresh request failed: %s", err)
        await self.async_refresh()

    async def async_start_engine(self) -> None:
        """Async start engine."""
        await self._run_command(self.api.async_start_engine)

    async def async_stop_engine(self) -> None:
        """Async stop engine."""
        await self._run_command(self.api.async_stop_engine)

    async def async_lock(self) -> None:
        """Async lock."""
        await self._run_command(self.api.async_lock)

    async def async_unlock(self) -> None:
        """Async unlock."""
        await self._run_command(self.api.async_unlock)

    async def async_horn(self) -> None:
        """Async horn."""
        await self._run_command(self.api.async_horn)

    async def async_lights(self) -> None:
        """Async lights."""
        await self._run_command(self.api.async_lights)

    async def async_stop_horn_lights(self) -> None:
        """Async stop horn lights."""
        await self._run_command(self.api.async_stop_horn_lights)

    async def _run_command(self, command) -> None:
        try:
            await command()
        except HondaLinkCommandError as err:
            raise HomeAssistantError(str(err)) from err
        await self.async_request_refresh()
