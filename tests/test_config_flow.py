"""Exercise the real config-flow manager with mocked upstream responses."""

from importlib import import_module
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType

from .conftest import DOMAIN, PACKAGE, api


async def test_search_choose_create(hass, client, location):
    with patch.object(import_module(PACKAGE), "async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "Asiago"})
        assert result["step_id"] == "location"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"location": "376"})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"]["location"]["slug"] == "asiago"
        assert result["result"].unique_id == "376"
        assert result["title"] == location.label
        await hass.async_block_till_done()


async def test_duplicate(hass, client, entry):
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"query": "asiago"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"location": "376"})
    assert result["reason"] == "already_configured"
    client[1].assert_not_awaited()


@pytest.mark.parametrize(
    ("failure", "error"), [(api.CannotConnect(), "cannot_connect"), (api.SourceError(), "invalid_response")]
)
async def test_search_failures(hass, client, failure, error):
    client[0].side_effect = failure
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"query": "asiago"})
    assert result["errors"] == {"base": error}


async def test_no_results_and_short_query(hass, client):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"query": " a "})
    assert result["errors"] == {"query": "query_too_short"}
    client[0].assert_not_awaited()
    client[0].return_value = []
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"query": "missing"})
    assert result["errors"] == {"base": "no_locations"}


@pytest.mark.parametrize(
    ("failure", "error"), [(api.CannotConnect(), "cannot_connect"), (api.SourceError(), "invalid_response")]
)
async def test_forecast_validation_retry(hass, client, failure, error, forecast):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"}, data={"query": "asiago"})
    client[1].side_effect = failure
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"location": "376"})
    assert result["errors"] == {"base": error}
    assert result["step_id"] == "location"
    client[1].side_effect = None
    client[1].return_value = forecast
    with patch.object(import_module(PACKAGE), "async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {"location": "376"})
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
