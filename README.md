# Census

Census is a survey platform for medical audit and research. It is secure with encrypted identifiers only visible to users entering the data.

## Contributing

Please read CONTRIBUTING.md for guidelines, especially around dummy credentials in tests and secret scanning.

### Enable pre-commit hooks

To run basic hygiene and secret scanning locally before each commit:

```bash
# macOS
brew install pre-commit

# Install hooks for this repo
pre-commit install
pre-commit install --hook-type commit-msg

# Optional: run on the whole repo once
pre-commit run --all-files
```

## Core Requirements

The application is open source and customizable for look and feel. Users create accounts to run surveys that they distribute by sharing a url

## Accounts and Authentication

Users can be individuals or Organisations that contain individuals. Permissions levels include those users creating surveys, those users that can view all surveys in an organisation, and superusers. Those completing surveys have access only to that survey and to edit their own record.   Users completing surveys do not have to own an account but they can only view the record they create. Users should not be able to edit a survey more than once unless specified otherwise.

### Creating a survey

The application runs in the browser and offers users creating surveys the option of creating surveys from different question types. These include: free text, multiple choice (single and multiple selection), lickert scale, orderable list, yes/no, drop-down, image choice. It is possible to group questions into sections. There is a menu of customisable question groups that can be shared between surveys.

A single user (or organisation) can create multiple surveys, each with its own link and set of question groups and questions. Users can share question groups with other users in a community. On creation of a survey, a unique one-time key is created for that survey visible only to the creator(s) of that survey. This key is used to encrypt/decrypt sensitive fields.

Seeding a survey with questions can be done as a drag and drop with elements on a canvas, but also can be done through an API that accepts a list of questions with options and question type and question group. It is also possible to create a survey from a simple markdown file with headings as question group headings, individual lines per question and question types in brackets, with bullets or dashes below as a list of options.

Where demographic information is collected (names, dates of birth, hospital numbers, addresses), appropriate data impact assessments will be in place by the users prior. Sensitive fields are encrypted using the unique survey key known only to the admin for that survey.

Some fields on completing will need access to external APIs:

1. ODS codes for GP surgeries or hospital trusts
2. medical terminologies such as SNOMED
3. index of multiple deprivation scores from postcodes
4. organisation codes from postcodes such as local authority or ICB

Surveys are distributed either by links in an email list or are scheduled to be live between specific dates. There is a dashboard per survey showing number of completed surveys.

### Data Storage

Data on each survey are stored in a local folder or as blob storage as with each response to a survey in json. Critical fields are hashed and accessible only to those with the survey key. Data is exportable as csv without the identifiers but not exportable with the identifiers. Data with identifiers is viewable in the platform to those in possession of the survey key and who are users with permission to edit the survey.

### Reporting

There is some high-level reporting in a dashboard in real time - it reports numbers of returns and aggregated counts of fields.

## Technologies

Census must be open source and customisable - admin users can change css / icons. There can be organisational styling for the platform, with options to change this per survey.

The project should be dockerized and easy to deploy. It is a security-first project so must follow the OWASP principles. Credentials and sensitive data is stored on a server. Python is used as this is the organisational preferred language.

Frontend frameworks should be modern and lightweight, with a popular styling library (daisy ui/tailwind) and where possible, webcomponents should be used that can be shared and reused, especially for the form controls or form groups.

Styling
Basic styling is minimalist, soft and friendly, but sciencey and professional looking.

## Documentation

User documentation is provided as well as documentation of an API to:

- get / list / create / update / delete surveys
- healthcheck
- get / list / create / update / delete users

See docs:

- docs/README.md
- docs/authentication-and-permissions.md
- docs/api.md
- docs/getting-started-api.md
- docs/user-management.md
- docs/themes.md
- CONTRIBUTING.md


## Quickstart

Local with Docker (recommended):

1. Copy environment file and edit as needed

   ```bash
   cp .env.example .env
   ```

2. Build and start services

   ```bash
   docker compose up --build
   ```

3. Open <https://localhost:8000>

Without Docker (Python + Node):

- Install Poetry and Node 18+
- poetry install
- npm install && npm run build:css
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py runserver

API endpoints:

- GET /api/health
- POST /api/token (JWT obtain)
- POST /api/token/refresh (JWT refresh)
- /api/surveys/ (CRUD for authenticated owners)
- /api/users/ (admin read-only)

API permissions mirror SSR rules: you can list and retrieve surveys you own, and any survey in organizations where you are an ADMIN. Updates/deletes require ownership or org ADMIN.
See docs/api.md for endpoint-level protections and error semantics.

Security posture:

- Server-side rendering, CSRF protection, session cookies (HttpOnly, Secure)
- Strict password validators, lockout on brute force (django-axes)
- Rate limiting on form posts (django-ratelimit)
- CSP headers (django-csp) and static via WhiteNoise
- Sensitive demographics encrypted per-survey using AES-GCM with derived keys; responses mirrored to filesystem under data/
- API uses JWT (Bearer) auth; include Authorization header in requests.

## Tests

There are tests for all the endpoints, and in particular for all the functions relating to user and organisation management and permissions. There are also tests for survey creation and update, and relating to hashing and decryption of key identifiers.
