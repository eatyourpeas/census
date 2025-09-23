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

## Troubleshooting

- 401 on unsafe methods: missing session or CSRF token.
- 403 on unsafe methods: authenticated but not authorized for the resource.
- CORS errors in browser: CORS is disabled by default; allow origins explicitly in settings.
- SSL cert complaints with curl/requests: example uses `-k`/`verify=False` for local; remove in production.
