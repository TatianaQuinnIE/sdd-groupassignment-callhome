# Calling-home planner

A small web app that helps people living abroad find good times to call family and
friends back home, and tells them who they have not called in a while.

Scrum on Azure group assignment. MVP deadline: 24 Nov 2026, 23:59.

## What the product does

- **contacts-service** (Python FastAPI): stores contacts with home city, time zone,
  sleep hours, preferred call length and how often to call, plus a log of calls made.
- **overlap-service** (Python FastAPI): fetches contacts from contacts-service, finds the
  best call windows over the next 7 days, ranks contacts by how overdue they are, and
  flags public holidays in the contact's country (Nager.Date, cached).
- **UI**: plain HTML/JS on Azure Static Web Apps: a contacts page and a "This week" grid.

If overlap-service or Nager.Date is down, contacts and the call log still work and the
UI shows "Suggestions unavailable right now".

## Repository layout

| Folder | Contents |
| --- | --- |
| `contacts-service/` | Contacts and call-log API |
| `overlap-service/` | Call-window suggestions and holiday flags |
| `ui/` | Static front end |
| `docs/` | Decisions, data model, Scrum files |

## Team

| Name | GitHub | Workstream |
| --- | --- | --- |
| Alexandra | _add username_ | contacts-service |
| Luna | lunalarcher06 | overlap-service |
| Alicia | aliciaamueller | Frontend + integration |
| Tatiana | _add username_ | CI/CD pipeline |
| Sanad | _add username_ | Azure infrastructure + monitoring |

## Run locally

_To be added by Alicia (docker compose up)._

## Run the tests

_To be added by Alicia._

## Live URL and Azure setup

_To be added by Sanad._

## Rules

- No direct pushes to `main`. Every change goes through a pull request approved by another member.
- Never commit secrets. Only `.env.example` files are committed.
- AI-assisted work is recorded in `AI_USAGE.md`.
