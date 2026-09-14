"""Bounded asynchronous transport and defensive parsers for public pages."""

import asyncio
import json
import re
from datetime import date, datetime, timedelta
from urllib.parse import quote

from aiohttp import ClientError, ClientSession
from bs4 import BeautifulSoup

from .const import (
    BASE_URL,
    CATEGORY_ALIASES,
    CATEGORY_SCORES,
    FORECAST_DAYS,
    MAX_RESPONSE_BYTES,
    MONTHS,
    REQUEST_TIMEOUT,
    SEARCH_PATH,
    SOURCE_TIMEZONE,
)
from .models import Forecast, ForecastDay, Location


class SourceError(Exception):
    """The upstream response cannot be used safely."""


class CannotConnect(SourceError):
    """The upstream service could not be reached."""


def parse_locations(payload: object) -> list[Location]:
    """Validate search records and deduplicate using the provider's stable ID."""
    if not isinstance(payload, list):
        raise SourceError("Unexpected location search response")
    locations: dict[str, Location] = {}
    for row in payload:
        if not isinstance(row, dict):
            continue
        identifier = row.get("id_localita")
        name, slug = row.get("nome_loc"), row.get("canonical")
        if (
            isinstance(identifier, bool)
            or not str(identifier).isdigit()
            or not isinstance(name, str)
            or not name.strip()
            or not isinstance(slug, str)
            or not re.fullmatch(r"[\w+'-]+", slug)
        ):
            continue
        locations[str(identifier)] = Location(
            str(identifier),
            name.strip(),
            slug,
            str(row.get("prov") or ""),
            str(row.get("regione") or ""),
        )
    if payload and not locations:
        raise SourceError("No valid records in location search response")
    return list(locations.values())[:50]


def _parse_day(text: str, anchor: date) -> date | None:
    """Resolve yearless Italian dates against publication, never fetch time."""
    match = re.fullmatch(r"(\d{1,2})\s+([a-z]+)(?:\s+(\d{4}))?", text.casefold())
    if not match or match[2] not in MONTHS:
        return None
    years = [int(match[3])] if match[3] else [anchor.year - 1, anchor.year, anchor.year + 1]
    for year in years:
        try:
            candidate = date(year, MONTHS[match[2]], int(match[1]))
        except ValueError:
            continue
        if 0 <= (candidate - anchor).days < FORECAST_DAYS:
            return candidate
    return None


def parse_forecast(html: str, fetched_at: datetime) -> Forecast:
    """Parse only the mushroom table, tolerating presentation-only changes."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    match = re.search(r"Aggiornamento:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", text)
    if not match:
        raise SourceError("Missing forecast publication time")
    try:
        published = datetime.fromisoformat(match[1]).replace(tzinfo=SOURCE_TIMEZONE)
    except ValueError as err:
        raise SourceError("Invalid forecast publication time") from err
    if published > fetched_at + timedelta(hours=1):
        raise SourceError("Forecast publication time is in the future")
    table = next(
        (
            node
            for node in soup.select(".table-container, table")
            if "Presenza funghi" in node.get_text(" ", strip=True)
        ),
        None,
    )
    if table is None:
        raise SourceError("Mushroom forecast table not found")
    days: dict[date, ForecastDay] = {}
    for row in table.select(".table-row--data, tr"):
        cells = row.select(".table-cell, td")
        if len(cells) != 2:
            continue
        day = _parse_day(" ".join(cells[0].stripped_strings), published.date())
        description = " ".join(cells[1].stripped_strings)
        if day is None or not description:
            continue
        category = CATEGORY_ALIASES.get(" ".join(description.casefold().split()))
        item = ForecastDay(day, description, category, CATEGORY_SCORES.get(category))
        if day in days and days[day] != item:
            raise SourceError("Conflicting forecasts for the same date")
        days[day] = item
    today = fetched_at.astimezone(SOURCE_TIMEZONE).date()
    if not any(day >= today for day in days):
        raise SourceError("Forecast is empty or expired")
    return Forecast(tuple(days[day] for day in sorted(days)), published, fetched_at)


class MushroomClient:
    """Use Home Assistant's session; parsing runs outside the event loop."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session

    async def _get(self, url: str) -> str:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; HA-3BMeteo-Funghi/0.1)", "Accept-Language": "it"},
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise CannotConnect(f"3BMeteo returned HTTP {response.status}")
                    body = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise SourceError("Response exceeds size limit")
                    return body.decode("utf-8")
        except (ClientError, TimeoutError) as err:
            raise CannotConnect("Unable to reach 3BMeteo") from err
        except UnicodeError as err:
            raise SourceError("Invalid response encoding") from err

    async def search(self, query: str) -> list[Location]:
        query = query.strip().lower().translate(str.maketrans({"ò": "o'", "à": "a'", "è": "e'", "ì": "i'", "ù": "u'"}))
        raw = await self._get(f"{BASE_URL}{SEARCH_PATH}{quote(query, safe='')}")
        try:
            return await asyncio.to_thread(lambda: parse_locations(json.loads(raw)))
        except ValueError as err:
            raise SourceError("Invalid search JSON") from err

    async def forecast(self, location: Location) -> Forecast:
        html = await self._get(location.url)
        return await asyncio.to_thread(parse_forecast, html, datetime.now(SOURCE_TIMEZONE))
