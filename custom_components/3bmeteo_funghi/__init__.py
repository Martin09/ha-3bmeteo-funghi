"""3BMeteo mushroom-fruiting forecasts."""

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import MushroomClient
from .const import CARD_FILE, CARD_URL, CONF_LOCATION, DOMAIN
from .coordinator import MushroomConfigEntry, MushroomCoordinator
from .models import Location

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Serve the bundled module once; resource registration is opt-in in the UI."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(Path(__file__).parent / "card" / CARD_FILE), cache_headers=False)]
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MushroomConfigEntry) -> bool:
    coordinator = MushroomCoordinator(
        hass, entry, MushroomClient(async_get_clientsession(hass)), Location(**entry.data[CONF_LOCATION])
    )
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    coordinator.start_calendar_updates(entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MushroomConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
