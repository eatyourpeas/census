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

### Quick Start (Docker Compose)

```bash
git clone <your-repo-url>
cd census
docker compose up --build
```

### Development Environment Script

For a better development experience, use the provided startup script:

```bash
./s/dev
```

This enhanced script will:

- Build the Docker image (Python + Poetry + Node for CSS build)
- Start Postgres and the Django app in detached mode
- Run migrations and Tailwind build automatically
- Serve the app on <http://localhost:8000>
- Provide helpful status updates and tips

## Development Environment Options

### For VS Code Users

If you're using VS Code, you can automatically open it after starting the containers:

```bash
# Option 1: Using the --code flag
./s/dev --code

# Option 2: Using environment variable
OPEN_VSCODE=true ./s/dev
```

**Benefits:**
- Containers start in the background
- VS Code opens automatically in the project directory
- Ready to start coding immediately

**Requirements:**
- VS Code must be installed with the `code` command available in your PATH

### For Non-VS Code Users

Simply use the standard startup command:

```bash
./s/dev
```

This will start all containers without opening any editor, giving you full control over your development environment.

### Script Help

View all available options:

```bash
./s/dev --help
```

Both approaches will:

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

### Container Issues

If the web service fails on first run, try rebuilding:

```bash
docker compose down
docker compose up --build
```

Or using the development script:

```bash
docker compose down
./s/dev
```

### VS Code Not Opening

If you use `./s/dev --code` but VS Code doesn't open:

1. **Check VS Code installation**: Ensure VS Code is installed and the `code` command is available:
   ```bash
   code --version
   ```

2. **Install VS Code CLI**: If the `code` command isn't available, install it:
   - **macOS/Linux**: Open VS Code → Command Palette (Cmd/Ctrl+Shift+P) → "Shell Command: Install 'code' command in PATH"
   - **Windows**: Usually installed automatically with VS Code

3. **Alternative**: Start containers without VS Code integration:
   ```bash
   ./s/dev
   ```

### Development Script Help

For all available options and troubleshooting:

```bash
./s/dev --help
```
