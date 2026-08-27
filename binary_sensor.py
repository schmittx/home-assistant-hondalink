"""Support for HondaLink binary sensor entities."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import HondaLinkEntity
from .util import (
    any_light_on,
    any_open_state,
    get_path,
    maintenance_minder_on,
    maintenance_required,
    status_body,
)


@dataclass(frozen=True, kw_only=True)
class HondaLinkBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class to describe a HondaLink binary sensor entity."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    attr_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


DOOR_KEYS = [
    "firstRowDriver",
    "firstRowPassenger",
    "secondRowDriver",
    "secondRowPassenger",
]
WINDOW_KEYS = ["frontWindowDR", "frontWindowAS", "rearWindowRR", "rearWindowRL"]


BINARY_SENSORS: tuple[HondaLinkBinarySensorEntityDescription, ...] = (
    HondaLinkBinarySensorEntityDescription(
        key="any_door_open",
        translation_key="any_door_open",
        device_class=BinarySensorDeviceClass.DOOR,
        value_fn=lambda body: any_open_state(body, "doorStatus", DOOR_KEYS),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="hood_open",
        translation_key="hood_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda body: any_open_state(body, "doorStatus", ["hood"]),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="trunk_open",
        translation_key="trunk_open",
        device_class=BinarySensorDeviceClass.OPENING,
        value_fn=lambda body: any_open_state(body, "doorStatus", ["trunk"]),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="any_window_open",
        translation_key="any_window_open",
        device_class=BinarySensorDeviceClass.WINDOW,
        value_fn=lambda body: any_open_state(
            body, "windowStatus", WINDOW_KEYS, "closeState"
        ),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="any_light_on",
        translation_key="any_light_on",
        device_class=BinarySensorDeviceClass.LIGHT,
        value_fn=any_light_on,
    ),
    HondaLinkBinarySensorEntityDescription(
        key="warning_lamp_on",
        translation_key="warning_lamp_on",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda body: any(
            str(message.get("condition", "")).upper() == "ON"
            for group in get_path(body, "warningLamps.data", []) or []
            if isinstance(group, dict)
            for message in group.get("messages", [])
            if isinstance(message, dict)
        ),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="remote_engine_running",
        translation_key="remote_engine_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda body: (
            str(
                get_path(body, "remoteEngineStart.vehicleStartEvent.resStatus", "")
            ).upper()
            == "ON"
        ),
    ),
    HondaLinkBinarySensorEntityDescription(
        key="maintenance_minder_on",
        translation_key="maintenance_minder_on",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=maintenance_minder_on,
        attr_fn=lambda body: {
            "maintenance_required": maintenance_required(body),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a HondaLink binary sensor entity based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        HondaLinkBinarySensorEntity(coordinator, entry, description)
        for description in BINARY_SENSORS
    )


class HondaLinkBinarySensorEntity(HondaLinkEntity, BinarySensorEntity):
    """Representation of a HondaLink binary sensor entity."""

    entity_description: HondaLinkBinarySensorEntityDescription

    def __init__(
        self,
        coordinator,
        entry: ConfigEntry,
        description: HondaLinkBinarySensorEntityDescription,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.value_fn(
            status_body(self.coordinator.data or {})
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes."""
        if self.entity_description.attr_fn is None or not self.is_on:
            return None
        return self.entity_description.attr_fn(status_body(self.coordinator.data or {}))
