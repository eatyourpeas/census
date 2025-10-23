# Authentication and permissions

This document explains how users authenticate and what they can access in the system (SSR UI and API). It also describes the role model and how authorization is enforced in code.

## Authentication

Census supports multiple authentication methods for healthcare environments:

### Traditional Authentication
- Web UI uses Django session authentication with CSRF protection.
- API uses JWT (Bearer) authentication via SimpleJWT. Obtain a token pair using username/password, then include the access token in the `Authorization: Bearer <token>` header.
- Anonymous users can access public participant survey pages (SSR) when a survey is live. They cannot access the builder or any API objects.
- Usernames are equal to email addresses. Use your email as the username when logging in or obtaining tokens.

### Healthcare SSO (Single Sign-On)
Census integrates with OIDC providers for healthcare worker convenience:

#### Supported Providers
- **Google OAuth**: For healthcare workers with personal Google accounts
- **Microsoft Azure AD**: For hospital staff with organizational Microsoft 365 accounts
- **Multi-provider support**: Same user can authenticate via multiple methods

#### SSO Features
- **Email-based linking**: OIDC accounts automatically link to existing users via email address
- **Preserved encryption**: SSO users maintain the same encryption security as traditional users
- **Dual authentication**: Users can switch between SSO and password authentication
- **Organization flexibility**: Supports both personal and organizational accounts

#### Setup Requirements
To enable OIDC authentication, configure these redirect URIs in your cloud consoles:

**Google Cloud Console:**
- Production: `https://census.eatyourpeas.dev/oidc/callback/`
- Development: `http://localhost:8000/oidc/callback/`

**Azure Portal:**
- Production: `https://census.eatyourpeas.dev/oidc/callback/`
- Development: `http://localhost:8000/oidc/callback/`

#### Environment Configuration
OIDC requires these environment variables:
```bash
OIDC_RP_CLIENT_ID_AZURE=<azure-client-id>
OIDC_RP_CLIENT_SECRET_AZURE=<azure-client-secret>
OIDC_OP_TENANT_ID_AZURE=<azure-tenant-id>
OIDC_RP_CLIENT_ID_GOOGLE=<google-client-id>
OIDC_RP_CLIENT_SECRET_GOOGLE=<google-client-secret>
OIDC_RP_SIGN_ALGO=RS256
OIDC_OP_JWKS_ENDPOINT_GOOGLE=https://www.googleapis.com/oauth2/v3/certs
OIDC_OP_JWKS_ENDPOINT_AZURE=https://login.microsoftonline.com/common/discovery/v2.0/keys
```

#### User Experience
Healthcare workers can choose their preferred authentication method:
1. **SSO Login**: Click "Sign in with Google" or "Sign in with Microsoft"
2. **Traditional Login**: Use email and password
3. **Account Linking**: Same email automatically links OIDC and traditional accounts
4. **Encryption Integration**: All users get the same encryption protection regardless of authentication method

## Identity and roles

There are three key models in `census_app.surveys.models`:

- Organization: a container for users and surveys.
- OrganizationMembership: links a user to an organization with a role.
  - Roles: ADMIN, CREATOR, VIEWER
- Survey: owned by a user and optionally associated with an organization.

Role semantics used by the app:

- Owner: The user who created the survey. Owners can view/edit their own surveys.
- Org ADMIN: Can view/edit all surveys that belong to their organization.
- Org CREATOR or VIEWER: No additional rights beyond their personal ownership. They cannot access other members' surveys.
- Participant (no membership): Can only submit responses via public links; cannot access builder or API survey objects.

Single-organisation admin model:

- A user can be an ADMIN of at most one organisation. The user management hub (`/surveys/manage/users/`) focuses on that single organisation context for each admin user.

## Enforcement in server-side views (SSR)

The central authorization checks live in `census_app/surveys/permissions.py`:

- `can_view_survey(user, survey)` — True if user is the survey owner or an ADMIN of the survey's organization
- `can_edit_survey(user, survey)` — Same policy as view for now
- `require_can_view(user, survey)` — Raises 403 if not allowed
- `require_can_edit(user, survey)` — Raises 403 if not allowed

All builder/dashboard/preview endpoints call these helpers before proceeding. Unauthorized requests receive HTTP 403.

## Enforcement in the API (DRF)

The API mirrors the same rules using a DRF permission class and scoped querysets:

- Listing: returns only the surveys the user can see (their own plus any in orgs where they are ADMIN). Anonymous users see an empty list.
- Retrieve: allowed only if `can_view_survey` is true.
- Create: authenticated users can create surveys. The creator becomes the owner.
- Update/Delete/Custom actions: allowed only if `can_edit_survey` is true.

Error behavior:

- 401 Unauthorized: missing/invalid/expired JWT
- 403 Forbidden: logged in but insufficient permissions on the object

Additional protections:

- Object-level permissions are enforced for detail endpoints (retrieve/update/delete) and custom actions like `seed`. Authenticated users will receive 403 (Forbidden) if they don’t have rights on an existing object, rather than 404.
- Querysets are scoped to reduce exposure: list endpoints only return what you’re allowed to see (owned + org-admin).
- Throttling is enabled (AnonRateThrottle, UserRateThrottle). See `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` in `settings.py`.
- CORS is disabled by default (`CORS_ALLOWED_ORIGINS = []`). Enable explicit origins before using the API cross-site.

### Using the API with curl (JWT)

1. Obtain a token pair (access and refresh):

```sh
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"username": "<USER>", "password": "<PASS>"}' \
  https://localhost:8000/api/token
```

1. Call the API with the access token:

```sh
ACCESS=<paste_access_token>
curl -s -H "Authorization: Bearer $ACCESS" https://localhost:8000/api/surveys/
```

1. Refresh the access token when it expires:

```sh
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"refresh": "<REFRESH_TOKEN>"}' \
  https://localhost:8000/api/token/refresh
```

## Participants and sensitive data

- Public participant pages are SSR and respect survey live windows. Submissions are accepted without an account.
- Sensitive demographics are encrypted per-survey using an AES-GCM key derived for that survey. The key is shown once upon survey creation. Viewing decrypted demographics requires the survey key (handled server-side and not exposed via API).

## Security posture highlights

- CSRF and session security enabled; cookies are Secure/HttpOnly in production.
- Strict password validation and brute force protection (django-axes).
- CSP via django-csp. WhiteNoise serves static assets.
- Ratelimits for form submissions.

## Developer guidance

- Use the helpers in `surveys/permissions.py` from any new views.
- When adding API endpoints, prefer DRF permission classes that delegate to these helpers and always scope querysets by the current user.
- Return 403 (not 404) for authorization failures to avoid leaking resource existence to authenticated users; for anonymous API users, DRF may return 401 for unsafe methods.
