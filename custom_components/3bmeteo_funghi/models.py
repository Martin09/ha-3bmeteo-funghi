"""Immutable source models, independent of Home Assistant."""

from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import quote

from .const import BASE_URL, FORECAST_DAYS, FORECAST_PATH


@dataclass(frozen=True, slots=True)
class Location:
    """A locality returned by the mushroom-specific search."""

    id: str
    name: str
    slug: str
    province: str = ""
    region: str = ""

    @property
    def label(self) -> str:
        return " — ".join(part for part in (self.name, self.province, self.region) if part)

    @property
    def url(self) -> str:
        return f"{BASE_URL}{FORECAST_PATH}{quote(self.slug, safe='+')}"


@dataclass(frozen=True, slots=True)
class ForecastDay:
    """A dated forecast; unknown categories retain their source description."""

    date: date
    description: str
    category: str | None
    score: int | None

    def as_dict(self) -> dict:
        return {
            "date": self.date.isoformat(),
            "description": self.description,
            "category": self.category,
            "score": self.score,
        }


@dataclass(frozen=True, slots=True)
class Forecast:
    """One source response, with distinct publication and retrieval times."""

    days: tuple[ForecastDay, ...]
    published_at: datetime
    fetched_at: datetime

    def on(self, day: date) -> ForecastDay | None:
        return next((item for item in self.days if item.date == day), None)

    def upcoming(self, today: date) -> tuple[ForecastDay, ...]:
        return tuple(item for item in self.days if 0 <= (item.date - today).days < FORECAST_DAYS)

    def best(self, today: date) -> ForecastDay | None:
        return max(
            (item for item in self.upcoming(today) if item.score is not None),
            key=lambda item: item.score,
            default=None,
        )
