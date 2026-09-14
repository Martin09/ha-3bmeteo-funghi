"""Offline fixtures and a frozen source-local calendar."""

from dataclasses import asdict
from datetime import datetime
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "3bmeteo_funghi"
PACKAGE = f"custom_components.{DOMAIN}"
api = import_module(f"{PACKAGE}.api")
models = import_module(f"{PACKAGE}.models")


@pytest.fixture(autouse=True)
def enable_integration(enable_custom_integrations, freezer):
    freezer.move_to("2026-09-14T14:00:00+02:00")


@pytest.fixture
def html():
    return (Path(__file__).parent / "fixtures/forecast.html").read_text()


@pytest.fixture
def forecast(html):
    return api.parse_forecast(html, datetime.fromisoformat("2026-09-14T14:00:00+02:00"))


@pytest.fixture
def location():
    return models.Location("376", "Asiago", "asiago", "VI", "Veneto")


@pytest.fixture
def entry(location):
    return MockConfigEntry(
        domain=DOMAIN, unique_id=location.id, title=location.label, data={"location": asdict(location)}
    )


@pytest.fixture
def client(location, forecast):
    with (
        patch.object(api.MushroomClient, "search", new_callable=AsyncMock, return_value=[location]) as search,
        patch.object(api.MushroomClient, "forecast", new_callable=AsyncMock, return_value=forecast) as fetch,
    ):
        yield search, fetch
