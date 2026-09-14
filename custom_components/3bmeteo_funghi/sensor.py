"""Automation-friendly sensors sharing a single forecast response."""

from datetime import date, datetime, timedelta

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CATEGORY_SCORES, DOMAIN, NAME, SOURCE_TIMEZONE
from .coordinator import MushroomConfigEntry, MushroomCoordinator

PARALLEL_UPDATES = 0
SENSORS = (
    SensorEntityDescription(key="score", translation_key="score", icon="mdi:mushroom"),
    SensorEntityDescription(key="tomorrow", translation_key="tomorrow", icon="mdi:mushroom"),
    SensorEntityDescription(
        key="category", translation_key="category", device_class=SensorDeviceClass.ENUM, options=list(CATEGORY_SCORES)
    ),
    SensorEntityDescription(key="peak", translation_key="peak", icon="mdi:chart-line"),
    SensorEntityDescription(key="best_day", translation_key="best_day", device_class=SensorDeviceClass.DATE),
    SensorEntityDescription(
        key="forecast_days", translation_key="forecast_days", entity_category=EntityCategory.DIAGNOSTIC
    ),
    SensorEntityDescription(
        key="published",
        translation_key="published",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: MushroomConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    async_add_entities(MushroomSensor(entry.runtime_data, description) for description in SENSORS)


class MushroomSensor(CoordinatorEntity[MushroomCoordinator], SensorEntity):
    """A relative-day sensor. Missing data is unknown, never zero."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _unrecorded_attributes = frozenset({"forecast", "fetched_at"})

    def __init__(self, coordinator: MushroomCoordinator, description: SensorEntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        location = coordinator.location
        self._attr_unique_id = f"{location.id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, location.id)},
            entry_type=DeviceEntryType.SERVICE,
            name=location.label,
            manufacturer="3BMeteo",
            model=NAME,
            configuration_url=location.url,
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data.upcoming(datetime.now(SOURCE_TIMEZONE).date()))

    @property
    def native_value(self) -> int | str | date | datetime | None:
        data = self.coordinator.data
        today = datetime.now(SOURCE_TIMEZONE).date()
        key = self.entity_description.key
        if key in ("score", "tomorrow", "category"):
            day = data.on(today + timedelta(days=key == "tomorrow"))
            return (day.category if key == "category" else day.score) if day else None
        if key in ("peak", "best_day"):
            best = data.best(today)
            return (best.date if key == "best_day" else best.score) if best else None
        if key == "forecast_days":
            return len(data.upcoming(today))
        return data.published_at

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.entity_description.key != "score":
            return None
        data = self.coordinator.data
        today = datetime.now(SOURCE_TIMEZONE).date()
        day = data.on(today)
        return {
            "forecast": [item.as_dict() for item in data.upcoming(today)],
            "description": day.description if day else None,
            "source_url": self.coordinator.location.url,
            "location": self.coordinator.location.name,
            "published_at": data.published_at.isoformat(),
            "fetched_at": data.fetched_at.isoformat(),
            "score_min": 0,
            "score_max": 100,
        }
