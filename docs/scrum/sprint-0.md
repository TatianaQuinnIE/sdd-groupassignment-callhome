# Sprint 0

**Product:** Calling-home planner
**Dates:** 4–10 Nov 2026
**MVP deadline:** 24 Nov 2026, 23:59

## Sprint goal

`docker compose up` from a clean clone returns the UI page and `/health` from both
services.

## Team

| Member | GitHub | Workstream |
| --- | --- | --- |
| Alexandra | alemol123 | contacts-service |
| Luna | lunalarcher06 | overlap-service |
| Alicia | aliciaamueller | Frontend + integration |
| Tatiana | TatianaQuinnIE | CI/CD pipeline |
| Sanad | sanadhamadd | Azure infrastructure + monitoring |

**Product Owner:** Alicia
**Scrum Master:** Tatiana

## Sprint backlog

Tick an item when it is merged into `main`.

- [x] **Luna:** repository skeleton
- [x] **Alexandra:** contacts-service skeleton with `/health`, one migration file, Dockerfile
      (pinned dependencies, non-root, no `COPY . .`), request log middleware
- [x] **Luna:** overlap-service skeleton with `/health`, one migration file, Dockerfile using
      the same pattern, reused log middleware, Nager.Date tried for 3–4 countries
- [ ] **Alicia:** `docker-compose.yml` with both services, two SQL Server containers and the
      UI, static `index.html` that calls both `/health` endpoints
- [x] **Tatiana:** branch protection on `main` (PR + 1 approval + CI green), CI workflow
      running lint, format check and tests on every PR, this file
- [ ] **Sanad:** access to the Azure resource group checked, group service principal stored as
      a GitHub secret, first Bicep file for the Container Apps environment and the two
      databases

## Working agreement

- Branch from `main` as `feature/<story>-<name>`.
- No direct pushes to `main`. Every change needs a pull request, one approval from another
  member and a green `ci` check.
- Never commit secrets. Only `.env.example` files are committed.
- AI-assisted work is recorded in `AI_USAGE.md`.

## Continuous integration

`.github/workflows/ci.yml` runs on every pull request. For each service that has an `app/`
folder it runs `ruff check`, `ruff format --check` and `pytest`. The rules for "done" are in
`docs/scrum/definition-of-done.md`.

## Sprint review

The Sprint Goal was not met: there is no `docker-compose.yml` on `main` yet, so the
system cannot be started from a clean clone.

**Done (merged into `main` by 10 Nov):**

- Repository skeleton (Luna, first commit, before branch protection was on)
- contacts-service skeleton (#1, Alexandra)
- CI workflow, branch protection and this file (#2, Tatiana)
- overlap-service skeleton (#4, Luna)

**Not done, moved to Sprint 1:**

- `docker-compose.yml` and static `index.html` (Alicia)
- Azure access check, service principal as a GitHub secret, first Bicep file (Sanad)
- `docs/scrum/definition-of-done.md` (Tatiana, added in Sprint 1)

The repository was transferred from Alicia's account to Tatiana's on 10 Nov, because
branch protection needs an owner or admin.

## Retrospective

**What went well**

- Both service skeletons follow the same pattern (`/health`, request log middleware,
  migration runner, Dockerfile with pinned dependencies and a non-root user), so either
  service is easy to read for anyone in the team.
- CI and branch protection were on from the first week: every change after the skeleton
  went through a pull request, a review and a green `ci` check.
- Roles and workstreams were clear from the start, one per member.

**What to improve**

- Everything was merged on the last day (10 Nov). Work that lands that late cannot be
  integrated or fixed before the review, and the Sprint Goal was missed for that reason.
- The integration piece (`docker-compose.yml`) depended on both services and only started
  once they existed. It should start in parallel, against agreed ports and settings.
- Azure access was not checked early enough: the group identity in the IE subscription
  was still missing at the end of the sprint.

**Action for Sprint 1**

- Agree the API contract (endpoint names and JSON fields) on the first day, so everyone
  can build in parallel against it, and merge small pieces during the sprint instead of
  at the end.
- Get a first deploy through the pipeline in the first days of Sprint 1, as the brief
  asks, before building features on top.
