"""One polling coordinator per locality."""

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MushroomClient, SourceError
from .const import DOMAIN, SOURCE_TIMEZONE, UPDATE_INTERVAL
from .models import Forecast, Location

LOGGER = logging.getLogger(__name__)


class MushroomCoordinator(DataUpdateCoordinator[Forecast]):
    """Fetch once for all sensors and roll relative days over at Rome midnight."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: MushroomClient, location: Location) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = client
        self.location = location
        self._date = datetime.now(SOURCE_TIMEZONE).date()

    def start_calendar_updates(self, entry: ConfigEntry) -> None:
        """Keep day-based state accurate without additional upstream requests."""
        entry.async_on_unload(async_track_time_interval(self.hass, self._calendar_tick, timedelta(minutes=1)))

    @callback
    def _calendar_tick(self, now: datetime) -> None:
        today = now.astimezone(SOURCE_TIMEZONE).date()
        if today != self._date:
            self._date = today
            self.async_update_listeners()

    async def _async_update_data(self) -> Forecast:
        try:
            return await self.client.forecast(self.location)
        except SourceError as err:
            raise UpdateFailed(str(err)) from err


type MushroomConfigEntry = ConfigEntry[MushroomCoordinator]
