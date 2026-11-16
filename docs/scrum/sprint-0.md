# Sprint 0

**Product:** Calling-home planner
**Sprint end:** 11 Nov 2026
**MVP deadline:** 24 Nov 2026, 23:59

## Sprint goal

Set up the repository, both service skeletons, local Docker Compose, CI and the first
Azure infrastructure, so that feature work can start in Sprint 1.

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
- [ ] **Luna:** overlap-service skeleton with `/health`, one migration file, Dockerfile using
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
folder it runs `ruff check`, `ruff format --check` and `pytest`.

## Sprint review

_To fill in at the end of the sprint: what was finished and what moves to Sprint 1._

## Retrospective

_To fill in with the team: what went well, what to improve, one action for Sprint 1._
