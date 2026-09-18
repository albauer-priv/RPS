# Deployment Runbook

RPS ships as a Docker image built and published automatically to GitHub Container Registry (GHCR) on every push to `main`.

---

## Requirements

| Requirement | Detail |
|-------------|--------|
| Docker + Docker Compose | Docker 24+ with Compose v2 |
| GHCR access | Public image; no credentials needed to pull |
| OpenAI-compatible API key | Required: `RPS_LLM_API_KEY` |
| intervals.icu credentials | Required: `ATHLETE_ID`, `API_KEY` |
| Persistent volume | `./runtime` — must survive container restarts |

---

## Repo Structure

```
Dockerfile              # Image definition (python:3.13-slim, Streamlit on port 8501)
docker-compose.yml      # Single-service compose file (pulls from GHCR)
.dockerignore           # Excludes runtime/, .venv/, .env from image
.env.example            # Template for all required and optional env vars
requirements.txt        # Python dependencies (pinned for reproducibility)
```

---

## Build Process

The image is built automatically by `.github/workflows/ghcr-image.yml`:

- **Trigger:** push to `main` or manual `workflow_dispatch`
- **Registry:** `ghcr.io/albauer-priv/rps`
- **Tags:** `latest` + short SHA (e.g. `sha-abc1234`)
- **Cache:** GitHub Actions cache (layer cache, `mode=max`)
- **Build arg:** `GIT_COMMIT` — baked into the image as `$GIT_COMMIT` env var

To build locally:

```bash
docker build -t rps:local .
```

---

## Deploy Process

**1. Create `.env` from the template**

```bash
cp .env.example .env
# Edit .env and fill in at minimum:
#   RPS_LLM_API_KEY, ATHLETE_ID, API_KEY
```

**2. Create the runtime directory**

```bash
mkdir -p runtime
```

**3. Pull and start**

```bash
docker compose pull
docker compose up -d
```

**4. Verify**

```bash
docker compose logs -f
# App is ready when Streamlit prints "You can now view your Streamlit app"
# Health: http://localhost:8501/_stcore/health
```

**5. Update to a new release**

```bash
docker compose pull
docker compose up -d
```

---

## Data & Key Handling

### Runtime data

All persistent state lives in `./runtime/` on the host, mounted into the container at `/app/runtime`:

```
runtime/
  athletes/<athlete_id>/          # Per-athlete workspace
    artifacts/                    # Planning artifacts (JSON)
    runs/                         # Run history
    logs/                         # rps.log
    locks/                        # File-based run locks (auto-recovered on startup)
```

The `runtime/` directory is **excluded from the Docker image** via `.dockerignore`. Never delete it without a backup.

### Environment variables / secrets

All secrets are passed via `.env` (never baked into the image):

| Variable | Required | Description |
|----------|----------|-------------|
| `RPS_LLM_API_KEY` | Yes | OpenAI-compatible API key |
| `RPS_LLM_BASE_URL` | No | Custom base URL (default: OpenAI) |
| `RPS_LLM_MODEL` | No | Model name (default: `gpt-5.4-mini`) |
| `ATHLETE_ID` | Yes | intervals.icu athlete ID |
| `API_KEY` | Yes | intervals.icu API key |
| `RPS_USERS_FILE` | No | Path to `users.yaml` for opt-in auth |

See `.env.example` for the full list including optional tuning vars.

### Opt-in authentication

By default the app is open (no login). To enable per-user login:

**1. Create `config/users.yaml`:**

```yaml
users:
  - username: alice
    athlete_id: "i123456"
    password_hash: "sha256:<hash>"     # see step 2
    llm_api_key: "sk-..."              # optional per-user key override
```

**2. Hash a password:**

```bash
docker run --rm ghcr.io/albauer-priv/rps:latest \
  python -m rps.ui.auth hash <password>
```

**3. Mount the config and set the env var in `docker-compose.yml`:**

```yaml
volumes:
  - ./runtime:/app/runtime
  - ./config:/app/config:ro
environment:
  RPS_USERS_FILE: /app/config/users.yaml
```

---

## Rollback

Each push produces a `sha-<short>` tag alongside `latest`. To roll back:

```bash
# docker-compose.yml: change image to the previous SHA tag
image: ghcr.io/albauer-priv/rps:sha-abc1234
docker compose up -d
```

The `runtime/` data is forward-compatible; no migration is needed for rollbacks.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Container exits immediately | Missing required env var | Check `docker compose logs` for the error |
| "Athlete lock busy" after crash | Stale lock file | Lock auto-recovered on next startup; or delete `runtime/athletes/<id>/locks/` |
| Planning runs stuck as RUNNING | Orphaned queue item | Recovered automatically on container restart |
| `/_stcore/health` returns 503 | Streamlit still starting | Wait ~10 s; check logs |
