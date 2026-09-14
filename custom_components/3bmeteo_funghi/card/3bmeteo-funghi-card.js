/* Framework-free Lovelace card. Source strings are always rendered as text. */
const TEXT = {
  en: {
    title: "Mushroom forecast", missing: "Select a mushroom score entity.",
    unavailable: "Forecast unavailable", empty: "No forecast days available",
    index: "Index / 100 · not a probability", published: "Published",
    entity: "Forecast entity", name: "Title", days: "Days (1–15)",
  },
  it: {
    title: "Previsioni funghi", missing: "Seleziona un sensore indice funghi.",
    unavailable: "Previsioni non disponibili", empty: "Nessun giorno di previsione disponibile",
    index: "Indice / 100 · non è una probabilità", published: "Pubblicazione",
    entity: "Entità previsioni", name: "Titolo", days: "Giorni (1–15)",
  },
};
const language = (hass) => hass?.language?.startsWith("it") ? "it" : "en";
const node = (tag, text, className) => {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
};
const forecastEntities = (hass) => Object.keys(hass?.states || {}).filter(
  (id) => id.startsWith("sensor.") && Array.isArray(hass.states[id].attributes.forecast)
    && hass.states[id].attributes.score_max === 100,
);
const validScore = (score) => typeof score === "number" && Number.isFinite(score) && score >= 0 && score <= 100;

class MushroomForecastCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  static getConfigElement() { return document.createElement("threebmeteo-funghi-editor"); }
  static getStubConfig(hass) {
    return { entity: forecastEntities(hass)[0] || "", days: 15 };
  }

  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("sensor.")) throw new Error("Select a sensor entity");
    const days = config.days ?? 15;
    if (!Number.isInteger(days) || days < 1 || days > 15) throw new Error("days must be an integer from 1 to 15");
    this._config = { ...config, days };
    this._state = undefined;
    this._render();
  }

  set hass(hass) {
    const state = hass.states[this._config?.entity];
    const locale = hass.language;
    this._hass = hass;
    if (state === this._state && locale === this._locale) return;
    this._state = state;
    this._locale = locale;
    this._render();
  }

  getCardSize() { return 5; }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }

  _render() {
    if (!this._config || !this._hass) return;
    const lang = language(this._hass);
    const text = TEXT[lang];
    const state = this._hass.states[this._config.entity];
    const attrs = state?.attributes || {};
    const style = node("style", `
      ha-card { padding: 20px; color: var(--primary-text-color); }
      h2 { margin: 0; font-size: 1.25rem; font-weight: 500; }
      .meta { color: var(--secondary-text-color); font-size: .8rem; margin: 8px 0 16px; }
      .forecast { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 12px; }
      .day { flex: 0 0 100px; padding: 12px 8px; border: 1px solid var(--divider-color); border-radius: 12px; text-align: center; }
      .score { font-size: 1.6rem; font-weight: 600; margin: 12px 0; }
      .description { font-size: .8rem; margin-top: 10px; }
      meter { width: 90%; height: 10px; }
      button { color: inherit; background: transparent; border: 0; padding: 0; cursor: pointer; text-align: left; font: inherit; }
      button:focus-visible, a:focus-visible, .forecast:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 3px; }
      a { color: var(--primary-color); } footer { font-size: .8rem; margin-top: 12px; }
    `);
    const card = node("ha-card");
    const heading = node("h2");
    const more = node("button", this._config.name || attrs.location || text.title);
    more.addEventListener("click", () => this.dispatchEvent(new CustomEvent("hass-more-info", {
      detail: { entityId: this._config.entity }, bubbles: true, composed: true,
    })));
    heading.append(more);
    card.append(heading, node("p", text.index, "meta"));
    if (!state) card.append(node("p", text.missing));
    else if (state.state === "unavailable") card.append(node("p", text.unavailable));
    else {
      const items = Array.isArray(attrs.forecast) ? attrs.forecast.slice(0, this._config.days) : [];
      const list = node("div", undefined, "forecast");
      list.setAttribute("role", "list");
      list.setAttribute("aria-label", text.title);
      list.tabIndex = 0;
      for (const day of items) {
        if (!day || !/^\d{4}-\d{2}-\d{2}$/.test(day.date)) continue;
        const date = new Date(`${day.date}T12:00:00Z`);
        if (Number.isNaN(date.getTime())) continue;
        const item = node("div", undefined, "day");
        item.setAttribute("role", "listitem");
        const time = node("time", new Intl.DateTimeFormat(lang, {
          weekday: "short", day: "numeric", month: "short", timeZone: "UTC",
        }).format(date));
        time.dateTime = day.date;
        item.append(time, node("div", validScore(day.score) ? String(day.score) : "—", "score"));
        if (validScore(day.score)) {
          const meter = node("meter");
          meter.min = 0;
          meter.max = 100;
          meter.value = day.score;
          meter.setAttribute("aria-label", `${time.textContent}: ${day.score}/100`);
          item.append(meter);
        }
        item.append(node("div", day.description || "—", "description"));
        list.append(item);
      }
      card.append(list.childElementCount ? list : node("p", text.empty));
    }
    const footer = node("footer");
    const link = node("a", "3BMeteo");
    link.href = "https://www.3bmeteo.com/meteo-funghi";
    try {
      const url = new URL(attrs.source_url);
      if (url.origin === "https://www.3bmeteo.com" && url.pathname.startsWith("/meteo-funghi/")) link.href = url.href;
    } catch { /* Keep the fixed provider link. */ }
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    footer.append(link);
    if (attrs.published_at) {
      const published = new Date(attrs.published_at);
      if (!Number.isNaN(published.getTime())) footer.append(node("span", ` · ${text.published}: ${published.toLocaleString(lang)}`));
    }
    card.append(footer);
    this.shadowRoot.replaceChildren(style, card);
  }
}

class MushroomForecastEditor extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); }
  setConfig(config) { this._config = { ...config }; this._render(); }
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (first) this._render();
  }
  _render() {
    if (!this._config || !this._hass) return;
    const text = TEXT[language(this._hass)];
    const fields = node("div");
    for (const [key, label] of [["entity", text.entity], ["name", text.name], ["days", text.days]]) {
      const wrapper = node("label", label);
      const input = node(key === "entity" ? "select" : "input");
      if (key === "entity") {
        const entities = new Set(["", ...forecastEntities(this._hass), this._config.entity].filter((id) => id !== undefined));
        for (const id of entities) {
          const option = node("option", this._hass.states[id]?.attributes.friendly_name || id || "—");
          option.value = id;
          input.append(option);
        }
      } else if (key === "days") { input.type = "number"; input.min = 1; input.max = 15; }
      input.value = this._config[key] ?? (key === "days" ? 15 : "");
      input.addEventListener("change", () => {
        if (key === "days" && (!input.checkValidity() || !Number.isInteger(Number(input.value)))) return;
        this._config = { ...this._config, [key]: key === "days" ? Number(input.value) : input.value };
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
      });
      wrapper.append(input);
      fields.append(wrapper);
    }
    this.shadowRoot.replaceChildren(node("style", `
      label { display: block; margin: 16px 0; color: var(--primary-text-color); }
      input, select { box-sizing: border-box; display: block; width: 100%; margin-top: 8px; padding: 10px;
        color: var(--primary-text-color); background: var(--card-background-color); border: 1px solid var(--divider-color); }
    `), fields);
  }
}

if (!customElements.get("threebmeteo-funghi-card")) customElements.define("threebmeteo-funghi-card", MushroomForecastCard);
if (!customElements.get("threebmeteo-funghi-editor")) customElements.define("threebmeteo-funghi-editor", MushroomForecastEditor);
window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "threebmeteo-funghi-card")) window.customCards.push({
  type: "threebmeteo-funghi-card", name: "3BMeteo Funghi", preview: true,
  description: "15-day mushroom-fruiting forecast · Previsioni crescita funghi",
});
