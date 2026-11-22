"""Response shapes for GET /suggestions. All datetimes are UTC; the UI converts for display."""

from datetime import datetime

from pydantic import BaseModel

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
