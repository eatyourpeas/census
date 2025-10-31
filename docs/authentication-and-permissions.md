# Authentication and permissions

This document explains how users authenticate and what they can access in the system (SSR UI and API). It also describes the role model and how authorization is enforced in code.

## Authentication

CheckTick supports multiple authentication methods for healthcare environments:

### Traditional Authentication
- Web UI uses Django session authentication with CSRF protection.
- API uses JWT (Bearer) authentication via SimpleJWT. Obtain a token pair using username/password, then include the access token in the `Authorization: Bearer <token>` header.
- Anonymous users can access public participant survey pages (SSR) when a survey is live. They cannot access the builder or any API objects.
- Usernames are equal to email addresses. Use your email as the username when logging in or obtaining tokens.

### Healthcare SSO (Single Sign-On)

CheckTick integrates with OIDC providers for seamless clinician authentication:

#### Supported Providers

- **Google OAuth**: For clinicians with personal Google accounts
- **Microsoft Azure AD**: For hospital staff with organizational Microsoft 365 accounts
- **Multi-provider support**: Same user can authenticate via multiple methods

#### Key Features

- **Email-based linking**: OIDC accounts automatically link to existing users via email address
- **Preserved encryption**: SSO users maintain the same encryption security as traditional users
- **Dual authentication**: Users can switch between SSO and password authentication
- **Organization flexibility**: Supports both personal and organizational accounts
- **External user support**: Handles Azure AD guest accounts and external clinicians

#### User Experience

Clinicians can choose their preferred authentication method:

1. **SSO Login**: Click "Sign in with Google" or "Sign in with Microsoft"
2. **Traditional Login**: Use email and password
3. **Account Linking**: Same email automatically links OIDC and traditional accounts
4. **Encryption Integration**: All users get the same encryption protection regardless of authentication method

#### Enterprise Setup

For detailed setup instructions including cloud console configuration, environment variables, and troubleshooting, see:

**📋 [OIDC SSO Setup Guide](oidc-sso-setup.md)**

This comprehensive guide covers:

- Step-by-step Azure AD and Google Cloud setup
- Production environment configuration
- Security considerations and best practices
- Troubleshooting common issues

## Identity and roles

There are four key models in `census_app.surveys.models`:

- Organization: a container for users and surveys.
- OrganizationMembership: links a user to an organization with a role.
  - Roles: ADMIN, CREATOR, VIEWER
- Survey: owned by a user and optionally associated with an organization.
- SurveyMembership: links a user to a specific survey with a role.
  - Roles: CREATOR, EDITOR, VIEWER

### Organization Roles

Organization-level role semantics:

- **Owner**: The user who created the survey. Owners can view/edit their own surveys.
- **Org ADMIN**: Can view/edit all surveys that belong to their organization.
- **Org CREATOR or VIEWER**: No additional rights beyond their personal ownership. They cannot access other members' surveys.
- **Participant** (no membership): Can only submit responses via public links; cannot access builder or API survey objects.

### Survey Collaboration Roles

Individual surveys can have collaborators with specific roles through SurveyMembership:

| Role | Content Editing | User Management | Survey Creation |
|------|----------------|-----------------|-----------------|
| **CREATOR** | Yes | Yes | Yes |
| **EDITOR** | Yes | No | No |
| **VIEWER** | No | No | No |

- **CREATOR**: Full access to survey content and collaborator management. Can edit questions, groups, and manage other users' access to the survey.
- **EDITOR**: Can modify survey content (questions, groups, settings) but cannot manage collaborators or create new surveys.
- **VIEWER**: Read-only access to surveys for monitoring and preview purposes.

Single-organisation admin model:

- A user can be an ADMIN of at most one organisation. The user management hub (`/surveys/manage/users/`) focuses on that single organisation context for each admin user.

### Survey Collaboration Features

Survey creators can invite collaborators to work on specific surveys through the "Manage collaborators" feature:

- **Adding collaborators**: Survey CREATORs can add users by email address and assign roles
- **Role management**: CREATORs can change collaborator roles or remove access
- **Dashboard integration**: The survey dashboard shows a "Manage collaborators" button only to users who can manage survey users (CREATORs)
- **Permission boundaries**: EDITORs can modify survey content but cannot see or access user management features

This enables teams to collaborate on survey design while maintaining clear boundaries between content editing and access control.

## Enforcement in server-side views (SSR)

The central authorization checks live in `census_app/surveys/permissions.py`:

- `can_view_survey(user, survey)` — True if user is the survey owner, an ADMIN of the survey's organization, or has survey membership (CREATOR, EDITOR, or VIEWER)
- `can_edit_survey(user, survey)` — True if user is the survey owner, an ADMIN of the survey's organization, or has survey membership as CREATOR or EDITOR
- `can_manage_survey_users(user, survey)` — True if user is the survey owner, an ADMIN of the survey's organization, or has survey membership as CREATOR (only CREATORs can manage collaborators)
- `require_can_view(user, survey)` — Raises 403 if not allowed
- `require_can_edit(user, survey)` — Raises 403 if not allowed

All builder/dashboard/preview endpoints call these helpers before proceeding. Unauthorized requests receive HTTP 403.

## Enforcement in the API (DRF)

The API mirrors the same rules using a DRF permission class and scoped querysets:

- **Listing**: returns only the surveys the user can see (their own, any in orgs where they are ADMIN, plus surveys they are members of via SurveyMembership). Anonymous users see an empty list.
- **Retrieve**: allowed only if `can_view_survey` is true.
- **Create**: authenticated users can create surveys. The creator becomes the owner.
- **Update/Delete/Custom actions**: allowed only if `can_edit_survey` is true (CREATOR and EDITOR roles for survey members).

User management operations (adding/removing collaborators) require `can_manage_survey_users` permission, which is restricted to survey CREATORs, organization ADMINs, and survey owners.

Error behavior:

- 401 Unauthorized: missing/invalid/expired JWT
- 403 Forbidden: logged in but insufficient permissions on the object

Additional protections:

- Object-level permissions are enforced for detail endpoints (retrieve/update/delete) and custom actions like `seed`. Authenticated users will receive 403 (Forbidden) if they don't have rights on an existing object, rather than 404.
- Querysets are scoped to reduce exposure: list endpoints only return what you're allowed to see (owned + org-admin).
- Throttling is enabled (AnonRateThrottle, UserRateThrottle). See `REST_FRAMEWORK.DEFAULT_THROTTLE_RATES` in `settings.py`.
- CORS is disabled by default (`CORS_ALLOWED_ORIGINS = []`). Enable explicit origins before using the API cross-site.

### Account Deletion Restrictions

For security and data integrity, account deletion is strictly controlled:

- **User accounts**: Only superusers can delete user accounts via Django Admin (`/admin/auth/user/`)
- **Organizations**: Only superusers can delete organizations via Django Admin (`/admin/surveys/organization/`)
- **Regular users cannot delete their own accounts** to prevent data loss and maintain security

This protects against:

- Accidental deletion of surveys shared with other users
- Malicious or compromised account actions
- Loss of audit trails and organizational data
- Cascade deletion effects that impact multiple users

Survey creators and organization admins retain full control over survey access and membership management, but cannot perform destructive account-level operations.

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

## Error Pages and User Experience

CheckTick provides styled error pages for common authentication and permission failures, ensuring users receive helpful feedback when access is denied or issues occur:

### Custom Error Templates

- **403 Forbidden**: Displayed when authenticated users lack permission to access a resource. Shows clear messaging about access restrictions and provides navigation options back to safe areas.
- **404 Not Found**: Friendly page-not-found experience with suggestions to return to the dashboard or home page.
- **405 Method Not Allowed**: Technical error page for HTTP method mismatches.
- **500 Internal Server Error**: Reassuring message when server errors occur, encouraging users to try again or contact support.
- **Account Lockout**: Displayed after 5 failed login attempts (via django-axes). Informs users of the 1-hour cooldown period and offers password reset options.

All error templates extend the base template and use DaisyUI components, maintaining consistent branding and styling throughout the application. They include helpful actions like "Back to Dashboard", "Go to Home Page", and "Reset Password" to guide users toward resolution.

### Testing Error Pages in Development

When `DEBUG=True`, developers can preview all error pages at `/debug/errors/` to verify styling and user experience. These debug routes are automatically disabled in production (when `DEBUG=False`).

### Brute Force Protection

The django-axes integration tracks failed login attempts and locks accounts after 5 failures. The lockout period is 1 hour, after which users can attempt to log in again. The custom lockout template (`403_lockout.html`) provides clear guidance during this period.

## Security posture highlights

- CSRF and session security enabled; cookies are Secure/HttpOnly in production.
- Strict password validation and brute force protection (django-axes).
- CSP via django-csp. WhiteNoise serves static assets.
- Ratelimits for form submissions.

## Developer guidance

- Use the helpers in `surveys/permissions.py` from any new views.
- When adding API endpoints, prefer DRF permission classes that delegate to these helpers and always scope querysets by the current user.
- Return 403 (not 404) for authorization failures to avoid leaking resource existence to authenticated users; for anonymous API users, DRF may return 401 for unsafe methods.
