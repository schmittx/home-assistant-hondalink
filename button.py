"""Support for HondaLink button entities."""

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import HondaLinkDataUpdateCoordinator
from .entity import HondaLinkEntity


@dataclass(frozen=True, kw_only=True)
class HondaLinkButtonEntityDescription(ButtonEntityDescription):
    """Class to describe a HondaLink button entity."""

    press_fn: Callable[[HondaLinkDataUpdateCoordinator], object]


BUTTONS: tuple[HondaLinkButtonEntityDescription, ...] = (
    HondaLinkButtonEntityDescription(
        key="start_engine",
        translation_key="start_engine",
        icon="mdi:engine",
        press_fn=lambda coordinator: coordinator.async_start_engine(),
    ),
    HondaLinkButtonEntityDescription(
        key="stop_engine",
        translation_key="stop_engine",
        icon="mdi:engine-off",
        press_fn=lambda coordinator: coordinator.async_stop_engine(),
    ),
    HondaLinkButtonEntityDescription(
        key="horn",
        translation_key="horn",
        icon="mdi:bullhorn",
        press_fn=lambda coordinator: coordinator.async_horn(),
    ),
    HondaLinkButtonEntityDescription(
        key="lights",
        translation_key="lights",
        icon="mdi:car-light-high",
        press_fn=lambda coordinator: coordinator.async_lights(),
    ),
    HondaLinkButtonEntityDescription(
        key="stop_horn_lights",
        translation_key="stop_horn_lights",
        icon="mdi:car-light-alert",
        press_fn=lambda coordinator: coordinator.async_stop_horn_lights(),
    ),
    HondaLinkButtonEntityDescription(
        key="refresh",
        translation_key="refresh",
        icon="mdi:refresh",
        press_fn=lambda coordinator: coordinator.async_force_refresh(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up a HondaLink button entity based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        HondaLinkButtonEntity(coordinator, entry, description)
        for description in BUTTONS
    )


class HondaLinkButtonEntity(HondaLinkEntity, ButtonEntity):
    """Representation of a HondaLink button entity."""

    entity_description: HondaLinkButtonEntityDescription

    def __init__(
        self,
        coordinator: HondaLinkDataUpdateCoordinator,
        entry: ConfigEntry,
        description: HondaLinkButtonEntityDescription,
    ) -> None:
        """Initialize entity."""
        super().__init__(coordinator, entry, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.press_fn(self.coordinator)
