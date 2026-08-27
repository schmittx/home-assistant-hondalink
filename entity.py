"""Base class for HondaLink entities."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_VEHICLE_INFO, CONF_VIN, DOMAIN
from .coordinator import HondaLinkDataUpdateCoordinator


class HondaLinkEntity(CoordinatorEntity[HondaLinkDataUpdateCoordinator]):
    """Representation of a HondaLink entity."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: HondaLinkDataUpdateCoordinator, entry, key: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.vin = entry.data[CONF_VIN]
        self._attr_unique_id = f"{self.vin}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes.

        Implemented by platform classes.
        """
        vehicle = self.entry.data.get(CONF_VEHICLE_INFO) or {}
        year = vehicle.get("ModelYear")
        model = vehicle.get("ModelGroupNameFriendly") or vehicle.get("ModelCode")
        trim = vehicle.get("ModelTrimTypeCode")
        model_name = " ".join(str(x) for x in (year, model, trim) if x)
        return DeviceInfo(
            identifiers={(DOMAIN, self.vin)},
            manufacturer=vehicle.get("DivisionName") or "Honda",
            model=model_name or None,
            name=vehicle.get("Alias Name") or model_name or f"Honda {self.vin[-6:]}",
            serial_number=self.vin,
            configuration_url="https://mygarage.honda.com/",
        )
