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
| Alexandra | alemol123 | contacts-service |
| Luna | lunalarcher06 | overlap-service |
| Alicia | aliciaamueller | Frontend + integration |
| Tatiana | TatianaQuinnIE | CI/CD pipeline |
| Sanad | sanadhamadd | Azure infrastructure + monitoring |

## Run locally

_To be added by Alicia (docker compose up)._

## Run the tests

_To be added by Alicia._

## Live URL and Azure setup

### Live URLs

| Part | URL |
| --- | --- |
| UI (Static Web App) | https://proud-smoke-020ed6603.5.azurestaticapps.net |
| contacts-service | https://sdd-3b-g5-contacts.salmoncoast-e659666b.westeurope.azurecontainerapps.io |
| overlap-service | https://sdd-3b-g5-overlap.salmoncoast-e659666b.westeurope.azurecontainerapps.io |

Until the first pipeline deploy, both services run a placeholder image and the UI shows
the default Static Web Apps page. After a quiet period the first request can take up to a
minute, because the container starts from zero and the database resumes from auto-pause.

### What runs in Azure

Everything is in the group resource group `rg-sdd-3b-g5` (West Europe), in the IE
subscription, and is defined in [`infra/main.bicep`](infra/main.bicep).

| Resource | Name | Settings |
| --- | --- | --- |
| Log Analytics workspace | `sdd-3b-g5-logs` | 30-day retention, 1 GB/day cap |
| Container Apps environment | `sdd-3b-g5-env` | Consumption plan, logs to the workspace above |
| Container App | `sdd-3b-g5-contacts` | 0-1 replicas, 0.25 vCPU, 0.5 GiB |
| Container App | `sdd-3b-g5-overlap` | 0-1 replicas, 0.25 vCPU, 0.5 GiB |
| SQL server | `sdd-3b-g5-sql` | TLS 1.2+, firewall: Azure services only |
| SQL database | `sdd-3b-g5-contacts-db` | Serverless Gen5 0.5-1 vCore, auto-pause 15 min, 2 GB |
| SQL database | `sdd-3b-g5-overlap-db` | Serverless Gen5 0.5-1 vCore, auto-pause 15 min, 2 GB |
| Static Web App | `sdd-3b-g5-ui` | Free tier |

Configuration reaches the services only through environment variables. Database
passwords are Container Apps secrets. CORS allows only the UI's address and is handled in
the service code, not in the Container Apps ingress.

### Reproduce the setup

The initial setup is run once by one member. After that, only the pipeline changes
anything. No password is ever written in the repository.

1. Accept the Microsoft invitation from IE Instituto de Empresa, S.L., then sign in to
   that directory:

   ```bash
   az login --tenant 5ca2bc70-353c-4d1f-b7d7-7f2b2259df68
   ```

2. Choose three strong passwords (SQL admin, `contacts_app` user, `overlap_app` user) and
   keep them in a password manager. They must not contain any part of the login name.

3. Preview, then deploy:

   ```bash
   az deployment group what-if --resource-group rg-sdd-3b-g5 --template-file infra/main.bicep
   az deployment group create --resource-group rg-sdd-3b-g5 --template-file infra/main.bicep
   ```

   `az` asks for the three passwords; they are `@secure()` parameters, so they are not
   stored in the deployment history. The command prints the live URLs.

Still to do: one database user per service (`contacts_app`, `overlap_app`), the federated
credential for the pipeline identity, and the GitHub secrets.

## Deployment pipeline

`.github/workflows/deploy.yml` runs on every push to `main`:

1. Runs the whole of `ci.yml` (lint, format, tests with the 70% gate, Bandit, pip-audit,
   gitleaks, Docker build). If anything fails, nothing is deployed. On `main`, CI runs only
   from here, so it does not run twice.
2. Builds both images and pushes them to GHCR as
   `ghcr.io/tatianaquinnie/<service>:<commit SHA>` (owner in lowercase, `provenance: false`).
3. Signs in to Azure as the managed identity `sdd-3b-g5-github` with OIDC (no Azure
   password stored in GitHub).
4. For each Container App (contacts first): sets the database password secret, sets the
   target port to 8000 and switches the image to the new SHA.
5. Writes `ui/config.js` with both service addresses and uploads `ui/` to the `$web`
   container of the storage account `UI_STORAGE` (static website).
6. Calls `/health` on both services for up to 3 minutes and fails the run if the new
   revision never returns 200.

GitHub secrets it needs (Settings › Secrets and variables › Actions): `AZURE_CLIENT_ID`,
`AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `CONTACTS_DB_PASSWORD`, `OVERLAP_DB_PASSWORD`.
Variables: `PREFIX`, `RESOURCE_GROUP` and `UI_STORAGE` (default `sdd-3b-g5`, `rg-sdd-3b-g5`
and `sdd3bg5ui`).

First deploy only: GHCR packages start private, so Azure cannot pull them. After the first
run, open each package (`contacts-service`, `overlap-service`) in GitHub › Packages ›
Package settings, change visibility to Public, and re-run the failed job.

## Rules

- No direct pushes to `main`. Every change goes through a pull request approved by another member.
- Never commit secrets. Only `.env.example` files are committed.
- AI-assisted work is recorded in `AI_USAGE.md`.
