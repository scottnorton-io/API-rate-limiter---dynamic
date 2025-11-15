# Deployment Patterns & Environments

This page outlines a few recommended deployment patterns for
`dynamic-api-rate-limiter`, with a focus on macOS development,
CI, and containerized environments.

The goals:
- Keep secrets out of source control.
- Use the same rate-limiting behavior everywhere.
- Make local dev + CI as close as reasonably possible.

---

## 1. macOS Local Development (No Homebrew Required)

On macOS you can use the system Python 3 (from Xcode CLT or python.org
installers) and the built-in `venv` module. No Homebrew is required.

### 1.1. Create and activate a virtual environment

From your project root:

```bash
# Create a virtual environment in .venv
python3 -m venv .venv

# Activate it (bash/zsh)
source .venv/bin/activate

# Your shell prompt should now reflect the active venv
```

In Visual Studio Code, you can point the Python interpreter to `.venv/bin/python`
via the Command Palette → "Python: Select Interpreter".

### 1.2. Install the project (dev mode)

```bash
pip install --upgrade pip
pip install -e ".[dev]"
```

This gives you:
- The library itself
- Test tooling (pytest, ruff)
- Docs tooling (mkdocs)
- Security extras (keyring)

### 1.3. Use Keychain for secrets (recommended)

See `Security on macOS` in the docs for details. In short:

```bash
python -m keyring set dynamic-api-rate-limiter NOTION_TOKEN
python -m keyring set dynamic-api-rate-limiter OPENAI_API_KEY
```

Then in code, use the `get_secret()` helper pattern (see
`examples/example_keyring_macos.py`).

---

## 2. CI / GitHub Actions

In CI we typically:

- Do **not** rely on macOS Keychain.
- Use GitHub Actions secrets to inject tokens as env vars.
- Keep workflows deterministic and non-interactive.

Example (already in this repo):

- `ci.yml`: installs the project with `.[dev]`, runs lint + tests.
- `publish.yml`: builds and uploads distributions to PyPI when you push a tag.
- `docs.yml`: builds and deploys MkDocs site to GitHub Pages.

### 2.1. Providing secrets in CI

In GitHub:

1. Go to **Settings → Secrets and variables → Actions**.
2. Add secrets like:
   - `NOTION_TOKEN`
   - `OPENAI_API_KEY`
   - `SLACK_BOT_TOKEN`
3. In workflows, expose them as environment variables, e.g.:

   ```yaml
   env:
     NOTION_TOKEN: ${{ secrets.NOTION_TOKEN }}
     OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
   ```

Your scripts can then use the same `get_secret()` helper from the macOS
pattern, which will simply fall back to environment variables in CI.

---

## 3. Docker / Containerized Deployment

In containers, we avoid using system keyrings and rely on environment
variables or external secret managers (e.g., AWS SSM, GCP Secret Manager,
HashiCorp Vault).

### 3.1. Minimal Dockerfile pattern

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Copy only what is needed initially (for faster builds)
COPY pyproject.toml README.md ./
COPY api_ratelimiter ./api_ratelimiter
COPY examples ./examples

RUN pip install --upgrade pip         && pip install .

# At runtime, pass secrets via env vars:
#   - NOTION_TOKEN
#   - OPENAI_API_KEY
#   - etc.
#
# CMD here is just an example
CMD ["python", "-m", "examples.example_airtable"]
```

Then run with:

```bash
docker build -t dynamic-api-rate-limiter-demo .

docker run --rm       -e NOTION_TOKEN=...       -e OPENAI_API_KEY=...       dynamic-api-rate-limiter-demo
```

In more advanced setups, use your orchestrator's secret management
(Kubernetes, ECS, Nomad, etc.) instead of literal `-e` values.

---

## 4. Shared Patterns Across Environments

Regardless of environment, a few patterns repeat:

- **Single source for rate-limiting logic** – the library handles tokens,
  cool-downs, and backoff based on API feedback.
- **Separation of config and code** – API tokens, org IDs, and base IDs
  come from configuration (Keychain, env vars, or secret managers).
- **Consistent helpers** – e.g., `get_secret(name)` that first checks
  keyring (for local macOS) and then env vars (for CI/containers).

This makes it easy to reuse the same scripts in:

- Local development on macOS
- GitHub Actions CI
- Docker/Kubernetes deployment

without changing how the rate limiting itself works.
