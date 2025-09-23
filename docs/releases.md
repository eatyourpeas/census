# Releases

All notable changes to this project are documented here. This file focuses on developer-facing changes (DX), CI, security posture, and API/documentation updates.

## Unreleased

- CI: Add PostgreSQL 16 service with healthcheck; wait for readiness using pg_isready.
- CI: Use service hostname in DATABASE_URL; run Django migrations before tests.
- CI: Publish pytest JUnit XML report and upload as artifact.
- CI: Upload Docker service logs (Postgres, web) on failure to speed up triage.
- Docs UI: Add API docs links and CSP-safe badges (Swagger, ReDoc, OpenAPI schema) on home and docs pages.
- OpenAPI: Fixed missing dependencies (`inflection`, `uritemplate`); verified /api/schema.
- API Docs: Embedded Swagger UI and ReDoc pages served under /api/docs and /api/redoc.
- Security: Tight CSP; docs pages are CSP-exempt where required; no inline JS elsewhere.
- Publishing: Survey lifecycle (status/visibility/unlisted keys), access tokens, hCaptcha, one-response-per-token, thank-you page, and response metrics.
- Tests: Added tests for /api/schema and docs pages; expanded suite; lint fixes via Ruff.

## 0.1.0 — Initial Preview

- Core survey models and permissions parity across SSR and API.
- JWT auth via SimpleJWT; rate limiting and brute-force protection.
- Tailwind + DaisyUI styling; drag-and-drop for groups with SortableJS.
- Basic organization and survey management, response storage, and export foundations.
