# Getting started

This guide gives you a quick tour of the project, how to run it with Docker, and where to go next.

## What is Census?

Census is a secure, server-rendered survey platform built with Django and DRF. It focuses on:

- Strong security by default (CSP, CSRF, HSTS, rate limits, audit logs)
- Simple SSR UI with Tailwind + DaisyUI
- Fine-grained permissions for organizations, surveys, and memberships
- A drag-and-drop survey builder and API for programmatic seeding

## Prerequisites

- Docker and Docker Compose

## Clone and run

```bash
git clone <your-repo-url>
cd census
docker compose up --build
```

This will:

- Build the Docker image (Python + Poetry + Node for CSS build)
- Start Postgres and the Django app
- Run migrations and Tailwind build automatically
- Serve the app on <http://localhost:8000>

## Login and create an account

- Visit <http://localhost:8000>
- Click Sign up to create a user
- From Profile, you can “Upgrade to organization” to create an organization you own.

## Development workflow

- CSS: Tailwind/DaisyUI builds at startup. If you edit CSS or templates frequently, you can run a local Node watcher or re-run `npm run build:css` inside the container.
- Tests: Run the test suite inside the container:

```bash
docker compose exec web python -m pytest -q
```

## Next steps

- Read Surveys to create an organization, survey, and content.
- Read Branding and Theme Settings to customize the look and feel.
- See Getting Started with the API for API usage and authentication.

## Troubleshooting

- If the web service fails on first run, try rebuilding:

```bash
docker compose down
docker compose up --build
```
