# Contributing

We welcome contributions of all kinds—bug reports, feature requests, docs, and code. Before opening a new issue, please search the existing [Issues](https://github.com/eatyourpeas/census/issues) to avoid duplicates. If you plan to work on something, feel free to open an issue to discuss it first. Pull Requests are very welcome—small, focused PRs are easiest to review.

Please follow these guidelines to keep the codebase healthy and secure.

## Tests and dummy credentials

Secret scanners (e.g. GitGuardian, GitHub Secret Scanning, ggshield) run on this repo. To avoid false positives:

- Use non-secret-like dummy values in tests.
  - Prefer a low-entropy constant: `test-pass`
  - Avoid realistic patterns: long base64/hex, JWT-like strings (`xxx.yyy.zzz`), PEM blocks, cloud key prefixes, or "CorrectHorseBatteryStaple"-style phrases.
- If you need to construct tokens for parsing, break known signatures (shorten them, remove prefixes) so they don’t match detectors.
- If a finding still occurs, resolve it one of these ways (in this order):
  1. Refactor to a less-detectable string.
  2. Use a precise per-secret ignore via ggshield (CLI) tied to the signature.
  3. As a last resort, add an inline allowlist comment above the line if your team policy permits:
     - Python: `# pragma: allowlist secret`

## Commit hygiene

- Keep changes focused; write clear commit messages.
- Link issues/PRs where relevant.
- Run the test suite locally before pushing.

## Security practices

- Do not commit real secrets, keys, or tokens.
- Use `.env.example` as a template; never commit your real `.env`.
- Follow existing security patterns (CSP, CSRF, HSTS, rate limiting) when adding features.

## Style

- Python: ruff/black-compatible; follow existing patterns.
- Frontend: Tailwind + DaisyUI; keep components consistent with the current design.

### Linting & formatting

We use three tools for Python code quality:

- Ruff: fast linter (the primary style/lint engine)
- Black: code formatter (opinionated, no config)
- isort: import sorting (configured to match Black)

Local usage (poetry-managed):

```sh
# Lint
poetry run ruff check .

# Format (apply changes)
poetry run black .
poetry run isort --profile black .

# Verify (no changes should be needed)
poetry run black --check .
poetry run isort --profile black --check-only .
```

Pre-commit (optional but recommended): install hooks once, then they run automatically on commits.

```sh
pip install pre-commit
pre-commit install
# To run on entire repo
pre-commit run --all-files
```

CI runs the following in the lint phase (see `.github/workflows/ci.yml`):

- `ruff check .`
- `black --check .`
- `isort --profile black --check-only .`

## Docs

- Update `docs/` when behavior or APIs change.
- Keep examples accurate and minimal.
