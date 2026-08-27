"""Support for HondaLink lock entities."""

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import HondaLinkEntity
from .util import all_door_locks_locked, status_body


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a HondaLink lock entity based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([HondaLinkDoorLockEntity(coordinator, entry)])


class HondaLinkDoorLockEntity(HondaLinkEntity, LockEntity):
    """Representation of a HondaLink lock entity."""

    _attr_translation_key = "doors"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize entity."""
        super().__init__(coordinator, entry, "doors_lock")

    @property
    def is_locked(self) -> bool | None:
        """Return true if the lock is locked."""
        return all_door_locks_locked(status_body(self.coordinator.data or {}))

    async def async_lock(self, **kwargs) -> None:
        """Lock the lock."""
        await self.coordinator.async_lock()

    async def async_unlock(self, **kwargs) -> None:
        """Unlock the lock."""
        await self.coordinator.async_unlock()
