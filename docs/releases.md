# Releases

All notable changes to this project are documented here. This file focuses on developer-facing changes (DX), CI, security posture, and API/documentation updates.

## Unreleased

- CI: Add PostgreSQL 16 service with healthcheck; wait for readiness using pg_isready.
- CI: Map Postgres port and use localhost in DATABASE_URL to avoid service DNS flakiness on GitHub-hosted runners.
- CI: Run Django migrations before tests to ensure schema is current.
- CI: Publish pytest JUnit XML report and upload as artifact.
- CI: Upload Docker service logs (Postgres, web) on failure to speed up triage.
- Docs UI: Add API docs links and CSP-safe badges (Swagger, ReDoc, OpenAPI schema) on home and docs pages.
- OpenAPI: Fixed missing dependencies (`inflection`, `uritemplate`); verified /api/schema.
- API Docs: Embedded Swagger UI and ReDoc pages served under /api/docs and /api/redoc.
- Security: Tight CSP; docs pages are CSP-exempt where required; no inline JS elsewhere.
- Publishing: Survey lifecycle (status/visibility/unlisted keys), access tokens, hCaptcha, one-response-per-token, thank-you page, and response metrics.
- Tests: Added tests for /api/schema and docs pages; expanded suite; lint fixes via Ruff.

### CI pipeline overview

The CI workflow spins up a PostgreSQL 16 service with a healthcheck and explicitly waits for readiness using pg_isready. We map port 5432 and connect via localhost to avoid occasional DNS resolution failures for the service hostname in GitHub-hosted runners. The steps are:

1. Checkout and setup Python 3.12
2. Wait for Postgres readiness (pg_isready against localhost)
3. Cache Poetry virtualenvs and install dependencies
4. Lint with Ruff and run Django system checks
5. Run migrations (manage.py migrate --noinput)
6. Run pytest; emit JUnit XML (pytest-report.xml)
7. Always upload the test report; on failure, also upload Docker logs (postgres.log, web.log)

This keeps CI close to production (Postgres) while remaining robust on shared runners.

## 0.1.0 — Initial Preview

- Core survey models and permissions parity across SSR and API.
- JWT auth via SimpleJWT; rate limiting and brute-force protection.
- Tailwind + DaisyUI styling; drag-and-drop for groups with SortableJS.
- Basic organization and survey management, response storage, and export foundations.
