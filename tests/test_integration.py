"""Real HA lifecycle, translated entities, availability, and calendar rollover."""

from dataclasses import asdict, replace
from datetime import UTC, datetime
from importlib import import_module

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from .conftest import DOMAIN, PACKAGE, api


async def setup(hass, entry):
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    return {
        key: registry.async_get_entity_id("sensor", DOMAIN, f"376_{key}")
        for key in (
            "score",
            "tomorrow",
            "category",
            "peak",
            "best_day",
            "forecast_days",
            "published",
        )
    }


async def test_setup_sensors_unload(hass, client, entry):
    ids = await setup(hass, entry)
    assert all(ids.values())
    assert hass.states.get(ids["score"]).state == "0"
    assert len(hass.states.get(ids["score"]).attributes["forecast"]) == 15
    assert hass.states.get(ids["category"]).state == "absent"
    assert hass.states.get(ids["peak"]).state == "33"
    assert hass.states.get(ids["best_day"]).state == "2026-09-17"
    assert hass.states.get(ids["forecast_days"]).state == "15"
    assert "unit_of_measurement" not in hass.states.get(ids["score"]).attributes
    client[1].assert_awaited_once()
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert hass.states.get(ids["score"]).state == "unavailable"


async def test_update_failure_and_recovery(hass, client, entry):
    ids = await setup(hass, entry)
    client[1].side_effect = api.CannotConnect("offline")
    await entry.runtime_data.async_refresh()
    assert hass.states.get(ids["score"]).state == "unavailable"
    client[1].side_effect = None
    await entry.runtime_data.async_refresh()
    assert hass.states.get(ids["score"]).state == "0"


async def test_initial_failure_retries(hass, client, entry):
    client[1].side_effect = api.SourceError("changed markup")
    entry.add_to_hass(hass)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_rome_rollover_without_fetch(hass, client, entry, freezer):
    freezer.move_to("2026-09-15T23:59:30+02:00")
    ids = await setup(hass, entry)
    client[1].reset_mock()
    freezer.move_to("2026-09-16T00:00:31+02:00")
    async_fire_time_changed(hass, datetime.now(UTC))
    await hass.async_block_till_done()
    assert hass.states.get(ids["score"]).state == "17"
    assert hass.states.get(ids["tomorrow"]).state == "33"
    assert hass.states.get(ids["forecast_days"]).state == "13"
    client[1].assert_not_awaited()


async def test_missing_today_is_unknown(hass, client, entry, forecast):
    client[1].return_value = replace(forecast, days=forecast.days[1:])
    ids = await setup(hass, entry)
    assert hass.states.get(ids["score"]).state == "unknown"
    assert hass.states.get(ids["tomorrow"]).state == "0"


async def test_unknown_category_preserved(hass, client, entry, forecast):
    client[1].return_value = replace(
        forecast, days=(replace(forecast.days[0], score=None, category=None, description="New"),)
    )
    ids = await setup(hass, entry)
    assert hass.states.get(ids["score"]).state == "unknown"
    assert hass.states.get(ids["peak"]).state == "unknown"
    assert hass.states.get(ids["category"]).state == "unknown"
    assert hass.states.get(ids["score"]).attributes["description"] == "New"


async def test_expiry_on_calendar_rollover(hass, client, entry, freezer):
    freezer.move_to("2026-09-28T23:59:30+02:00")
    ids = await setup(hass, entry)
    freezer.move_to("2026-09-29T00:00:31+02:00")
    async_fire_time_changed(hass, datetime.now(UTC))
    await hass.async_block_till_done()
    assert hass.states.get(ids["score"]).state == "unavailable"


async def test_multiple_locations_and_reload(hass, client, entry, location):
    await setup(hass, entry)
    other = replace(location, id="809", name="Borgo Val di Taro", slug="borgo+val+di+taro")
    second = MockConfigEntry(domain=DOMAIN, unique_id=other.id, data={"location": asdict(other)}, title=other.label)
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(second.entry_id)
    await hass.async_block_till_done()
    assert second.runtime_data is not entry.runtime_data
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert second.state is ConfigEntryState.LOADED
    assert entry.state is ConfigEntryState.LOADED


async def test_diagnostics_omit_location(hass, client, entry):
    await setup(hass, entry)
    module = import_module(f"{PACKAGE}.diagnostics")
    result = await module.async_get_config_entry_diagnostics(hass, entry)
    assert result["forecast_days"] == 15
    assert "Asiago" not in str(result)
    assert "376" not in str(result)


@pytest.mark.usefixtures("client")
async def test_card_static_path(hass, entry, hass_client):
    await setup(hass, entry)
    http = await hass_client()
    response = await http.get("/3bmeteo_funghi/3bmeteo-funghi-card.js")
    assert response.status == 200
    assert "threebmeteo-funghi-card" in await response.text()
