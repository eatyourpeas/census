# Census

![GitHub License](https://img.shields.io/github/license/eatyourpeas/census?style=for-the-badge&color=%23BF40BF)
![Swagger Validator](https://img.shields.io/swagger/valid/3.0?specUrl=https%3A%2F%2Fcensus.eatyourpeas.dev%2Fapi%2Fschema&style=for-the-badge)
![GitHub Issues or Pull Requests](https://img.shields.io/github/issues/eatyourpeas/census?style=for-the-badge&color=%23BF40BF)
![GitHub Container Registry](https://ghcr-badge.egpl.dev/eatyourpeas/census/latest_tag?trim=major&label=latest&style=for-the-badge&color=%23BF40BF)
![GitHub Container Registry](https://ghcr-badge.egpl.dev/eatyourpeas/census/size?tag=latest&style=for-the-badge&color=%23BF40BF)

Census is an open source survey platform for medical audit and research. It supports OIDC (Google and Microsoft 365) and data is secure with encrypted identifiers only visible to users entering the data. Although built for the UK, it is fully i18n compliant and supports a range of languages. Survey creators build questions from a library of question types, or they can import them written in markdown. There is a growing library of lists to populate dropdowns for which contributions are welcome. There is also an API which supports user, survey and question management.

Try it out [here](https://census.eatyourpeas.dev)
>[!NOTE]
>This is in a sandbox dev environment and is for demo purposes only. Do not store patient or sensitive information here.

## 🐳 Self-Hosting

Census can be self-hosted using Docker. Pre-built multi-architecture images are available on GitHub Container Registry.

### Quick Start

```bash
# Download docker-compose file
wget https://raw.githubusercontent.com/eatyourpeas/census/main/docker-compose.registry.yml

# Configure environment
cp .env.selfhost .env
# Edit .env with your settings

# Start Census
docker compose -f docker-compose.registry.yml up -d
```

**📦 Docker Images:** [ghcr.io/eatyourpeas/census](https://github.com/eatyourpeas/census/pkgs/container/census)

**📚 Full Documentation:** See [Self-Hosting Guides](https://census.eatyourpeas.dev/docs/self-hosting-quickstart/)

## Documentation

Documentation can be found [here](https://census.eatyourpeas.dev/docs/)

## Getting Help & Contributing

### 💬 Community & Support

- **[Discussions](https://github.com/eatyourpeas/census/discussions)** - For questions, ideas, and community support
- **[Issues](https://github.com/eatyourpeas/census/issues)** - For bug reports and specific feature requests
- **[Documentation](https://census.eatyourpeas.dev/docs/)** - Complete guides and API documentation

### When to use what?

**Use Discussions for:**

- General questions about using Census
- Seeking advice on healthcare survey design
- Sharing your Census use cases
- Community announcements and updates
- Brainstorming new ideas before formal feature requests
- Getting help with deployment or configuration
- Asking "How do I...?" questions

**Use Issues for:**

- Reporting bugs or unexpected behavior
- Requesting specific features with detailed requirements
- Documentation corrections or improvements
- Security concerns (non-sensitive)

### Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on contributing code, documentation, and reporting issues.

## Issues

Please raise [issues](https://github.com/eatyourpeas/census/issues) for bugs and specific feature requests. For general questions and community support, use [Discussions](https://github.com/eatyourpeas/census/discussions).

## Technologies

Census is open source and customisable - admin users can change styles and icons.

The project is built on Django with Postgres 16, DaisyUI. It is dockerized and easy to deploy. It is a security-first project and follows OWASP principles. Sensitive data is encrypted.

## Quickstart

Local with Docker (recommended):

1. Copy environment file and edit as needed

   ```bash
   cp .env.example .env
   ```

2. Build and start services - a convenience `s` folder of bash scripts supports build of the containers.

   ```bash
   s/dev
   ```

3. Open <https://localhost:8000>

Without Docker (Python + Node):

- Install Poetry and Node 18+
- poetry install
- npm install && npm run build:css
- python manage.py migrate
- python manage.py createsuperuser
- python manage.py runserver

Container deployments:

- Run `python manage.py collectstatic --noinput` once the environment variables (including `DATABASE_URL`) are available.
- Start the app with `python manage.py migrate --noinput && gunicorn census_app.wsgi:application --bind 0.0.0.0:${PORT:-8000}`.

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
- Sensitive demographics encrypted per-survey using AES-GCM with derived keys
- API uses JWT (Bearer) auth; include Authorization header in requests
- Per-survey encryption keys with zero-knowledge architecture
- See [Patient Data Encryption](docs/patient-data-encryption.md) for detailed security documentation

## Tests

There are tests for all the endpoints, and in particular for all the functions relating to user and organisation management and permissions. There are also tests for survey creation and update, and relating to hashing and decryption of key identifiers.
