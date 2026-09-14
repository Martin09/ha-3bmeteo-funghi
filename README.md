# 3BMeteo Funghi for Home Assistant

[![Checks](https://github.com/Martin09/ha-3bmeteo-funghi/actions/workflows/ci.yaml/badge.svg)](https://github.com/Martin09/ha-3bmeteo-funghi/actions/workflows/ci.yaml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/Martin09/ha-3bmeteo-funghi/badges/.badge/coverage.json&cacheSeconds=3600)](https://github.com/Martin09/ha-3bmeteo-funghi/actions/workflows/ci.yaml)
[![Release](https://img.shields.io/github/v/release/Martin09/ha-3bmeteo-funghi)](https://github.com/Martin09/ha-3bmeteo-funghi/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://www.hacs.xyz/docs/use/)
[![hassfest](https://img.shields.io/badge/hassfest-validated-41BDF5.svg)](https://developers.home-assistant.io/docs/creating_integration_manifest/#validation)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-41BDF5.svg)](https://www.home-assistant.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Bring [3BMeteo's mushroom-fruiting forecast](https://www.3bmeteo.com/meteo-funghi)
into Home Assistant. UI setup, locality search, up to **15 dated forecast days**,
automation-friendly sensors, and an optional bundled forecast card.

This is an independent community integration, not an official 3BMeteo product.
The provider describes its forecasts as experimental. They estimate fruiting
conditions, not mushroom edibility or the probability of a successful outing.

## Installation

Requires **Home Assistant 2026.3+** and internet access to `www.3bmeteo.com`.

### HACS (recommended)

1. Open **HACS → ⋮ → Custom repositories**.
2. Add `https://github.com/Martin09/ha-3bmeteo-funghi` as **Integration**.
3. Download **3BMeteo Funghi**, then restart Home Assistant.
4. Open **Settings → Devices & services → Add integration → 3BMeteo Funghi**.
5. Enter at least three characters of an Italian hill/mountain locality, choose
   a search result, and wait for the forecast validation.

Repeat step 4 to monitor another locality. Duplicate localities are rejected
using 3BMeteo's stable locality ID. Search is restricted to the provider's
mushroom-supported localities; try a nearby locality if yours is not listed.
Setup is available in Italian and English.

All runtime files, including the card and local brand icon, ship in one HACS
integration download. No second repository, npm build, account, API key, or
YAML integration configuration is required.

### Manual installation

Copy `custom_components/3bmeteo_funghi/` into your Home Assistant
`config/custom_components/` directory, restart, and follow the UI setup above.

## Sensors

Each locality creates one service device with these sensors. Entity IDs are
assigned by Home Assistant; select them in the UI rather than assuming a name.

| Sensor | Value |
| --- | --- |
| Mushroom score | Today's normalized 0–100 index, plus the `forecast` attribute |
| Mushroom score tomorrow | Tomorrow's index |
| Mushroom presence | Stable enum: `absent`, `almost_absent`, `scarce`, `fair`, `good`, `excellent`, `exceptional` |
| Peak mushroom score | Highest known index in the remaining forecast window |
| Best mushroom day | Date of the highest known index; earliest date wins ties |
| Forecast days available | Remaining dated rows, including rows with an unknown category (diagnostic) |
| Forecast publication time | Provider's publication timestamp (diagnostic) |

The main score sensor also exposes `description` (original Italian text),
`location`, `source_url`, `published_at`, `fetched_at`, `score_min`, `score_max`,
and a `forecast` array. Each forecast row contains:

```json
{
  "date": "2026-09-17",
  "description": "Scarsa o Localizzata",
  "category": "scarce",
  "score": 33
}
```

Dates and “today/tomorrow” use **Europe/Rome**, independently of your Home
Assistant timezone. Yearless source dates are anchored to the provider's
publication date, including December–January transitions. Relative-day sensors
roll over within one minute of Rome midnight without a network request.

### Score mapping

The source publishes seven ordered qualitative levels. This integration maps
them to equally spaced, rounded **index points**. This scale is our normalization,
not a 3BMeteo percentage or a probability; sensors intentionally have no `%` unit
and no measurement state class.

| Original category | Stable category | Index |
| --- | --- | ---: |
| Assente | `absent` | 0 |
| Quasi del tutto assente / Quasi assente | `almost_absent` | 17 |
| Scarsa o Localizzata / Scarsa | `scarce` | 33 |
| Discreta | `fair` | 50 |
| Buona | `good` | 67 |
| Ottima | `excellent` | 83 |
| Eccezionale | `exceptional` | 100 |

Unrecognized descriptions are preserved, with `category: null` and `score: null`.
Missing dates are not filled or shifted. Today's missing/unknown value is
`unknown`, never zero. Peak/best-day sensors consider only known scores and may
therefore represent a partial forecast; inspect the array if completeness matters.

### Automations

Use the UI automation editor with a **Numeric state** trigger on “Mushroom
score”, above `66`, for good-or-better conditions. Use “Mushroom presence” for
category-based state triggers. A numeric-state trigger fires when crossing a
threshold, not at every update. For a daily reminder while conditions remain
good, use a daily time trigger plus a numeric-state condition instead.

## Optional Lovelace card

The integration serves the bundled JavaScript once it is loaded. Enable it once:

1. Enable **Advanced mode** in your Home Assistant user profile if needed.
2. Open **Settings → Dashboards → ⋮ → Resources → Add resource**.
3. URL: `/3bmeteo_funghi/3bmeteo-funghi-card.js?v=0.1.0`
4. Resource type: **JavaScript module**.
5. Reload the browser, edit a dashboard, and choose **3BMeteo Funghi** from the
   card picker. Its visual editor lets you select the main score sensor, title,
   and number of days (1–15).

The card has a horizontally scrollable forecast, keyboard access, HA theme
colors, Italian/English interface text, original provider descriptions, a source
link, and publication time. Clicking the heading opens entity details. It works
in Sections and Masonry dashboards and fetches no data directly from 3BMeteo.

For the dashboard's manual card editor, the configuration shape is:

```yaml
type: custom:threebmeteo-funghi-card
entity: sensor.replace_with_your_mushroom_score_entity
days: 15
name: Mushroom outlook
```

The example entity is a placeholder. The resource is opt-in and is not injected
into existing dashboards. For YAML-managed resources, register the same module
URL in your existing Lovelace resource configuration.

After an integration update, change the resource's version query if the browser
continues showing old code. If removing the integration, also remove its cards
and this resource from your dashboards.

## Updates and failure behavior

- One forecast request per locality every **six hours**, shared by all sensors.
- Setup validates the chosen forecast before saving; loading the entry performs
  its own first refresh. There is no speculative fetching for every search result.
- Requests have a 30-second timeout and a 2 MB response limit. HTML and JSON
  parsing run outside Home Assistant's event loop.
- HTTP errors, invalid responses, missing tables, and fully expired forecasts
  surface as coordinator update errors. Entities become unavailable on refresh
  failures and recover on successful refresh. HA retries initial setup failures.
- A shortened source forecast is accepted and its actual length is exposed.
  Data are never extrapolated to promise 15 days when fewer are published.
- The large forecast array and retrieval timestamp are excluded from Recorder
  history; the current array remains accessible to dashboards and automations.
- The integration uses public website endpoints, not a documented supported API.
  Provider changes or access restrictions can interrupt service.

### Troubleshooting

- **No locations:** use three or more characters; choose a supported Italian
  hill/mountain locality rather than an ordinary weather-only locality.
- **Cannot connect:** check outbound HTTPS access and retry later. HTTP 403/429
  can indicate provider access/rate restrictions; frequent manual reloads will
  not fix them.
- **Invalid response:** the forecast may be expired or the markup may have
  changed. Download diagnostics from the integration's menu and open an issue.
- **Unknown score:** check the original description. New source labels require
  a reviewed mapping rather than an assumed numeric value.
- **Card not found:** verify the integration loaded, the resource is a module,
  its URL is correct, and the browser was refreshed.

Diagnostics omit the selected locality and include publication time, number
of rows, update success, and unrecognized categories.

## Development

Python **3.14+**, managed exclusively with `uv`:

```sh
uv sync
uv run prek install
uv run pytest tests/
uv run ruff check .
uv run ruff format --check .
uv run prek run --all-files
```

Tests mock 3BMeteo and cover parsing, dates, failures, config flow, lifecycle,
sensor state, and metadata. The fixture is a minimized representation of the
public September 2026 forecast markup, without advertisements or tracking.
The card is plain JavaScript with no runtime dependencies or build step.
Optional real-browser tests cover mobile/desktop overflow, safe text rendering,
unknown/unavailable states, card configuration, and the visual editor:

```sh
uv sync --group browser
uv run --group browser playwright install chromium
uv run --group browser pytest tests/
```

Without the `browser` group, these tests are skipped. CI installs Chromium and
runs both the integration and browser suites.

The checked-in test-helper release currently pins Home Assistant 2026.2.3;
this tests the integration APIs but does not validate 2026.3+ local brand serving.
CI also runs the current Home Assistant **hassfest** and HACS validators. Keep
the test-helper lock current as newer compatible releases become available.

### Architecture

- `api.py`: bounded HTTP, location and HTML parsers, typed source errors.
- `models.py`: immutable locality/forecast objects, independent of HA.
- `coordinator.py`: shared polling and calendar rollover notifications.
- `config_flow.py`: validated search/selection and duplicate prevention.
- `sensor.py`: translated, stable-ID sensors using `entry.runtime_data`.
- `card/`: optional frontend module and visual editor.
- `const.py`: endpoints, limits, timezone, and the explicit category map.

### Releasing

1. Run all checks and review CI's hassfest/HACS results.
2. Update `manifest.json`, `pyproject.toml`, and the card resource example version;
   run `uv lock` and commit `uv.lock`.
3. Publish a tagged GitHub release with release notes. HACS downloads the
   integration directory directly; no generated ZIP is required.

Custom-repository installation does not imply inclusion in HACS's default
catalog. Default catalog submission is a separate maintainer task.

## Attribution and license

Forecast data and category labels belong to **3BMeteo**. Refer to the provider's
[conditions of use](https://www.3bmeteo.com/condizioni-utilizzo/it) for data usage.
Integration code and its original mushroom illustration are licensed under
[MIT](LICENSE).
