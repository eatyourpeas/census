# Getting started with the API

This quick guide shows how to authenticate with JWT and call the API using curl, plus a small Python example.

Prerequisites:

- The app is running (Docker or `python manage.py runserver`)
- You have a user account (or a superuser)
- Base URL in examples: `https://localhost:8000`
- Usernames are equal to email addresses; log in with your email as the username.

## Interactive documentation

 [![Swagger UI](/static/docs/swagger-badge.svg)](/api/docs)
 [![ReDoc](/static/docs/redoc-badge.svg)](/api/redoc)
 [![OpenAPI JSON](/static/docs/openapi-badge.svg)](/api/schema)

Tip: In Swagger UI, paste your JWT into browser localStorage under the key `jwt` to auto-authorize requests.

## JWT with curl

1. Obtain a token pair (access and refresh):

```sh
curl -k -s -X POST -H "Content-Type: application/json" \
  -d '{"username": "<USER>", "password": "<PASS>"}' \
  https://localhost:8000/api/token
```

1. List surveys with Bearer token:

```sh
ACCESS=<paste_access_token>
curl -k -s -H "Authorization: Bearer $ACCESS" https://localhost:8000/api/surveys/
```

1. Create a survey with Bearer token:

```sh
ACCESS=<paste_access_token>
curl -k -s -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '{"name": "My Survey", "slug": "my-survey"}' \
  https://localhost:8000/api/surveys/
```

Note: The response includes a `one_time_key_b64` to store securely for demographics decryption.

1. Seed questions (owner or org ADMIN):

```sh
SURVEY_ID=<ID>
ACCESS=<paste_access_token>
curl -k -s -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -X POST \
  -d '[{"text": "Age?", "type": "text", "order": 1}]' \
  https://localhost:8000/api/surveys/$SURVEY_ID/seed/
```

For detailed documentation on question types, JSON structure, and advanced features like follow-up text inputs, see [Using the API](using-the-api.md).

1. Update survey (owner or org ADMIN):

```sh
SURVEY_ID=<ID>
ACCESS=<paste_access_token>
curl -k -s -H "Authorization: Bearer $ACCESS" \
  -H "Content-Type: application/json" \
  -X PATCH \
  -d '{"description": "Updated"}' \
  https://localhost:8000/api/surveys/$SURVEY_ID/
```

## Python example (requests)

```python
import requests

base = "https://localhost:8000"
session = requests.Session()
session.verify = False  # for local self-signed; do not use in production

# 1) Obtain token pair
r = session.post(
  f"{base}/api/token",
  json={"username": "<USER>", "password": "<PASS>"},
)
r.raise_for_status()
tokens = r.json()
access = tokens["access"]

headers = {"Authorization": f"Bearer {access}"}

# 2) List surveys
print(session.get(f"{base}/api/surveys/", headers=headers).json())

# 3) Create a survey
r = session.post(
  f"{base}/api/surveys/",
  json={"name": "Quick start", "slug": "quick-start"},
  headers=headers,
)
r.raise_for_status()
print(r.json())
```

## Permissions recap

- List shows your surveys and any in orgs where you are an ADMIN.
- Retrieve/Update/Delete/Seed require ownership or org ADMIN.
- Authenticated users without rights get 403; non-existent resources return 404.

## Publishing surveys via API

**Important note on encryption:**

Surveys that collect patient data (using question groups with `patient_details_encrypted` template) require encryption to be configured before publishing. The API will reject publish attempts with a `400 Bad Request` if encryption is not set up.

**Recommended workflow for patient data surveys:**

1. Create the survey structure via API:

   ```sh
   curl -k -s -H "Authorization: Bearer $ACCESS" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '{"name": "Patient Survey", "slug": "patient-survey"}' \
     https://localhost:8000/api/surveys/
   ```

2. Add questions and patient data groups via API

3. **Use the web interface** to publish the survey for the first time:
   - Navigate to the survey dashboard
   - Click "Publish"
   - Complete the encryption setup workflow (create recovery phrases, etc.)
   - This creates the necessary encryption keys

4. After encryption is set up, you can update publish settings via API:

   ```sh
   curl -k -s -H "Authorization: Bearer $ACCESS" \
     -H "Content-Type: application/json" \
     -X PUT \
     -d '{"status": "published", "visibility": "authenticated"}' \
     https://localhost:8000/api/surveys/$SURVEY_ID/publish/
   ```

**For surveys without patient data:** You can publish directly via API without encryption setup.

**Rationale:** The API uses JWT authentication (username/password based), not SSO. Interactive encryption setup—displaying recovery phrases, confirming encryption keys, etc.—is only available through the web interface. This design ensures patient data is always properly protected while keeping the API focused on administrative operations.

## Troubleshooting

- 401 on unsafe methods: missing session or CSRF token.
- 403 on unsafe methods: authenticated but not authorized for the resource.
- 400 on publish with "encryption" error: survey collects patient data but has no encryption; use web interface to set up encryption first.
- CORS errors in browser: CORS is disabled by default; allow origins explicitly in settings.
- SSL cert complaints with curl/requests: example uses `-k`/`verify=False` for local; remove in production.
