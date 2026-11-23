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
