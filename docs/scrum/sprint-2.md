# Sprint 2

**Product:** Calling-home planner
**Dates:** 19–24 Nov 2026 (feature freeze Mon 23 Nov, submission tag Tue 24 Nov)
**MVP deadline:** 24 Nov 2026, 23:59

## Sprint goal

The MVP is complete, monitored and documented. A user opens the live UI on Azure, adds a
contact, logs a call and sees the "This week" grid with call suggestions and holiday
flags. If overlap-service or Nager.Date is down, the contacts page still works and shows
"Suggestions unavailable right now". The team can show request count, error rate, p95 and
one SLO from Log Analytics, and every member has a decision record and `AI_USAGE.md` rows.

## Team

| Member | GitHub | Workstream |
| --- | --- | --- |
| Alexandra | alemol123 | contacts-service |
| Luna | lunalarcher06 | overlap-service |
| Alicia | aliciaamueller | Frontend + integration |
| Tatiana | TatianaQuinnIE | CI/CD pipeline |
| Sanad | sanadhamadd | Azure infrastructure + monitoring |

**Product Owner:** Luna
**Scrum Master:** Tatiana

## Sprint backlog

Tick an item when it is merged into `main` and meets the Definition of Done
(`docs/scrum/definition-of-done.md`), which includes a green deploy and `/health` 200.

- [x] **Alicia:** `docker-compose.yml` with both services, one SQL Server container holding
      both databases (`db-init` creates them and one login per service), and the UI; static
      `index.html` calling both `/health` endpoints (#14, #16). Carried over from Sprint 0.
- [x] **Alicia:** real UI: contacts CRUD, "Log a call" per contact, "This week" grid, error
      banner and "Suggestions unavailable right now" (#19)
- [ ] **Alicia:** README "Run locally" and "Run the tests" sections (#18, in review)
- [ ] **Alicia:** "My week": edit your own busy times, sleep and time zone (#21, in review)
- [x] **Luna:** `GET /suggestions` in overlap-service (#17)
- [ ] **Luna:** Nager.Date client using the `holiday_cache` table, holiday flags in
      `/suggestions`
- [ ] **Luna:** tests with mocked HTTP for Nager.Date down, timing out or returning bad data
      (second partial-failure case)
- [ ] **Alexandra:** `docs/data-model.md` with an ER diagram matching the migrations
- [x] **Sanad:** Azure setup moved to our own subscription (`rg-sdd-3b-g5`, Poland Central);
      Bicep, pipeline identity and README "Live URL and Azure setup" updated (#15)
- [ ] **Sanad:** saved Log Analytics queries (request count, error rate, p95 per service), a
      Workbook, and an SLO ("99% of GET /contacts under 500 ms over 7 days") with its KQL
- [x] **Tatiana:** deploy health check fixed, so a green Deploy run means both apps run this
      commit's image and `/health` returns 200 (#12)
- [x] **Tatiana:** decision record 4 (deployment and pipeline) and the README architecture
      diagram (#13)
- [ ] **Tatiana:** rotate both database passwords (Sanad changes them in SQL, Tatiana updates
      the GitHub secrets) and check the next deploy is green
- [ ] **Alexandra and Sanad:** `docs/scrum/sprint-1.md`
- [ ] **Luna and Tatiana:** this file
- [ ] **Everyone:** own decision record in `docs/decisions.md` (1 Alexandra, 2 Luna,
      3 Alicia #20 in review, 4 Tatiana done, 5 Sanad) and own `AI_USAGE.md` rows

## Already done before this sprint (Sprint 1, merged into `main` by 18 Nov)

- Coverage gate, security checks and Definition of Done (#7, Tatiana)
- Call-window algorithm with tests (#5, Luna) and overdue ranking (#6, Luna)
- Azure infrastructure in Bicep and first deploy (#8, Sanad)
- Contacts CRUD with validation and tests (#9, Alexandra) and call log (#10, Alexandra)
- CD pipeline: images to GHCR, deploy to Azure Container Apps, health check (#11, Tatiana)

## Sprint review

_Status on Sun 22 Nov; final version after the feature freeze on Mon 23 Nov._

**Done (merged into `main`):** compose with one SQL Server container (#16), `GET /suggestions`
(#17), the real UI with partial-failure handling (#19), the move to our own Azure
subscription (#15), the health-check fix (#12) and decision record 4 with the diagram (#13).
The last Deploy runs on `main` are green and the UI is live at
https://sdd3bg5ui.z36.web.core.windows.net.

**In review:** README run locally / tests (#18), decision record 3 (#20), "My week" (#21).

**Not started on `main` yet:** Nager.Date client and its tests, monitoring and SLO,
`docs/data-model.md`, `sprint-1.md`, decision records 1, 2 and 5, password rotation.

_Goal met or not: to decide at the review on Mon 23 Nov._

## Retrospective

_To fill in with the team after the rehearsal on Mon 23 Nov: what went well, what to
improve, one agreement for next time._
