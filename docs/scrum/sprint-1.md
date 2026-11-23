# Sprint 1

**Product:** Calling-home planner
**Dates:** 11–18 Nov 2026
**MVP deadline:** 24 Nov 2026, 23:59

## Sprint goal

The skeleton runs on Azure through the pipeline, then contacts can be created, listed,
edited and deleted end to end.

## Team

| Member | GitHub | Workstream |
| --- | --- | --- |
| Alexandra | alemol123 | contacts-service |
| Luna | lunalarcher06 | overlap-service |
| Alicia | aliciaamueller | Frontend + integration |
| Tatiana | TatianaQuinnIE | CI/CD pipeline |
| Sanad | sanadhamadd | Azure infrastructure + monitoring |

**Product Owner:** Alexandra
**Scrum Master:** Sanad

## Sprint backlog

Ticked items were merged into `main` between 11 and 18 Nov.

- [x] **Luna:** call-window algorithm as pure functions, with tests for daylight saving
      and windows crossing midnight (#5)
- [x] **Luna:** overdue ranking: contacts never called first, then by how late the call is (#6)
- [x] **Tatiana:** coverage gate (fails under 70%), Bandit, pip-audit and gitleaks in CI,
      and `docs/scrum/definition-of-done.md` (#7)
- [x] **Sanad:** Azure infrastructure in Bicep: Log Analytics, Container Apps environment,
      both Container Apps, SQL server and two serverless databases (#8)
- [x] **Alexandra:** contacts CRUD with validation and tests (#9)
- [x] **Alexandra:** call log and `last_called` on each contact, migration 002 (#10)
- [x] **Tatiana:** CD pipeline: images to GHCR tagged by commit SHA, deploy to Azure
      Container Apps, `/health` check (#11)
- [ ] **Alicia:** `docker-compose.yml` and a static `index.html` calling both `/health`
      endpoints (carried over from Sprint 0)
- [ ] **Luna:** `GET /suggestions`, fetching contacts from contacts-service with a timeout
- [ ] **Alicia:** contacts page in the UI (list, add, edit, delete)

## Sprint review

Held in class on 19 Nov. Alexandra (Product Owner) checked each item against its
acceptance criteria.

The Sprint Goal was **partly met**. The pipeline (#11) was merged on 18 Nov and both
services reached Azure, but the first Deploy run was reported as failed because the health
check waited for a field that stays empty in our setup. The contacts API was complete
(#9, #10), but there was no UI on `main` yet, so contacts could not be managed end to end
from the browser.

**Done (merged into `main` by 18 Nov):** #5, #6, #7, #8, #9, #10, #11.

**Not done, moved to Sprint 2:**

- Deploy health check fix (Tatiana, #12, merged 19 Nov)
- `docker-compose.yml` and `index.html` (Alicia, #14 and #16)
- `GET /suggestions` (Luna, #17)
- Contacts page and the rest of the UI (Alicia, #19)

## Retrospective

_Written by Alexandra (Product Owner) from the Sprint 1 commit and pull-request history,
and confirmed by Sanad (Scrum Master) when approving this file._

**What went well**

- Every backend item came with tests and passed the new CI gates: 70% coverage, Bandit,
  pip-audit and gitleaks (#7). The contacts API (#9, #10) and the call-window and overdue
  algorithms (#5, #6) reached `main` tested.
- The infrastructure is code (#8, Bicep), so the Azure setup can be rebuilt instead of
  clicked together in the portal.
- Field names were agreed between services early: contacts-service returns exactly what
  overlap-service's overdue ranking needs (`last_called`, `call_every_days`).

**What to improve**

- Work landed too late: all 7 Sprint 1 pull requests were merged on the last two days
  (17–18 Nov), and the CD pipeline (#11) on the evening of the last day. When its first
  run was reported as failed, there was no time left to fix it inside the sprint.
- Some reviews were very fast: #9 and #10 were merged within a few minutes of their last
  commit, which leaves little time for the reviewer to run the code.
- `docker-compose.yml` was carried over a second time, so nobody could start the whole
  system locally and test the services together before deploying.

**Agreements for Sprint 2**

- Merge small pull requests as soon as each piece works, not at the end of the sprint,
  and freeze features on Mon 23 Nov so the last day is for fixes and the rehearsal.
- A reviewer pulls the branch and runs the tests or the app before approving.
- docker-compose comes first, so every member can run the full system locally.
