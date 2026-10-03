# Backend

FastAPI, managed with [uv](https://docs.astral.sh/uv/).

## Setup

Requires uv. It installs the Python version from `.python-version` automatically.

```sh
uv sync
```

## Commands

| Command | What it does |
|---|---|
| `uv run fastapi dev` | Start dev server with reload at http://localhost:8000 (docs at `/docs`) |
| `uv run fastapi run` | Start production server |
| `uv run pytest` | Run tests |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |
| `uv add <pkg>` | Add a dependency (`--dev` for dev-only) |
