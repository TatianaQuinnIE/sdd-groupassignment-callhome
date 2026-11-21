"""HTTP endpoint for call suggestions."""

from typing import Annotated

from fastapi import APIRouter, Query, Request

from app.schemas import ContactSuggestionOut, SuggestionsOut
from app.suggestions import build_suggestions

router = APIRouter(tags=["suggestions"])


@router.get("/suggestions", response_model=SuggestionsOut)
def get_suggestions(request: Request, days: Annotated[int, Query(ge=1, le=14)] = 7):
    """Best call windows for each contact over the next `days` days, most overdue first.

    If contacts-service is down or too slow this raises ContactsUnavailable, which the app
    turns into a clear 503 (see create_app).
    """
    state = request.app.state
    contacts = state.contacts.fetch_contacts()
    now = state.clock()
    suggestions = build_suggestions(contacts, now, days, state.user)
    return SuggestionsOut(
        generated_at=now,
        days=days,
        user_time_zone=state.user.tz,
        suggestions=[ContactSuggestionOut.from_domain(s) for s in suggestions],
    )