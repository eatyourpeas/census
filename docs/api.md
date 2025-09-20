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
- `GET /users/` — admin-only read-only list

## Permissions matrix (summary)

- Owner
  - List: sees own surveys
  - Retrieve/Update/Delete: allowed for own surveys
- Org ADMIN
  - List: sees all surveys in their organization(s)
  - Retrieve/Update/Delete: allowed for surveys in their organization(s)
- Org CREATOR/VIEWER
  - List: sees only own surveys
  - Retrieve/Update/Delete: not allowed for others' surveys
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
