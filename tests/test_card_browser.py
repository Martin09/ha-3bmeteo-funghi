"""Optional real-browser card tests: uv run --group browser pytest tests/."""

from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.async_api", reason="Install the optional browser dependency group")
CARD = Path(__file__).resolve().parents[1] / "custom_components/3bmeteo_funghi/card/3bmeteo-funghi-card.js"


@pytest.fixture
async def page():
    async with playwright.async_playwright() as driver:
        browser = await driver.chromium.launch()
        page = await browser.new_page()
        await page.route("**/*", lambda route: route.abort())
        await page.set_content("""<style>
            body { margin: 16px; --primary-text-color: #222; --secondary-text-color: #555;
                --primary-color: #176c48; --divider-color: #ccc; --card-background-color: white; }
            ha-card { display: block; border-radius: 16px; background: white; }
            </style><threebmeteo-funghi-card></threebmeteo-funghi-card>""")
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.add_script_tag(content=CARD.read_text())
        yield page
        assert not errors
        await browser.close()


async def configure(page, days=15, state="33", language="en"):
    await page.evaluate(
        """({days, state, language}) => {
        window.card = document.querySelector('threebmeteo-funghi-card');
        const forecast = Array.from({length: 15}, (_, i) => ({
            date: `2026-09-${String(14+i).padStart(2, '0')}`,
            score: i === 0 ? 0 : i === 1 ? null : 67,
            description: i === 1 ? '<img src=x onerror=alert(1)>' : 'Buona',
        }));
        window.mockHass = {language, states: {'sensor.test': {state, attributes: {
            forecast, location: 'Asiago', score_max: 100,
            source_url: 'javascript:alert(1)', published_at: '2026-09-14T13:00:13+02:00',
        }}}};
        card.setConfig({entity: 'sensor.test', days});
        card.hass = mockHass;
    }""",
        {"days": days, "state": state, "language": language},
    )


@pytest.mark.parametrize("width", [360, 1000])
async def test_forecast_responsive_and_safe(page, width, tmp_path):
    await page.set_viewport_size({"width": width, "height": 600})
    await configure(page)
    assert await page.locator(".day").count() == 15
    assert await page.locator(".score").first.text_content() == "0"
    assert await page.locator(".score").nth(1).text_content() == "—"
    assert await page.locator("img").count() == 0
    assert await page.locator("a").get_attribute("href") == "https://www.3bmeteo.com/meteo-funghi"
    assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert await page.locator(".forecast").evaluate("el => el.scrollWidth > el.clientWidth")
    await page.locator(".forecast").focus()
    assert await page.locator(".forecast").evaluate("el => el.getRootNode().activeElement === el")
    await page.evaluate("card.addEventListener('hass-more-info', event => window.moreInfo = event.detail)")
    await page.locator("button").click()
    assert await page.evaluate("window.moreInfo.entityId") == "sensor.test"
    await page.screenshot(path=str(tmp_path / f"card-{width}.png"))


async def test_config_updates_and_unavailable(page):
    await configure(page)
    await page.evaluate("card.setConfig({entity: 'sensor.test', days: 3, name: 'Test'})")
    assert await page.locator(".day").count() == 3
    assert await page.locator("button").text_content() == "Test"
    await configure(page, state="unknown")
    assert await page.locator(".day").count() == 15
    await configure(page, state="unavailable", language="it")
    assert await page.locator(".day").count() == 0
    assert "Previsioni non disponibili" in await page.locator("ha-card").text_content()
    await page.evaluate("card.hass = {language: 'en', states: {}}")
    assert "Select a mushroom score entity" in await page.locator("ha-card").text_content()


async def test_visual_editor_and_validation(page):
    await configure(page)
    await page.evaluate("""() => {
        const klass = customElements.get('threebmeteo-funghi-card');
        window.editor = klass.getConfigElement();
        editor.setConfig({type: 'custom:threebmeteo-funghi-card', entity: 'sensor.test'});
        editor.hass = mockHass;
        editor.addEventListener('config-changed', event => window.changed = event.detail.config);
        document.body.append(editor);
    }""")
    await page.locator("input[type=number]").fill("7")
    await page.locator("input[type=number]").dispatch_event("change")
    assert await page.evaluate("window.changed.days") == 7
    assert await page.evaluate("window.changed.entity") == "sensor.test"
    for days in [0, 16, 1.5, "5"]:
        assert await page.evaluate(
            """days => {
            try { card.setConfig({entity: 'sensor.test', days}); return false; }
            catch { return true; }
        }""",
            days,
        )
