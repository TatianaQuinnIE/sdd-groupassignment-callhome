# AI usage

Each member adds a row for every significant AI-assisted piece (including workflows,
Dockerfiles and Bicep). Add rows as you go, not on the last day.

| Member | What | Tool / model | What I reviewed or changed |
| --- | --- | --- | --- |
| Luna | Asked Claude to match my code of overlap-service to Alexandra's code contacts-service | Claude (Sonnet 5.5) | Compared code with contacts-service, fixed a bug that caused duplicate entries in schema_migrations, added httpx2 to developer requirements to fix test failures. |
| Luna | Asked Claude on how could I implement schedules to the algorithm.| Claude (Sonnet 5.5) | At first I asked to have both people's calendar so they can see eachothers free hours. It was a better and easier change just to add prefered call hours blocks so that each person can see when would they like to be called during their free time. |
| Tatiana | CI workflow and sprint-0.md | Claude Code (Opus 5.5) | Read both files and filled in the Scrum roles |
| Tatiana | CI checks (coverage gate, Bandit, pip-audit, gitleaks), definition-of-done.md, Sprint 0 review | Claude Code (Opus 5.5) | Read all three files before committing |
| Sanad | Bicep file for our Azure setup and the Azure part of the README | Claude Code (Opus 5.5) | Went through it piece by piece and read each part before committing. Checked the settings against the prof's deployment guide. First deploy failed because my SQL password had part of the login name in it, so I changed it and redeployed. Opened all three URLs to make sure they work. |
| Alexandra | contacts-service skeleton: /health, request logging, migration runner, first migration, Dockerfile and tests | Claude Code (Opus 5.5) | Read each file to understand it, ran the tests and the Docker container locally and opened /health before pushing. Fixed my branch when it was not based on main. |
| Alexandra | Contacts CRUD endpoints with validation, repository layer and tests (PR #9) | Claude Code (Opus 5.5) | Asked for it to match the field names in Luna's overdue and windows code. Ran ruff and the 34 tests locally before pushing; Luna reviewed it. |
| Alexandra | Call log endpoints, last_called on contacts, migration 002 and tests | Claude Code (Opus 5.5) | Checked last_called matches what Luna's overdue ranking needs. Ran ruff and the 51 tests locally before pushing.
