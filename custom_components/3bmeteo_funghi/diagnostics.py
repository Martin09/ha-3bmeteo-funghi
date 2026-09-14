"""Diagnostics without exposing the user's selected locality."""

from homeassistant.core import HomeAssistant

from .coordinator import MushroomConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: MushroomConfigEntry) -> dict:
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "last_update_success": coordinator.last_update_success,
        "forecast_days": len(data.days) if data else 0,
        "published_at": data.published_at.isoformat() if data else None,
        "unknown_categories": sorted({day.description for day in data.days if day.category is None}) if data else [],
    }
