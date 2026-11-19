"""HTTP endpoints for contacts: full CRUD."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.repository import ContactsRepository
from app.schemas import CallIn, CallOut, ContactIn, ContactOut

router = APIRouter(prefix="/contacts", tags=["contacts"])


def get_repo(request: Request) -> ContactsRepository:
    return request.app.state.repo


Repo = Annotated[ContactsRepository, Depends(get_repo)]


def not_found(contact_id: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Contact {contact_id} not found")


@router.get("", response_model=list[ContactOut])
def list_contacts(repo: Repo):
    return repo.list_contacts()


@router.post("", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(body: ContactIn, repo: Repo):
    return repo.create_contact(body.model_dump())


@router.get("/{contact_id}", response_model=ContactOut)
def get_contact(contact_id: int, repo: Repo):
    contact = repo.get_contact(contact_id)
    if contact is None:
        raise not_found(contact_id)
    return contact


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(contact_id: int, body: ContactIn, repo: Repo):
    contact = repo.update_contact(contact_id, body.model_dump())
    if contact is None:
        raise not_found(contact_id)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(contact_id: int, repo: Repo):
    if not repo.delete_contact(contact_id):
        raise not_found(contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{contact_id}/calls", response_model=list[CallOut])
def list_calls(contact_id: int, repo: Repo):
    calls = repo.list_calls(contact_id)
    if calls is None:
        raise not_found(contact_id)
    return calls


@router.post("/{contact_id}/calls", response_model=CallOut, status_code=status.HTTP_201_CREATED)
def add_call(contact_id: int, body: CallIn, repo: Repo):
    call = repo.add_call(contact_id, body.model_dump())
    if call is None:
        raise not_found(contact_id)
    return call


@router.delete("/{contact_id}/calls/{call_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_call(contact_id: int, call_id: int, repo: Repo):
    if not repo.delete_call(contact_id, call_id):
        raise HTTPException(status_code=404, detail=f"Call {call_id} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
