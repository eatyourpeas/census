# User management and permissions

This document explains how organization- and survey-level user management works across SSR (server-rendered UI) and the API, including roles, permissions, endpoints, and security protections. The app follows a single-organisation admin model and enforces username=email.

## Roles and scopes

There are two membership scopes with separate roles:

- Organization membership (OrganizationMembership)
  - admin: Full administrative control over the organization context, including managing org members and managing surveys within the organization.
  - creator: Can create and manage their own surveys; read-only visibility to organization content is up to app policy, but creators do NOT manage org members.
  - viewer: Read-only role for organization context where applicable; cannot manage org members.

- Survey membership (SurveyMembership)
  - creator: Can manage members for that specific survey and edit the survey.
  - viewer: Can view the survey content and results according to app policy; cannot manage survey members.

Additional implicit authorities:

- Survey owner: Always has full control over the survey, including member management for that survey.
- Organization admin: Has admin rights for surveys that belong to their organization, including member management.

Single-organisation model:

- A user can be an ADMIN of at most one organisation. The “User management” hub focuses on that single org context.

## Permission matrix (summary)

- Manage org members (add/update/remove): Organization admin only
- Manage survey members (add/update/remove): Survey owner, organization admin (if the survey belongs to their org), or survey creator for that survey
- View survey: Owner, org admin (if applicable), any survey member (creator/viewer)

Guardrails:

- Organization admins cannot remove themselves from their own admin role via the SSR UI or the API. Attempts are rejected.
- SSR UI supports email-based lookup and creation for convenience. The API endpoints expect explicit user IDs for membership resources; scoped user creation endpoints exist to create a user in a given org or survey.

## SSR management pages

- Organisation hub: `/surveys/manage/users/`
  - Shows the single organisation you manage, all its users, and users grouped by surveys.
  - Quick-add forms let you add users to the organisation or to a survey by email and role.
  - Prevents an org admin from removing themselves as an admin.
  - Actions are audit-logged.

- Organization users: `/surveys/org/<org_id>/users/`
  - Admins can add or update members by email, change roles, and remove users. Non-admins receive 403.
  - Actions are audit-logged.

- Survey users: `/surveys/{slug}/users/`
  - Owners, org admins (if the survey belongs to their org), and survey creators can add/update/remove survey members.
  - Survey viewers see a read-only list.
  - Actions are audit-logged.

## API endpoints

Authentication: All endpoints below require JWT. Include "Authorization: Bearer <access_token>".

### Organization memberships

- List: GET /api/org-memberships/
- Create: POST /api/org-memberships/
- Update: PUT/PATCH /api/org-memberships/{id}/
- Delete: DELETE /api/org-memberships/{id}/

Scope and permissions:

- Queryset is restricted to organizations where the caller is an admin.
- Create/Update/Delete require admin role in the target organization.
- Delete: additionally prevents an org admin from removing their own admin membership.
- Unauthorized or out-of-scope access returns 403 Forbidden. Missing/invalid JWT returns 401 Unauthorized.

Serializer fields:

- id, organization, user, username (read-only), role, created_at (read-only)

### Survey memberships

- List: GET /api/survey-memberships/
- Create: POST /api/survey-memberships/
- Update: PUT/PATCH /api/survey-memberships/{id}/
- Delete: DELETE /api/survey-memberships/{id}/

Scope and permissions:

- Queryset contains only memberships for surveys the caller can view (owner, org-admin for the survey's org, or the caller is a member of the survey).
- Create/Update/Delete require manage permission on the survey (owner, org admin for the survey's org, or survey creator).
- Unauthorized or out-of-scope access returns 403; missing/invalid JWT returns 401.

Serializer fields:

- id, survey, user, username (read-only), role, created_at (read-only)

### Scoped user creation

To support flows where an admin/creator wants to add a person who may not yet exist:

- Create user within an org context (org admin only):
  - POST /api/scoped-users/org/{org_id}/create

- Create user within a survey context (survey owner/org admin/creator):
  - POST /api/scoped-users/survey/{survey_id}/create

Request schema:

- email (string, required)
- password (string, optional)

Behavior:

- If a user with the given email already exists, it is reused; otherwise a new user is created with username=email. Password is required only when creating a new user (optional if reusing).
- On success, returns the user's id/username/email and adds them as a Viewer in the specified scope by default (org Viewer or survey Viewer).
- Permission checks mirror the membership rules above. Unauthorized attempts receive 403.

Note: The SSR UI allows searching by email and will create or reuse users accordingly, with audit logging. If you need similar behavior via API, use the scoped user creation endpoints described here.

## Audit logging

Membership actions performed via the SSR UI are recorded in AuditLog with:

- actor, scope (organization or survey), organization/survey context, action (add/update/remove), target_user, metadata (e.g., role), timestamp

These records enable traceability of who changed which memberships and when.

## Security notes

- JWT is required for API access. Missing/invalid tokens result in 401; valid tokens without sufficient privileges result in 403.
- SSR uses session auth with CSRF protection and enforces permissions via centralized helpers.
- Organization admins cannot remove themselves as admins via the UI or the API; requests to remove self-admin are rejected.
- Sensitive demographics remain encrypted per-survey and are unaffected by membership operations.

## Testing

The test suite includes:

- JWT auth enforcement (missing/invalid tokens, refresh flow)
- API permission tests for list/detail/update/seed
- SSR portal tests for org/survey user management behaviors and permission boundaries

All tests are designed to ensure that protections are consistent and robust across SSR and API.
