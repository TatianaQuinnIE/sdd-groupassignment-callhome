"""HTTP endpoints for "My week": the user's time zone, sleep hours and weekly busy blocks."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.schedule import describe, find_overlap
from app.schemas import BusyBlockIn, BusyBlockOut, ScheduleOut, SettingsIn

router = APIRouter(prefix="/me", tags=["my week"])


def _schedule(request: Request) -> ScheduleOut:
    repo = request.app.state.schedule
    return ScheduleOut(**repo.get_settings(), busy=repo.list_blocks())


@router.get("", response_model=ScheduleOut)
def get_my_week(request: Request):
    return _schedule(request)


@router.put("", response_model=ScheduleOut)
def update_my_settings(body: SettingsIn, request: Request):
    request.app.state.schedule.update_settings(body.model_dump())
    return _schedule(request)


@router.post("/busy", response_model=BusyBlockOut, status_code=status.HTTP_201_CREATED)
def add_busy_block(body: BusyBlockIn, request: Request):
    repo = request.app.state.schedule
    clash = find_overlap(repo.list_blocks(), body.weekday, body.start, body.end)
    if clash is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This overlaps {describe(clash)}. Change the times or remove that block first.",
        )
    return repo.add_block(body.model_dump())


@router.delete("/busy/{block_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_busy_block(block_id: int, request: Request):
    if not request.app.state.schedule.delete_block(block_id):
        raise HTTPException(status_code=404, detail=f"Busy block {block_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
