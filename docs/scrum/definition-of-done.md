# Definition of Done

An item counts as done only when all of these are true:

1. It is merged into `main` through a pull request approved by another member.
2. CI is green: lint, format check, tests, coverage of at least 70%, Bandit, pip-audit and
   the gitleaks secret scan.
3. It is deployed to Azure by the pipeline, and `/health` returns 200.
4. It meets its acceptance criteria, checked by the Product Owner.
5. The docs are updated if it changes how to run, deploy or use the product.

Point 3 applies once the CD workflow is running (Sprint 1).

## Pull requests

- Small: under about 300 lines.
- One story per branch, named `feature/<story>-<name>`.
- Reviewed within 24 hours.
- No direct pushes to `main`, ever. Branch protection enforces this, including for admins.

## Secrets

- Only `.env.example` files are committed. `.env` is in `.gitignore`.
- The service principal, database passwords and any API keys live only in GitHub secrets
  and Container Apps secrets.
- If anything leaks: tell the group at once, rotate it, and follow the Assignment 2 §5
  procedure.

## AI usage

Every significant AI-assisted piece gets a row in `AI_USAGE.md`, added in the same pull
request.
