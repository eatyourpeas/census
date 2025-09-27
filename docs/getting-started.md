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

You have three options for VS Code integration:

#### Option 1: Local Virtual Environment (Best IntelliSense)

Develop with a local Python environment for the best IDE experience:

1. **Prerequisites:**
   - pyenv (for Python version management)
   - Poetry will be installed automatically

2. **Setup:**

   ```bash
   # Set up local virtual environment with all dependencies
   ./s/setup-local
   
   # Configure VS Code to use the local environment
   ./s/configure-vscode-local
   ```

3. **Reload VS Code window** (`Cmd+Shift+P` → "Developer: Reload Window")

**Benefits:**

- **Full IntelliSense support** - Complete import resolution, type hints, and autocomplete
- All Python packages directly accessible to VS Code language server
- Keep your host Git setup and credentials  
- Native VS Code performance
- Best debugging experience

**Trade-offs:**

- Requires local Python environment setup
- Need to keep local dependencies in sync with Docker
- Slightly more complex initial setup

**When to use:** When you want the best possible IDE experience with full IntelliSense support.

#### Option 2: Dev Containers (Full Container Development)

Use the provided Dev Container configuration to develop entirely within the container:

1. **Prerequisites:**
   - Install the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Usage:**

   ```bash
   # Start containers
   ./s/dev
   
   # In VS Code: Cmd+Shift+P → "Dev Containers: Reopen in Container"
   ```

**Benefits:**

- Complete development environment in container
- All Python dependencies pre-installed
- Consistent environment across team members
- No local Python setup required

**When to use:** When you prefer complete container isolation and don't mind container setup complexity.

#### Option 3: Docker Python Integration (Hybrid Development)

Develop on your host machine while using the Docker container's Python environment:

1. **Start your development environment:**

   ```bash
   ./s/dev
   ```

2. **Configure VS Code Python interpreter:**
   - Open Command Palette (`Cmd+Shift+P`)
   - Run `Python: Select Interpreter`
   - Choose `./docker-python` from the list
   - If not visible, select "Enter interpreter path..." and browse to `./docker-python`

3. **Install required VS Code extensions:**

   ```bash
   # Install these extensions if not already installed:
   # - Python (ms-python.python)
   # - Pylance (ms-python.vscode-pylance) 
   # - Black Formatter (ms-python.black-formatter)
   # - Ruff (charliermarsh.ruff)
   ```

4. **Create VS Code settings** (if not already present):

   Create or update `.vscode/settings.json` in your project root:

   ```json
   {
     "python.pythonPath": "./docker-python",
     "python.defaultInterpreterPath": "./docker-python",
     "python.linting.enabled": false,
     "python.terminal.activateEnvironment": false,
     "python.analysis.extraPaths": ["./"],
     "python.analysis.autoSearchPaths": true,
     "python.analysis.useLibraryCodeForTypes": true,
     "python.analysis.autoImportCompletions": true,
     "pylance.insidersChannel": "off",
     "ruff.path": ["./docker-ruff"],
     "ruff.interpreter": ["./docker-python"],
     "isort.path": ["./docker-isort"],
     "isort.interpreter": ["./docker-python"],
     "black-formatter.path": ["./docker-black"],
     "black-formatter.interpreter": ["./docker-python"],
     "[python]": {
       "editor.defaultFormatter": "ms-python.black-formatter",
       "editor.formatOnSave": true,
       "editor.codeActionsOnSave": {
         "source.organizeImports": "explicit",
         "source.fixAll.ruff": "explicit"
       }
     },
     "[django-html]": {
       "editor.defaultFormatter": null,
       "editor.formatOnSave": false
     },
     "[html]": {
       "editor.defaultFormatter": null,
       "editor.formatOnSave": false
     }
   }
   ```

5. **Optional: Reload VS Code window** (`Cmd+Shift+P` → "Developer: Reload Window")

**Benefits:**

- Keep your host Git setup and credentials
- Native VS Code performance
- All your extensions work normally
- Python execution uses container environment

**How it works:**

- VS Code runs on your host (fast, native experience)
- Python/linting/formatting execute in Docker (consistent environment)
- File editing happens on host with instant sync via volume mounts

**Technical Details:**

This approach uses Docker wrapper scripts (`docker-python`, `docker-black`, `docker-ruff`, etc.) that VS Code calls instead of local Python tools. The project includes:

- **Docker wrapper scripts**: Executable files that forward commands to the container
- **Pre-configured VS Code settings**: Located in `.vscode/settings.json` (see step 4 above)

The settings configure VS Code to:

- Point Python interpreter to `./docker-python`
- Configure Black formatter to use `./docker-black`
- Configure Ruff linting to use `./docker-ruff`
- Configure import sorting to use `./docker-isort`
- Enable format-on-save and organize imports

These wrappers automatically execute commands inside your running Docker container, so you get the benefits of the containerized environment without the complexity of dev containers.

**Note:** If you're setting up a fresh clone, the `.vscode/settings.json` file should already be included in the repository. If it's missing or you want to customize it, use the configuration shown in step 4 above.

### Switching Between Development Approaches

You can easily switch between different development approaches using the provided configuration scripts:

```bash
# Switch to local virtual environment (best IntelliSense)
./s/configure-vscode-local

# Switch to Docker wrapper approach (hybrid)
./s/configure-vscode-docker

# Start/restart the Docker environment
./s/dev
```

After switching approaches:

1. Reload your VS Code window (`Cmd+Shift+P` → "Developer: Reload Window")
2. Verify the Python interpreter is correct (`Cmd+Shift+P` → "Python: Select Interpreter")
3. Test that imports and formatting work as expected

**Configuration Backups:** The configuration scripts automatically backup your existing `.vscode/settings.json` to `.vscode/settings.json.backup` before making changes, so you can always revert if needed.

### Which VS Code Approach Should You Choose?

**Choose Local Virtual Environment if you:**

- Want the **best possible IntelliSense** with full import resolution and type hints
- Do lots of exploratory coding or refactoring where autocomplete is crucial
- Prefer immediate IDE feedback without any Docker overhead
- Don't mind managing a local Python environment alongside Docker

**Choose Dev Containers if you:**

- Want a completely isolated development environment
- Are on a team where everyone should have identical setups
- Don't mind setting up Git credentials in the container
- Prefer everything contained within Docker

**Choose Docker Python Integration if you:**

- Want a good balance between IDE features and environment consistency
- Prefer to keep your existing host Git setup and credentials  
- Want to use all your existing VS Code extensions without reconfiguration
- Are okay with slightly limited IntelliSense compared to local virtual environment

#### Quick VS Code Startup

For either approach, you can automatically open VS Code after starting containers:

```bash
# Option 1: Using the --code flag
./s/dev --code

# Option 2: Using environment variable
OPEN_VSCODE=true ./s/dev
```

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

### Docker Python Integration Issues

If you're using the Docker Python integration and encounter issues:

1. **Python interpreter not found**: Ensure containers are running:

   ```bash
   docker ps  # Should show census-web-1 and census-db-1 running
   ./s/dev    # Restart if needed
   ```

2. **Import errors or linting issues**: Reload VS Code window:
   - `Cmd+Shift+P` → "Developer: Reload Window"
   - Or restart VS Code completely

3. **"ENOENT" errors**: Usually means VS Code is trying to use host Python instead of Docker:
   - Check that Python interpreter is set to `./docker-python`
   - Verify `.vscode/settings.json` exists with correct configuration
   - Reload VS Code window after changes

4. **Wrapper scripts not executable**: Make them executable:

   ```bash
   chmod +x docker-python docker-black docker-ruff docker-isort
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
