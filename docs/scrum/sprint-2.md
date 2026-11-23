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
- [x] **Alicia:** README "Run locally" and "Run the tests" sections (#18)
- [x] **Alicia:** "My week": edit your own busy times, sleep and time zone (#21)
- [x] **Alicia:** "This week" shows public holidays: flagged windows, a holiday list, and a
      note when holidays can't be checked (#29)
- [x] **Alicia:** Sprint 0 retrospective, as Sprint 0 Product Owner (#23)
- [x] **Luna:** `GET /suggestions` in overlap-service (#17)
- [x] **Luna:** Nager.Date client using the `holiday_cache` table, holiday flags in
      `/suggestions` (#24)
- [x] **Luna:** tests with mocked HTTP for Nager.Date down, timing out or returning bad data
      (second partial-failure case) (#24)
- [x] **Alexandra:** `docs/data-model.md` with an ER diagram matching the migrations (#25)
- [x] **Sanad:** Azure setup moved to our own subscription (`rg-sdd-3b-g5`, Poland Central);
      Bicep, pipeline identity and README "Live URL and Azure setup" updated (#15)
- [x] **Sanad:** saved Log Analytics queries (request count, error rate, p95 per service), a
      Workbook, and an SLO ("99% of GET /contacts under 500 ms over 7 days") with its KQL
      (`infra/monitoring.bicep`, `docs/monitoring.md`) (#30)
- [x] **Tatiana:** deploy health check fixed, so a green Deploy run means both apps run this
      commit's image and `/health` returns 200 (#12)
- [x] **Tatiana:** decision record 4 (deployment and pipeline) and the README architecture
      diagram (#13)
- [ ] **Tatiana:** rotate both database passwords (Sanad changes them in SQL, Tatiana updates
      the GitHub secrets) and check the next deploy is green. Not done, on purpose: see
      "Not done" below.
- [x] **Alexandra and Sanad:** `docs/scrum/sprint-1.md` (#27)
- [x] **Luna and Tatiana:** this file (status on 22 Nov in #22, final version in #31)
- [x] **Everyone:** own decision record in `docs/decisions.md` (1 Alexandra #26, 2 Luna #28,
      3 Alicia #20, 4 Tatiana #13, 5 Sanad #30) and own `AI_USAGE.md` rows

## Already done before this sprint (Sprint 1, merged into `main` by 18 Nov)

- Coverage gate, security checks and Definition of Done (#7, Tatiana)
- Call-window algorithm with tests (#5, Luna) and overdue ranking (#6, Luna)
- Azure infrastructure in Bicep and first deploy (#8, Sanad)
- Contacts CRUD with validation and tests (#9, Alexandra) and call log (#10, Alexandra)
- CD pipeline: images to GHCR, deploy to Azure Container Apps, health check (#11, Tatiana)

## Sprint review

_Final version, Mon 23 Nov, after the feature freeze._

The Sprint Goal was met. On the live site (https://sdd3bg5ui.z36.web.core.windows.net) on
23 Nov we added a contact in Boston (US), logged a call, and saw "This week" with Thursday
26 Nov flagged as Thanksgiving Day, the "Public holidays" list and the "My week" card.
The test contact was deleted afterwards. Both `/health` endpoints returned 200, and the
last Deploy runs on `main` (after #28, #29 and #30) were green. Request count, error rate,
p95 and the SLO are in the Log Analytics Workbook (#30), and all five decision records and
everyone's `AI_USAGE.md` rows are on `main`.

**Done (merged into `main` 19–23 Nov):**

- Health-check fix (#12) and decision record 4 with the architecture diagram (#13), Tatiana
- docker-compose with one SQL Server container and the status page (#14, #16), Alicia
- Move to our own Azure subscription (#15), Sanad
- `GET /suggestions` (#17), Luna
- README "Run locally" and "Run the tests" (#18), Alicia
- Real UI with partial-failure handling (#19) and "My week" (#21), Alicia
- Decision record 3 (#20), Alicia
- Sprint 2 doc, status on 22 Nov (#22), Tatiana and Luna
- Sprint 0 retrospective (#23), Alicia
- Nager.Date client, holiday cache and mocked tests for down, timeout and bad data (#24), Luna
- `docs/data-model.md` (#25) and decision record 1 (#26), Alexandra
- `docs/scrum/sprint-1.md` (#27), Alexandra and Sanad
- Decision record 2 (#28), Luna
- Holidays in the "This week" UI (#29), Alicia
- Monitoring: saved queries, Workbook, SLO and decision record 5 (#30), Sanad
- Final Sprint 2 doc with the review and retrospective (#31), Tatiana and Luna

**Not done:**

- Rotation of both database passwords. We decided not to do it before the deadline. No
  password has leaked (gitleaks is green on every run, and the passwords are only in GitHub
  and Container Apps secrets). Rotating means Sanad changes both passwords in SQL at the
  same moment as a deploy pushes the new secrets, and any mismatch takes the live site
  down right before the submission and the demo. The GitHub secrets were last set on
  18 Nov. Moved to after the submission.

## Retrospective

_Written by Tatiana (Scrum Master) from the Sprint 2 commit and pull-request history,
and confirmed by the team on 23 Nov._

**What went well**

- The partial-failure design works at both levels. If overlap-service is down, the
  contacts page still works and shows "Suggestions unavailable right now" (#19). If
  Nager.Date is down, times out or returns bad data, the suggestions still come back
  without holiday flags (#24, tested with mocked HTTP) and the UI says "Public holidays
  couldn't be checked right now" (#29).
- `docker-compose.yml` came first this time (#14, #16, as agreed in Sprint 1), so the
  later features could be run and tested locally, e.g. #29 was tested against Luna's
  branch running locally.
- Every pull request was approved by another member before merging, and every Deploy
  run on `main` on 23 Nov was green, so each merge was live within minutes.
- Everyone wrote their own decision record and `AI_USAGE.md` rows.

**What to improve**

- Work was late again, as in Sprint 0 and Sprint 1: 15 of the 19 Sprint 2 pull requests
  were merged on 22–23 Nov, 8 of them on the feature-freeze day itself, including the
  holiday feature (#24, #29).
- Several people edited the same files in parallel (`AI_USAGE.md`, `docs/decisions.md`,
  `docs/data-model.md`), which caused merge conflicts: branches had to merge `main` back
  in to keep both versions (#23, #28), and the holiday branch was restarted from `main`
  after a conflict with "My week".
- Some reviews were approvals based on reading the diff, without running the branch.

**Agreement for next time**

- Merge each piece as soon as it works, and add your rows to shared files (`AI_USAGE.md`,
  `docs/decisions.md`) in that same small pull request, so shared files change a little
  at a time during the sprint instead of all at once on the last day.
