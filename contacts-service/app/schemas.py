"""Request and response shapes for the API, with validation."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContactIn(BaseModel):
    """What the UI sends to create or update a contact."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    city: str = Field(min_length=1, max_length=100)
    time_zone: str = Field(description="IANA time zone, e.g. 'Asia/Seoul'")
    country_code: str = Field(pattern=r"^[A-Za-z]{2}$", description="ISO country code, e.g. 'KR'")
    sleep_start: time = time(23, 0)
    sleep_end: time = time(7, 0)
    call_minutes: int = Field(default=30, ge=5, le=240)
    call_every_days: int = Field(default=7, ge=1, le=365)

    @field_validator("time_zone")
    @classmethod
    def time_zone_exists(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"unknown time zone: {value!r}") from exc
        return value

    @field_validator("country_code")
    @classmethod
    def upper_case(cls, value: str) -> str:
        return value.upper()


class ContactOut(ContactIn):
    """What the API returns for a contact."""

    id: int
    created_at: datetime
    updated_at: datetime
    last_called: datetime | None = None


class CallIn(BaseModel):
    """A call you made. called_at defaults to now; times without a zone are read as UTC."""

    model_config = ConfigDict(str_strip_whitespace=True)

    called_at: datetime | None = None
    minutes: int | None = Field(default=None, ge=1, le=600)
    note: str | None = Field(default=None, max_length=500)

    @field_validator("called_at")
    @classmethod
    def utc_and_not_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        value = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        if value > datetime.now(UTC):
            raise ValueError("called_at cannot be in the future")
        return value


class CallOut(BaseModel):
    id: int
    contact_id: int
    called_at: datetime
    minutes: int | None
    note: str | None
