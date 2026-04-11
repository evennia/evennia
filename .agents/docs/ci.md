# CI/CD

## Workflows (`.github/workflows/`)

### Test Suite (`github_action_test_suite.yml`)

Triggers on push/PR to `main` or `develop` (skips docs-only changes).

**Matrix**: Python 3.12, 3.13, 3.14 across three database jobs:

| Job | DB | Timeout | Notes |
|---|---|---|---|
| test-sqlite | SQLite | 30m | Coverage on Python 3.12 only |
| test-mysql | MySQL 8.0 | 35m | utf8mb3 charset, `--keepdb --parallel` |
| test-postgresql | PostgreSQL 14 | 60m | Sequential, no `--keepdb` (stale DB issues) |

**Deploy step** (main branch only, after all tests pass): builds and pushes Docker image `evennia/evennia:latest` to DockerHub.

### Doc Build (`github_action_build_docs.yml`)

Triggers on push/PR to `main`/`develop` when `docs/` or `evennia/contrib/` changes. Builds with Sphinx via `make release` in `docs/`. Requires a full game dir init + migrations before building.

### Other Workflows

- `codeql-analysis.yml` — Security scanning (JS + Python), weekly + on push/PR
- `github_action_issue_to_project.yml` — Auto-adds issues to GitHub Projects

## Custom Actions (`.github/actions/`)

- **`setup-database/`** — Waits for DB readiness, creates MySQL database/users, grants privileges. SQLite needs no setup.
- **`run-tests/`** — Sets up Python, installs Evennia, inits test game dir, copies DB-specific settings from `.github/workflows/{db}_settings.py`, runs migrations, then tests.

## Database Settings (`.github/workflows/`)

Each DB type has a settings file copied into the test game dir:

- `sqlite3_settings.py` — Minimal, uses Evennia defaults
- `mysql_settings.py` — utf8mb3 charset, `STRICT_TRANS_TABLES`, `innodb_strict_mode`
- `postgresql_settings.py` — Aggressive timeouts for CI: `lock_timeout=30s`, `statement_timeout=5m`

## Docker (`Dockerfile`)

- Base: `python:3.13-alpine`
- Build arg `EVENNIA_INSTALL_MODE`: `editable` (default, mounts source) or `pypi`
- Ports: 4000 (telnet), 4001 (web), 4002 (websocket)
- Volume: `/usr/src/game`
- Entrypoint: `bin/unix/evennia-docker-start.sh`

## Secrets

- `COVERALLS_REPO_TOKEN` — Coverage reporting
- `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` — Docker publishing
- `EVENNIA_TICKET_TO_PROJECT` — Issue automation
