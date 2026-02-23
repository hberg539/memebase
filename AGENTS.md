# AGENTS.md

This file provides guidance to AI coding assistants when working with code in this repository.

Read `README.md` for project overview, setup, configuration, and usage.

## Commands

```bash
uv run main.py             # Run dev server on 0.0.0.0:5000
uv run pytest              # Run tests
docker-compose up          # Run with Docker
```

## Architecture

**Entrypoint:**
- `main.py` - App entrypoint (inits DB, starts Flask server)

**Backend (Python/Flask) - `src/memebase/`:**
- `src/memebase/common.py` - Shared constants (paths, allowed extensions, content-type map, sort options)
- `src/memebase/app.py` - Flask routes and all API endpoints
- `src/memebase/service.py` - Business logic extracted from routes (file collision handling, meme registration, file path lookup)
- `src/memebase/ai.py` - AI integration via LiteLLM for meme analysis (returns name/description/tags as JSON)
- `src/memebase/db.py` - SQLite database layer (schema, queries, all SQL)
- `src/memebase/util.py` - Shared utilities (filename sanitization, file hashing, config loading, tomllib re-export)

**Tests - `tests/`:**
- `tests/test_util.py` - Utility tests (filename sanitization, tag normalization)
- `tests/test_ai.py` - Prompt building and AI response parsing tests
- `tests/test_service.py` - Service layer tests (path resolution, meme registration)

**Frontend (vanilla JS, no build):**
- `static/js/grid.js` - Grid rendering, search (300ms debounce), faceted filtering, pagination
- `static/js/modal.js` - Single meme view/edit dialog, auto-detect trigger
- `static/js/select.js` - Multi-select, bulk tag editing, bulk auto-detect with parallelization
- `static/js/upload.js` - Drag-and-drop file upload
- `static/js/utils.js` - Shared helpers (HTML escape, clipboard copy, icon rendering, file extension utils)
- `templates/base.html` - Base template with CSS/JS loading
- `templates/index.html` - Main SPA page structure

## Key Design Decisions

- **UUID primary key**: Memes use a generated UUID as PK, with SHA256 as a unique field for deduplication
- **SHA256 deduplication**: Files are hashed on upload to prevent duplicates
- **Faceted search**: `/api/memes` recalculates filter counts excluding each dimension (extension, tag, favorite) so counts stay accurate as filters are applied
- **Optimistic UI**: Frontend updates state immediately, then syncs with backend

## Database Schema

Two tables: `memes` (uuid PK, sha256 UNIQUE, size, filename, description, favorite, timestamps) and `tags` (uuid + tag compound PK, cascading delete from memes).

## CI

GitHub Actions runs `uv run pytest` on every push and PR (`.github/workflows/test.yml`).

## Rules

- Never commit or push without being explicitly asked to.
- When features, configuration, or usage changes, update `README.md` accordingly.
- `README.md` is user-facing - write it in a laid-back, casual tone. The audience is end-users and shitposters, not enterprise architects. Keep it fun and approachable.
- Never break the user's SQLite database. Schema changes must be backwards-compatible so existing data remains valid when the user updates the Docker image or pulls the latest code. Use additive migrations (new columns with defaults, new tables) instead of destructive changes (dropping/renaming columns, changing types). If a change would break existing databases, alert the developer before proceeding.
- Never use em dashes. Use regular dashes (-) or rewrite the sentence instead.
- Never use special Unicode characters in comments or strings that can't be typed on a standard keyboard. Stick to plain ASCII (e.g. use `--` not `──`, use `...` not `…`, use regular quotes not curly quotes).

## Code Style

- Write Pythonic, idiomatic code. Prefer built-in patterns, standard library idioms, and clean readable code over clever tricks.
- Always use type hints on function signatures (parameters and return types). Use modern Python syntax (`list[str]`, `X | None`) instead of `typing.List` or `typing.Optional`.
- Use absolute package imports (`from memebase.x import ...`), never bare `from x import ...`.
- Use `pathlib.Path` instead of `os.path` for filesystem operations.

## Commit Convention

This project uses [Conventional Commits](https://www.conventionalcommits.org/). A `pre-commit` hook enforces the format. Read `release-please-config.json` for the full list of types and changelog sections.

**Format:** `<type>(<scope>): <description>` (body and footer are optional)

**Scopes** (optional): `api`, `db`, `ai`, `ui`, `config`

**Description** starts with a lowercase letter (e.g. `fix: install xyz`, not `fix: Install xyz`).

**Commit body**: Only add a body/description if the change is not obvious to developers reading the diff. If you add one, it should explain the *why*, not restate the *what*.

**Breaking changes** bump the major version. Indicate with a `!` after the type/scope or a `BREAKING CHANGE:` footer.
