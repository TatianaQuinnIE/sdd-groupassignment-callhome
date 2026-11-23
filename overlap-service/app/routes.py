"""HTTP endpoint for call suggestions."""

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.schedule import to_person
from app.schemas import ContactSuggestionOut, SuggestionsOut
from app.suggestions import build_suggestions

router = APIRouter(tags=["suggestions"])


def _countries(contacts: list[dict]) -> set[str]:
    return {
        str(c["country_code"]).upper()
        for c in contacts
        if isinstance(c, dict) and c.get("country_code")
    }


def _years(now, days: int) -> range:
    """Calendar years the period can touch, with a day of margin for time-zone differences."""
    return range((now - timedelta(days=1)).year, (now + timedelta(days=days + 1)).year + 1)


@router.get("/suggestions", response_model=SuggestionsOut)
def get_suggestions(request: Request, days: Annotated[int, Query(ge=1, le=14)] = 7):
    """Best call windows for each contact over the next `days` days, most overdue first.

    If contacts-service is down or too slow this raises ContactsUnavailable, which the app
    turns into a clear 503 (see create_app). If Nager.Date is down the windows are still
    returned, without holiday flags, and holidays_available is false.
    """
    state = request.app.state
    # The user's saved week ("My week"), so their busy times shape the windows.
    user = to_person(state.schedule.get_settings(), state.schedule.list_blocks())
    contacts = state.contacts.fetch_contacts()
    now = state.clock()
    holidays = state.holidays.lookup(_countries(contacts), _years(now, days))
    suggestions = build_suggestions(contacts, now, days, user, holidays.by_country)
    return SuggestionsOut(
        generated_at=now,
        days=days,
        user_time_zone=user.tz,
        suggestions=[ContactSuggestionOut.from_domain(s) for s in suggestions],
        holidays_available=holidays.available,
    )
