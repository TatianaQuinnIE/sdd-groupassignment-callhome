# Decision records

One record per member (context, decision, alternatives, consequences).

1. Architecture (Alexandra)
2. Non-CRUD feature: overlap algorithm, time zones, Nager.Date caching (Luna)
3. Frontend (Alicia)
4. Deployment and pipeline (Tatiana)
5. Storage and monitoring (Sanad)

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
