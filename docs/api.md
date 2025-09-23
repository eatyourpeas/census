# API reference and protections

This document summarizes the REST API endpoints and their permission model.

## Authentication

- JWT (Bearer) authentication via SimpleJWT. Obtain tokens at `/api/token` and `/api/token/refresh` and pass the access token in `Authorization: Bearer <token>`.

## Endpoints

Base path: `/api/`

- `GET /health` — health check (AllowAny)
- `POST /token` — obtain JWT access/refresh pair
- `POST /token/refresh` — refresh access token
- `GET /surveys/` — list surveys visible to the current user
- `POST /surveys/` — create a survey (authenticated); returns `one_time_key_b64` once
- `GET /surveys/{id}/` — retrieve a survey (owner or org ADMIN)
- `PATCH /surveys/{id}/` — update a survey (owner or org ADMIN)
- `DELETE /surveys/{id}/` — delete a survey (owner or org ADMIN)
- `POST /surveys/{id}/seed/` — bulk create questions (owner or org ADMIN)
- `GET /surveys/{id}/publish/` — get publish settings (owner/org ADMIN/creator/viewer with view permission)
- `PUT /surveys/{id}/publish/` — update publish settings (owner/org ADMIN/creator)
- `GET /surveys/{id}/metrics/responses/` — response counts (total/today/last7/last14) for admins/creators/viewers with view permission
- `GET /users/` — admin-only read-only list

### Invite tokens

- `GET /surveys/{id}/tokens/` — list up to 500 most recent invite tokens (owner/org ADMIN/creator)
- `POST /surveys/{id}/tokens/` — create up to 1000 tokens with optional expiry/note (owner/org ADMIN/creator)

### OpenAPI and Swagger UI

- `GET /api/schema` — OpenAPI schema (JSON)
- `GET /api/docs` — Embedded Swagger UI (CSP-exempt). Paste a JWT into localStorage key `jwt` to authorize requests automatically.

## Permissions matrix (summary)

- Owner
  - List: sees own surveys
  - Retrieve/Update/Delete: allowed for own surveys
- Org ADMIN
  - List: sees all surveys in their organization(s)
  - Retrieve/Update/Delete: allowed for surveys in their organization(s)
- Org CREATOR/VIEWER
  - List: sees only own surveys
  - Retrieve: allowed for surveys they’re a member of
  - Update/Delete: only creators can update; viewers are read-only
  - Publish GET: allowed for creators and viewers (view permission)
  - Publish PUT: allowed for creators (and owner/org ADMIN)
  - Metrics GET: allowed for creators and viewers (view permission)
- Anonymous
  - List: empty array
  - Retrieve/Update/Delete: not allowed

## Error codes

- 401 Unauthorized — not authenticated for unsafe requests
- 403 Forbidden — authenticated but not authorized (object exists)
- 404 Not Found — resource doesn’t exist

## Throttling

- Enabled via DRF: `AnonRateThrottle` and `UserRateThrottle`.
- Rates configured in `census_app/settings.py` under `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`.

## CORS

- Disabled by default. To call the API from another origin, explicitly set `CORS_ALLOWED_ORIGINS` in settings.

## Example curl snippets (session + CSRF)

See `docs/authentication-and-permissions.md` for a step-by-step session login and CSRF flow using curl.
