# API reference and protections

Use the interactive documentation for the full, always-up-to-date list of endpoints and schemas:

- Swagger UI: /api/docs
- ReDoc: /api/redoc
- OpenAPI JSON: /api/schema

Notes:

- We link out to interactive docs instead of embedding them directly into this Markdown to respect our strict Content Security Policy (no inline scripts in docs pages).

## Authentication

- JWT (Bearer) authentication via SimpleJWT. Obtain tokens at `/api/token` and `/api/token/refresh` and pass the access token in `Authorization: Bearer <token>`.

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
