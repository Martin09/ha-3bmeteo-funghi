"""Search, choose, and validate a locality using Home Assistant's UI."""

from dataclasses import asdict
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode

from .api import CannotConnect, MushroomClient, SourceError
from .const import CONF_LOCATION, CONF_QUERY, DOMAIN
from .models import Location


class MushroomConfigFlow(ConfigFlow, domain=DOMAIN):
    """One entry per stable 3BMeteo locality ID."""

    VERSION = 1

    def __init__(self) -> None:
        self._locations: dict[str, Location] = {}

    @property
    def client(self) -> MushroomClient:
        return MushroomClient(async_get_clientsession(self.hass))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            query = user_input[CONF_QUERY].strip()
            if len(query) < 3:
                errors[CONF_QUERY] = "query_too_short"
            else:
                try:
                    self._locations = {loc.id: loc for loc in await self.client.search(query)}
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except SourceError:
                    errors["base"] = "invalid_response"
                else:
                    if self._locations:
                        return await self.async_step_location()
                    errors["base"] = "no_locations"
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_QUERY): vol.All(str, vol.Length(max=100))}),
            errors=errors,
        )

    async def async_step_location(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors = {}
        if user_input is not None:
            location = self._locations.get(user_input[CONF_LOCATION])
            if location is None:
                errors["base"] = "invalid_location"
            else:
                await self.async_set_unique_id(location.id)
                self._abort_if_unique_id_configured()
                try:
                    await self.client.forecast(location)
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except SourceError:
                    errors["base"] = "invalid_response"
                else:
                    return self.async_create_entry(title=location.label, data={CONF_LOCATION: asdict(location)})
        return self.async_show_form(
            step_id="location",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LOCATION): SelectSelector(
                        SelectSelectorConfig(
                            options=[{"value": loc.id, "label": loc.label} for loc in self._locations.values()],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )
