"""Parser regressions and mocked transport failures. Never contact 3BMeteo."""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientError

from .conftest import api

NOW = datetime.fromisoformat("2026-09-14T14:00:00+02:00")


def table(rows, published="2026-12-31 13:00:00"):
    return (
        f"<p>Aggiornamento: {published}</p><table><tr><th>Giorno</th><th>Presenza funghi</th></tr>"
        + "".join(f"<tr><td>{day}</td><td>{description}</td></tr>" for day, description in rows)
        + "</table>"
    )


def test_live_markup_shape(forecast):
    assert len(forecast.days) == 15
    assert forecast.days[0].date == date(2026, 9, 14)
    assert forecast.days[-1].date == date(2026, 9, 28)
    assert forecast.days[2].score == 17
    assert forecast.days[3].score == 33
    assert forecast.best(date(2026, 9, 14)).date == date(2026, 9, 17)
    assert forecast.published_at.isoformat() == "2026-09-14T13:00:13+02:00"


@pytest.mark.parametrize(
    ("label", "score"),
    [
        ("Assente", 0),
        ("Quasi assente", 17),
        ("Scarsa", 33),
        ("Discreta", 50),
        ("Buona", 67),
        ("Ottima", 83),
        ("Eccezionale", 100),
        ("  SCARSA&nbsp;o <b>Localizzata</b> ", 33),
        ("Nuova categoria", None),
    ],
)
def test_category_mapping(label, score):
    result = api.parse_forecast(table([("14 settembre", label)], "2026-09-14 13:00:00"), NOW)
    assert result.days[0].score == score
    assert bool(result.days[0].category) == (score is not None)


def test_year_rollover_and_missing_days():
    result = api.parse_forecast(
        table([("31 dicembre", "Buona"), ("2 gennaio", "Ottima"), ("31 febbraio", "Buona")]),
        datetime.fromisoformat("2027-01-01T10:00:00+01:00"),
    )
    assert [day.date for day in result.days] == [date(2026, 12, 31), date(2027, 1, 2)]
    assert result.on(date(2027, 1, 1)) is None
    assert len(result.upcoming(date(2027, 1, 1))) == 1


def test_leap_day():
    result = api.parse_forecast(
        table([("29 febbraio", "Buona")], "2028-02-28 13:00:00"), datetime.fromisoformat("2028-02-28T14:00:00+01:00")
    )
    assert result.days[0].date == date(2028, 2, 29)


@pytest.mark.parametrize(
    "html",
    [
        "<html>Maintenance</html>",
        "Aggiornamento: 2026-09-14 13:00:00 <table>Unrelated data</table>",
        table([], "2026-09-14 13:00:00"),
        table([("31 agosto", "Buona")], "2026-08-31 13:00:00"),
        table([("14 settembre", "Buona")], "2026-99-14 13:00:00"),
        table([("14 settembre", "Buona")], "2027-09-14 13:00:00"),
        table([("14 settembre", "Buona"), ("14 settembre", "Assente")], "2026-09-14 13:00:00"),
    ],
)
def test_invalid_forecasts_fail_explicitly(html):
    with pytest.raises(api.SourceError):
        api.parse_forecast(html, NOW)


def test_duplicate_rows_and_unknown_labels():
    result = api.parse_forecast(table([("14 settembre", "New"), ("14 settembre", "New")], "2026-09-14 13:00:00"), NOW)
    assert len(result.days) == 1
    assert result.days[0].as_dict() == {"date": "2026-09-14", "description": "New", "category": None, "score": None}
    assert result.best(date(2026, 9, 14)) is None


def test_locations_are_validated_and_deduplicated():
    row = {"id_localita": 376, "nome_loc": "Asiago", "canonical": "asiago", "prov": "VI", "regione": "Veneto"}
    locations = api.parse_locations([row, row, {}, None, {**row, "canonical": "../../evil"}])
    assert len(locations) == 1
    assert locations[0].label == "Asiago — VI — Veneto"
    assert locations[0].url == "https://www.3bmeteo.com/meteo-funghi/asiago"
    assert api.parse_locations([]) == []
    for invalid in ({}, [{"id_localita": True}], [None]):
        with pytest.raises(api.SourceError):
            api.parse_locations(invalid)


def session_for(body=b"[]", status=200):
    async def chunks(size):
        yield body

    response = MagicMock(status=status)
    response.content.iter_chunked = chunks
    session = MagicMock()
    session.get.return_value.__aenter__ = AsyncMock(return_value=response)
    return session


def routed_session(routes: dict[str, tuple[int, bytes]]):
    """Stub session replying per queried prefix, mimicking the upstream index quirks."""

    class Context:
        def __init__(self, status, body):
            self.status, self.body = status, body

        async def __aenter__(self):
            async def chunks(_size):
                yield self.body

            response = MagicMock(status=self.status)
            response.content.iter_chunked = chunks
            return response

        async def __aexit__(self, *_args):
            return False

    session = MagicMock()
    session.calls = []

    def get(url, **_kwargs):
        key = url.rsplit("/", 1)[-1].lower()
        session.calls.append(key)
        status, body = routes.get(key, (200, b""))
        return Context(status, body)

    session.get.side_effect = get
    return session


def record(identifier, name, slug, region):
    return {
        "id_localita": identifier,
        "nome_loc": name,
        "canonical": slug,
        "tipo": "M",
        "prov": "VI",
        "regione": region,
    }


CIVIASCO = record(2155, "Civiasco", "civiasco", "Piemonte")
CIVITA = record(2159, "Civita", "civita", "Calabria")
CIVAGO = record(978, "Civago", "civago", "Emilia Romagna")


async def test_search_transport():
    body = json.dumps([record(1, "Forli'", "forli", "Emilia Romagna")]).encode()
    session = session_for(body)
    result = await api.MushroomClient(session).search(" Forlì ")
    assert [loc.name for loc in result] == ["Forli'"]
    call = session.get.call_args
    assert call.args[0].endswith("/forli%27")
    assert call.kwargs["allow_redirects"] is False
    assert session.get.call_count == 1


async def test_full_name_falls_back_to_prefix():
    session = routed_session(
        {
            "civiasco": (200, b""),
            "civiasc": (200, b"\n"),
            "civias": (200, b"   "),
            "civia": (200, b""),
            "civ": (200, json.dumps([CIVAGO, {}, None, CIVITA, CIVIASCO]).encode()),
        }
    )
    result = await api.MushroomClient(session).search("Civiasco")
    assert [loc.name for loc in result] == ["Civiasco"]
    assert session.calls == ["civiasco", "civiasc", "civias", "civia", "civi", "civ"]


async def test_fallback_drops_records_without_filter_match():
    session = routed_session({"xcvit": (200, json.dumps([CIVITA, CIVAGO]).encode())})
    assert await api.MushroomClient(session).search("xcvita") == []


async def test_multi_token_fallback_with_apostrophe():
    session = routed_session(
        {
            "civita": (
                200,
                json.dumps([CIVITA, record(2161, "Civita d'Antino", "civita+dantino", "Abruzzo"), CIVAGO]).encode(),
            ),
        }
    )
    result = await api.MushroomClient(session).search("Civita d'Antino")
    assert [loc.name for loc in result] == ["Civita d'Antino"]


async def test_three_char_query_makes_no_fallback_calls():
    session = routed_session({"xyz": (200, b"")})
    assert await api.MushroomClient(session).search(" xyz ") == []
    assert session.calls == ["xyz"]


async def test_empty_exact_json_list_then_shorter_prefix():
    session = routed_session(
        {"asiago": (200, b"[]"), "asiag": (200, json.dumps([record(376, "Asiago", "asiago", "Veneto")]).encode())}
    )
    result = await api.MushroomClient(session).search("asiago")
    assert [loc.name for loc in result] == ["Asiago"]
    assert session.calls == ["asiago", "asiag"]


async def test_fallback_json_error_propagates():
    session = routed_session({"asiago": (200, b""), "asiag": (200, b"not json")})
    with pytest.raises(api.SourceError):
        await api.MushroomClient(session).search("asiago")


async def test_forecast_transport(location, html):
    forecast = await api.MushroomClient(session_for(html.encode())).forecast(location)
    assert len(forecast.days) == 15


@pytest.mark.parametrize("status", [301, 403, 404, 429, 500])
async def test_http_errors(status):
    with pytest.raises(api.CannotConnect, match=str(status)):
        await api.MushroomClient(session_for(status=status)).search("Asiago")


@pytest.mark.parametrize("body", [b"not json", b"\xff", b"x" * 2_000_001])
async def test_bad_responses(body):
    with pytest.raises(api.SourceError):
        await api.MushroomClient(session_for(body)).search("Asiago")


@pytest.mark.parametrize("error", [ClientError(), TimeoutError()])
async def test_network_errors(error):
    session = session_for()
    session.get.side_effect = error
    with pytest.raises(api.CannotConnect):
        await api.MushroomClient(session).search("Asiago")
