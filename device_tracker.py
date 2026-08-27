"""Support for HondaLink device tracker entities."""

from homeassistant.components.device_tracker.const import SourceType
from homeassistant.components.device_tracker.entity import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import HondaLinkEntity
from .util import dms_to_decimal, get_path, status_body, to_float


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a HondaLink device tracker entity based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities([HondaLinkDeviceTracker(coordinator, entry)])


class HondaLinkDeviceTracker(HondaLinkEntity, TrackerEntity):
    """Representation of a HondaLink device tracker entity."""

    _attr_translation_key = "location"

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        """Initialize entity."""
        super().__init__(coordinator, entry, "location")

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        body = status_body(self.coordinator.data or {})
        return dms_to_decimal(get_path(body, "gpsData.coordinate.latitude"))

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        body = status_body(self.coordinator.data or {})
        return dms_to_decimal(get_path(body, "gpsData.coordinate.longitude"))

    @property
    def location_accuracy(self) -> int | None:
        """Return the location accuracy of the device.

        Value in meters.
        """
        body = status_body(self.coordinator.data or {})
        radius = to_float(get_path(body, "gpsData.accuracy.radius"))
        return int(radius) if radius is not None else None
