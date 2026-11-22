"""Request and response shapes: GET /suggestions (datetimes in UTC, the UI converts them)
and "My week" under /me."""

from datetime import datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.suggestions import ContactSuggestion


class WindowOut(BaseModel):
    start: datetime
    end: datetime
    minutes: int


class OverdueOut(BaseModel):
    days_since: float | None  # None = never called
    ratio: float | None  # days since the last call / how often you want to call
    is_due: bool


class ContactSuggestionOut(BaseModel):
    contact_id: int
    name: str
    city: str
    time_zone: str
    country_code: str
    call_minutes: int
    overdue: OverdueOut
    windows: list[WindowOut]

    @classmethod
    def from_domain(cls, s: ContactSuggestion) -> "ContactSuggestionOut":
        return cls(
            contact_id=s.contact_id,
            name=s.name,
            city=s.city,
            time_zone=s.time_zone,
            country_code=s.country_code,
            call_minutes=s.call_minutes,
            overdue=OverdueOut(
                days_since=s.overdue.days_since, ratio=s.overdue.ratio, is_due=s.overdue.is_due
            ),
            windows=[WindowOut(start=w.start, end=w.end, minutes=w.minutes) for w in s.windows],
        )


class SuggestionsOut(BaseModel):
    generated_at: datetime
    days: int
    user_time_zone: str
    suggestions: list[ContactSuggestionOut]  # most overdue first


# "My week" (GET/PUT /me, POST/DELETE /me/busy). Times are local to the user's time zone.


class SettingsIn(BaseModel):
    time_zone: str = Field(description="IANA time zone, e.g. 'Europe/Madrid'")
    sleep_start: time
    sleep_end: time

    @field_validator("time_zone")
    @classmethod
    def time_zone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone: {value!r}") from exc
        return value


class BusyBlockIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    weekday: int = Field(ge=0, le=6, description="0 = Monday ... 6 = Sunday")
    start: time
    end: time
    label: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def end_after_start(self) -> "BusyBlockIn":
        if self.end <= self.start:
            raise ValueError("end must be after start (split a block that crosses midnight)")
        return self


class BusyBlockOut(BusyBlockIn):
    id: int


class ScheduleOut(BaseModel):
    time_zone: str
    sleep_start: time
    sleep_end: time
    busy: list[BusyBlockOut]
