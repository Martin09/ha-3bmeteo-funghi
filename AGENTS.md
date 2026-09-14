# AGENTS.md

## Project

HACS-compatible Home Assistant custom integration for 3BMeteo mushroom forecasts, with an optional bundled Lovelace card.

- Python >= 3.14, managed exclusively with `uv`.
- Integration: `custom_components/3bmeteo_funghi/`
- Card: `custom_components/3bmeteo_funghi/card/`
- Tests: `tests/`

## Initial Setup

Run `uv sync`, then `uv run prek install`.

## Checks

```bash
uv run pytest tests/
uv run ruff check .
uv run ruff format --check .
uv run prek run --all-files
```

## Rules

- Follow current Home Assistant config-entry patterns; use `entry.runtime_data` and a `DataUpdateCoordinator`.
- Never block Home Assistant's event loop; use async APIs or `hass.async_add_executor_job`.
- Use translated entity names, `has_entity_name = True`, and `strings.json` mirrored under `translations/`.
- Keep shared constants, endpoints, defaults, and keys in `const.py`.
- Keep the card framework-free and build-step-free; never hardcode entity IDs.
- Mock 3BMeteo in tests; never call the live service.
- Make scraping tolerant of missing or changed markup; surface failures through coordinator update errors.
- Add tests for behavior changes and keep `README.md` in sync.
- Commit `uv.lock`; do not commit credentials or local Home Assistant config.
- Use Conventional Commits and never skip hooks unless explicitly requested.
