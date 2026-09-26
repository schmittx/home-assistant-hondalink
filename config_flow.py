"""Adds config flow for HondaLink integration."""

import logging
from typing import Any
import uuid

import probatio

from homeassistant import config_entries
from homeassistant.const import UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import HondaLinkAPI, HondaLinkAuthError, HondaLinkError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_CLIENT_REG_KEY,
    CONF_COUNTRY,
    CONF_DEVICE_ID,
    CONF_EMAIL,
    CONF_EXPIRES_AT,
    CONF_HIDAS_IDENT,
    CONF_LANGUAGE,
    CONF_LOCK_COMMAND,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PIN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SESSION_ID,
    CONF_UNLOCK_COMMAND,
    CONF_VEHICLE_INFO,
    CONF_VIN,
    DEFAULT_LOCK_COMMAND,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_UNLOCK_COMMAND,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _vehicle_title(vehicle: dict[str, Any] | None, vin: str) -> str:
    vehicle = vehicle or {}
    if alias := vehicle.get("Alias Name") or vehicle.get("alias"):
        return str(alias)
    year = vehicle.get("ModelYear")
    division = vehicle.get("DivisionName")
    model = vehicle.get("ModelGroupNameFriendly") or vehicle.get("ModelCode")
    if year and division and model:
        return f"{year} {division} {model}"
    return f"{DEFAULT_NAME} {vin[-6:]}"


def _vehicle_label(vehicle: dict[str, Any]) -> str:
    vin = vehicle.get("VIN", "")
    title = _vehicle_title(vehicle, vin)
    return f"{title} ({vin})"


class HondaLinkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HondaLink integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._api: HondaLinkAPI | None = None
        self._base_data: dict[str, Any] = {}
        self._vehicles: list[dict[str, Any]] = []

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Async step user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL].strip()
            password = user_input[CONF_PASSWORD]
            device_id = str(uuid.uuid4())
            session_id = str(uuid.uuid4())

            session = async_get_clientsession(self.hass)
            self._api = HondaLinkAPI(
                session,
                email=email,
                password=password,
                #                pin=pin,
                #                vin=vin or None,
                device_id=device_id,
                session_id=session_id,
            )

            try:
                await self._api.async_login()
                self._vehicles = await self._api.async_get_vehicles()
            except HondaLinkAuthError as err:
                _LOGGER.warning(
                    "HondaLink authentication failed during config flow: %s", err
                )
                errors["base"] = "invalid_auth"
            except HondaLinkError as err:
                _LOGGER.warning(
                    "HondaLink connection failed during config flow: %s", err
                )
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected HondaLink config flow error")
                errors["base"] = "unknown"
            else:
                self._base_data = {
                    CONF_EMAIL: email,
                    CONF_PASSWORD: password,
                }
                return await self.async_step_vehicle()

        schema = probatio.Schema(
            {
                probatio.Required(CONF_EMAIL): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.EMAIL,
                    )
                ),
                probatio.Required(CONF_PASSWORD): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.PASSWORD,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_vehicle(self, user_input: dict[str, Any] | None = None):
        """Async step vehicle."""
        errors: dict[str, str] = {}
        vehicles_by_vin = {
            item["VIN"]: item for item in self._vehicles if item.get("VIN")
        }

        if user_input is not None:
            for vin, vehicle in vehicles_by_vin.items():
                if _vehicle_label(vehicle) == user_input[CONF_NAME]:
                    conf_vin = vin
            vehicle_info = vehicles_by_vin.get(conf_vin, {})
            if self._api is None:
                errors["base"] = "unknown"
            else:
                self._api.vin = conf_vin
                self._api.pin = user_input[CONF_PIN]
                await self.async_set_unique_id(conf_vin)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_vehicle_title(vehicle_info, conf_vin),
                    data=self._entry_data(
                        api=self._api,
                        email=self._base_data[CONF_EMAIL],
                        password=self._base_data[CONF_PASSWORD],
                        pin=user_input[CONF_PIN],
                        vin=conf_vin,
                        vehicle_info=vehicle_info,
                    ),
                )

        schema = probatio.Schema(
            {
                probatio.Required(CONF_NAME): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            _vehicle_label(vehicle)
                            for vehicle in vehicles_by_vin.values()
                            if vehicle.get("Enrollment") == "Y"
                        ],
                        sort=True,
                    )
                ),
                probatio.Required(CONF_PIN): TextSelector(
                    TextSelectorConfig(type=TextSelectorType.NUMBER)
                ),
            }
        )
        return self.async_show_form(
            step_id="vehicle", data_schema=schema, errors=errors
        )

    async def _async_create_vehicle_entry(
        self,
        api: HondaLinkAPI,
        email: str,
        password: str,
        pin: str,
        vin: str,
        vehicle_info: dict[str, Any] | None,
    ):
        await self.async_set_unique_id(vin)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=_vehicle_title(vehicle_info, vin),
            data=self._entry_data(api, email, password, pin, vin, vehicle_info),
        )

    def _entry_data(
        self,
        api: HondaLinkAPI,
        email: str,
        password: str,
        pin: str,
        vin: str,
        vehicle_info: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            CONF_EMAIL: email,
            CONF_PASSWORD: password,
            CONF_PIN: pin,
            CONF_VIN: vin,
            CONF_VEHICLE_INFO: vehicle_info or {},
            CONF_CLIENT_REG_KEY: api.client_reg_key,
            CONF_ACCESS_TOKEN: api.access_token,
            CONF_REFRESH_TOKEN: api.refresh_token,
            CONF_EXPIRES_AT: api.expires_at,
            CONF_COUNTRY: api.country,
            CONF_LANGUAGE: api.language,
            CONF_HIDAS_IDENT: api.hidas_ident,
            CONF_DEVICE_ID: api.device_id,
            CONF_SESSION_ID: api.session_id,
        }

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """HondaLink options callback."""
        return HondaLinkOptionsFlowHandler()


class HondaLinkOptionsFlowHandler(config_entries.OptionsFlow):
    """Config flow options for HondaLink."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data
        schema = probatio.Schema(
            {
                probatio.Required(
                    CONF_PIN,
                    default=options.get(CONF_PIN, data.get(CONF_PIN, "")),
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.NUMBER,
                    )
                ),
                probatio.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        unit_of_measurement=UnitOfTime.MINUTES,
                    )
                ),
                probatio.Required(
                    CONF_LOCK_COMMAND,
                    default=options.get(CONF_LOCK_COMMAND, DEFAULT_LOCK_COMMAND),
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
                probatio.Required(
                    CONF_UNLOCK_COMMAND,
                    default=options.get(CONF_UNLOCK_COMMAND, DEFAULT_UNLOCK_COMMAND),
                ): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
