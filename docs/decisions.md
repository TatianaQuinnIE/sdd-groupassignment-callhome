# Decision records

One record per member (context, decision, alternatives, consequences).

1. Architecture (Alexandra)
2. Non-CRUD feature: overlap algorithm, time zones, Nager.Date caching (Luna)
3. Frontend (Alicia)
4. Deployment and pipeline (Tatiana)
5. Storage and monitoring (Sanad)

## 1. Architecture (Alexandra)

**Context.** The brief asks for exactly two services, each in its own container with its
own database, talking over HTTP, and a static UI that calls them from the browser. Our
product has two kinds of work: keeping the user's people and calls (plain data, full CRUD)
and working out when to call them (time-zone maths, the overdue ranking, the user's own
week, and public holidays from an external API). Five people build it in three short
sprints, so each part must be small enough for one owner to build, test and explain.

**Decision.**

- **contacts-service** owns the data the user types in: `contacts` and `call_logs`, with
  full CRUD. It is the single source of truth for people and calls, and it calls no other
  service.
- **overlap-service** owns everything that is calculated: call windows, the overdue
  ranking and holiday flags, plus the data only it needs (the user's week and the holiday
  cache). It reads contacts from contacts-service with `GET /contacts` and stores no
  contact data itself.
- The dependency runs one way only: overlap-service calls contacts-service, never the
  reverse. A down overlap-service or a failing Nager.Date never affects the contacts page.
- Both services use Python 3.12 and **FastAPI**: request and response models validate
  input and turn bad data into a clear 422, and the docs at `/docs` are generated from
  the code.
- **A layered structure inside each service**, with one job per file. In contacts-service:
  - `routes.py`: the HTTP layer. Turns requests into calls and results into status codes
    (201, 204, 404).
  - `schemas.py`: what goes in and out, with validation (real IANA time zone, two-letter
    country code, sensible call settings).
  - `repository.py`: all the SQL, written by hand, with parameters (never string-built
    queries). The rest of the code only sees Python dictionaries.
  - `db.py`, `config.py`, `migrations.py`, `logging_middleware.py`: the connection,
    settings from environment variables, versioned migrations on startup, one log line
    per request.

  overlap-service follows the same pattern, and keeps its algorithms (`windows.py`,
  `overdue.py`, `suggestions.py`) as pure functions with no HTTP and no database.
- A database that cannot be reached becomes a 503 with "Database unavailable, please try
  again shortly", not a stack trace.

**Alternatives considered.**

- *Split by feature (one service for contacts and the UI's needs, one for calls):* call
  logs and contacts change together and are joined for `last_called`, so splitting them
  would mean an HTTP call or duplicated data for every read.
- *Put call logs or the user's week in a third service:* not allowed (exactly two
  services, no third container).
- *Flask or Express:* both work, but FastAPI gives typed validation and API docs without
  extra libraries, and the team already used Python in Assignment 2.
- *An ORM such as SQLAlchemy:* less SQL to write, but one more dependency and layer to
  explain. Our queries are few and short, so plain SQL in one repository file is clearer
  and easy to review.
- *Hexagonal (ports and adapters):* more interfaces and folders than two small services
  need. The repository is already the one boundary we swap in tests.

**Consequences.**

- Each service can be built, tested, deployed and scaled to zero on its own, by its own
  owner.
- Because the API layer only talks to a repository, tests swap in an in-memory one: the
  contacts API is tested without a database, and coverage of contacts-service is about
  99%.
- If contacts-service is down, overlap-service cannot make suggestions and answers with a
  clear 503; the reverse case leaves contacts working. Partial failure is therefore
  one-sided, and the demo shows the overlap-service side.
- There is no foreign key between the services (see `docs/data-model.md`): the link is
  each contact's `id` over HTTP. A deleted contact simply stops appearing in suggestions.
- The SQL is written for SQL Server (Azure SQL and the local container), so moving to
  another database would mean rewriting the repository and the migrations.

## 2. Non-CRUD feature: overlap algorithm, time zones, Nager.Date caching (Luna)

**Context** The app should help answer two questions: when is a good time to call someone in another time zone, and who should I call first? To do this, it needs to account for time zones, sleep schedules, weekly busy hours and daylight saving changes. It also checks public holidays using Nager.Date. The API or database might be unavailable, so the app should still show call suggestions when holiday data cannot be loaded. The overlap service gets contact details from the contacts-service over HTTP; it does not access that service's database directly.

**Decision**
- `windows.py` uses pure functions, with no database or network calls. It converts times to UTC, works out when either person is unavailable, and returns the remaining call windows that are long enough. It handles daylight-saving changes and sleep times that continue past midnight.
- `overdue.py` sorts contacts by how overdue they are: days since the last call divided by the preferred time between calls. People who have never been called come first. Ties are sorted by id.
- `GET /suggestions?days=N` combines the call windows and overdue ranking. The allowed range for `days` is 1–14. If contacts-service is unavailable, the endpoint returns a 503. A bad contact record is skipped so it does not stop the whole response.
- Holiday data is checked in memory first, then in the SQL tables `holiday_cache` and `holiday_cache_status`, and then fetched from Nager.Date if needed. A lookup is made once per country and year. If a lookup fails, the failure is remembered for 60 seconds to avoid repeatedly calling an unavailable API. Regional holidays are ignored. Holiday flags use the contact's local calendar.
- If Nager.Date or the cache is unavailable, the endpoint still returns call windows, but without holiday flags. It sets `holidays_available` to false. The cache connection has a short timeout so a paused database does not hold up the page for long.
- The algorithm supports preferred call hours, but contacts-service and the UI do not store them yet.

**Alternatives considered**
- **Use both people's full calendars:** This would need more personal data and could create privacy concerns. Weekly busy times and preferred hours cover the main need.
- **Call Nager.Date for every request:** This is simpler, but can be slow and makes every request depend on the API.
- **Store holidays in contacts-service:** This would mix holiday data into the contacts service, so it was kept separate.
- **Fail the whole request if holiday data is missing:** This would hide useful call suggestions. It is better to return the suggestions without holiday flags.
- **Do the calculations in the browser:** This would duplicate the time-zone logic and make it harder to test consistently.

**Consequences**
- The functions are easy to test without a real database or network connection. I ran 151 tests locally.
- The holiday cache does not expire automatically. A correction from Nager.Date will not show up until the cached data is cleared.
- The first lookup for a new country and year takes longer because it fetches data from Nager.Date.
- Holiday flags rely on the contact having a valid `country_code` and `time_zone`.
- The UI uses `holidays`, `holiday` and `holidays_available` from `/suggestions`.

## 3. Frontend (Alicia)

**Context.** The brief asks for a static UI that calls both services from the browser,
with CORS restricted to the UI's origin and the service URLs as configuration, not code.
Static Web Apps is not available in our subscription's regions, so the UI is files in a
storage static website. Both services scale to zero and the databases auto-pause, so the
first request after a quiet period can fail or take about a minute. With one service down,
the other part of the product must keep working and the user must see a clear message.

**Decision.**

- Plain HTML, CSS and JavaScript in `ui/`, no framework and no build step. One file per
  part of the page: `api.js` (calls to the services), `contacts.js` (people, full CRUD),
  `calls.js` (call log), `suggestions.js` ("This week").
- Every call goes through one helper, `callService()`. It aborts after 10 seconds and turns
  every failure (timeout, service down, 503, validation error) into one readable sentence.
- The service URLs come from `config.js`. Locally it points to `localhost:8001/8002`; on
  deploy the pipeline overwrites it with the Azure URLs.
- Each part fails on its own: if overlap-service is down, "This week" shows "Suggestions
  unavailable right now" with a Try again button, and people and calls keep working.
- The services send times in UTC; the browser converts them with `Intl` (the contact's
  local time, and call windows in the user's time zone from `/suggestions`).
- Data from the API is always inserted with `textContent`, never as HTML.
- Locally, compose serves `ui/` with a stock `nginx` image (no Dockerfile, not a service
  container).

**Alternatives considered.**

- *React or Vue built to static files:* nicer components, but it adds a build step to the
  pipeline, many dependencies, and more code to explain for three small sections.
- *Server-rendered pages from a service:* ruled out by the brief (static UI only).
- *Hard-coded service URLs:* simpler, but each environment would need a code change.
- *One global error page:* simpler, but one service failing would hide the part that
  still works, which is what the partial-failure requirement asks us to avoid.

**Consequences.**

- Deploying the UI is just uploading `ui/`; there is nothing to build or install.
- No automated UI tests: each part was tested by hand in Chrome against the compose stack,
  including with overlap-service stopped. The services' logic is covered by their tests.
- Call windows are shown in the demo user's time zone (`Europe/Madrid`, set in
  overlap-service), not the browser's. Supporting real users would need a time zone setting.
- The headline fonts load from Google Fonts. If they don't load, the page falls back to
  system fonts and still works.

## 4. Deployment and pipeline (Tatiana)

**Context.** After the initial setup, only the pipeline may change Azure. Every merge to
`main` must be tested, packaged and deployed without anyone touching the portal, and the
run must fail if the system is not actually up. The IE subscription has no identity for
the pipeline and we cannot create one there, so on the professor's advice everything runs
in Sanad's Azure for Students subscription (`rg-sdd-3b-g5`, Poland Central). Static Web
Apps is not available in the regions that subscription allows.

**Decision.**

- `deploy.yml` runs on push to `main`. Its first job calls `ci.yml` (`workflow_call`), and
  the deploy job has `needs: ci`, so nothing is deployed unless lint, format, tests (70%
  coverage), Bandit, pip-audit, gitleaks and the Docker build all pass. CI's own `push`
  trigger ignores `main`, so it does not run twice.
- Images are built with `provenance=false` and pushed to GHCR as
  `ghcr.io/tatianaquinnie/<service>:<commit SHA>`. Every running container can be traced
  to one commit.
- The pipeline signs in to Azure with OIDC as the managed identity `sdd-3b-g5-github`
  (Contributor on the resource group). GitHub holds no Azure password, only the
  client, tenant and subscription IDs and the two database passwords.
- For each Container App (contacts first, because overlap calls it): set the
  `db-password` secret from GitHub, set the ingress target port to 8000, switch to the new
  image.
- The UI gets the service addresses from a `config.js` written at deploy time, and `ui/`
  is uploaded to the `$web` container of the storage account.
- The run passes only when each app runs the new image and `/health` returns 200,
  retrying for 3 minutes to cover the cold start and the database resuming.

**Alternatives considered.**

- *`workflow_run` (deploy after a separate CI run):* works, but CI and deploy end up in two
  runs, and the guide asks for `workflow_call`.
- *Service principal with a client secret (`AZURE_CREDENTIALS`):* IE accounts cannot create
  service principals, and a stored secret would need rotating. OIDC has nothing to leak.
- *Azure Container Registry:* one more paid resource in the group. GHCR is free and
  already next to the code.
- *Static Web Apps for the UI:* our first plan, dropped because the region is not allowed
  in the subscription.
- *Waiting for `latestReadyRevisionName`:* our first health check. That field stays empty
  in our setup, so the first deploy was reported as failed although both services were
  up. PR #12 replaced it with "new image + `/health` 200".

**Consequences.**

- A merge to `main` is live in about 3–4 minutes. A red CI blocks the deploy.
- Rolling back means reverting the commit (the pipeline redeploys the previous code), or
  pointing the app at an older SHA tag.
- The first request after a quiet period can take about a minute (scale to zero and
  database auto-pause). The health check waits for it, and the UI must show a "starting
  up" message.
- One deploy at a time (`concurrency`), so two quick merges cannot overwrite each other.
- The pipeline depends on the federated credential subject matching
  `repo:TatianaQuinnIE/sdd-groupassignment-callhome:ref:refs/heads/main`. Renaming or
  transferring the repository breaks the sign-in until the credential is updated.

## 5. Storage and monitoring (Sanad)

**Context.** Each service needs its own data store in Azure, at almost no cost, and the
brief asks for request logs we can query plus a dashboard with request count, error rate
and response time, and one SLO. We run on an Azure for Students subscription with a small
credit and five allowed regions.

**Decision.**

- One Azure SQL logical server (`sdd-3b-g5-sql-pl`) with one serverless database per
  service, on the free offer (General Purpose, Gen5, 0.5-1 vCore, auto-pause when idle).
  Each service has a contained database user that exists only in its own database
  (`db_ddladmin`, `db_datareader`, `db_datawriter`), so it can run its migrations but can
  never read the other service's data. The firewall allows only Azure services.
- All Azure resources are in Bicep (`infra/`), so the setup can be repeated in another
  subscription. That already happened once, when we moved from the IE subscription (#15).
- Monitoring uses the Log Analytics workspace the Container Apps environment already
  writes to. Each service logs one INFO line per request (method, path, status, duration),
  without bodies. A saved function `RequestLogs` parses that line; saved queries and an
  Azure Workbook show request count, 5xx error rate and p50/p95 response time per service.
- SLO: 99% of `GET /contacts` answered without a server error in under 500 ms over 7 days,
  because every page of the UI starts with that request. Details in
  [`docs/monitoring.md`](monitoring.md).

**Alternatives considered.**

- *One shared database for both services:* simpler, but the services would be coupled
  through tables, and the brief wants each service to own its data.
- *Provisioned (always-on) databases:* no wake-up delay, but they cost money every hour.
  Serverless with auto-pause is nearly free for our traffic.
- *Application Insights with the OpenTelemetry SDK:* richer traces, but more code and
  dependencies in both services and more data to pay for. Our log lines already hold the
  three numbers the brief asks for.
- *A portal dashboard instead of a Workbook:* both work, but a Workbook can be defined in
  Bicep and keeps its queries next to the charts.

**Consequences.**

- Almost no running cost, but the first request after a quiet period waits for the
  container to start and the database to resume (up to about a minute).
- The cold-start 503 comes from Azure's ingress, not our code, so it is not in our logs
  and the SLO does not count it.
- Logs are kept 30 days with a 1 GB/day cap, which is plenty at INFO level.
- The dashboard depends on the log line format. Changing `logging_middleware.py` means
  updating the `RequestLogs` parser.
