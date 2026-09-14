"""Shared integration constants and the documented ordinal score mapping."""

from datetime import timedelta
from zoneinfo import ZoneInfo

DOMAIN = "3bmeteo_funghi"
NAME = "3BMeteo Funghi"
BASE_URL = "https://www.3bmeteo.com"
SEARCH_PATH = "/search/search_funghi/"
FORECAST_PATH = "/meteo-funghi/"
ATTRIBUTION = "Forecast data provided by 3BMeteo"
SOURCE_TIMEZONE = ZoneInfo("Europe/Rome")
UPDATE_INTERVAL = timedelta(hours=6)
REQUEST_TIMEOUT = 30
MAX_RESPONSE_BYTES = 2_000_000
FORECAST_DAYS = 15
CONF_LOCATION = "location"
CONF_QUERY = "query"
CARD_URL = "/3bmeteo_funghi/3bmeteo-funghi-card.js"
CARD_FILE = "3bmeteo-funghi-card.js"

# Seven ordered levels in the provider's map legend. These are index points,
# not probabilities. Explicit aliases only: unknown labels must stay unknown.
CATEGORY_SCORES = {
    "absent": 0,
    "almost_absent": 17,
    "scarce": 33,
    "fair": 50,
    "good": 67,
    "excellent": 83,
    "exceptional": 100,
}
CATEGORY_ALIASES = {
    "assente": "absent",
    "quasi assente": "almost_absent",
    "quasi del tutto assente": "almost_absent",
    "scarsa": "scarce",
    "scarsa o localizzata": "scarce",
    "discreta": "fair",
    "buona": "good",
    "ottima": "excellent",
    "eccezionale": "exceptional",
}
MONTHS = {
    month: index
    for index, month in enumerate(
        (
            "gennaio",
            "febbraio",
            "marzo",
            "aprile",
            "maggio",
            "giugno",
            "luglio",
            "agosto",
            "settembre",
            "ottobre",
            "novembre",
            "dicembre",
        ),
        start=1,
    )
}
