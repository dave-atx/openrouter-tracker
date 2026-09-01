# OpenRouter Tracker - Agent Instructions

## Quick Commands

```bash
# Install deps
uv sync

# Full rebuild (fetch → HTML → Atom)
uv run python src/fetch_models.py && uv run python src/generate_html.py && uv run python src/generate_atom.py

# Lint
uv run ruff check .

# Test
uv run pytest

# Local preview
cd docs && python -m http.server 8000
```

## Architecture

- **Entry points**: `src/fetch_models.py`, `src/generate_html.py`, `src/generate_atom.py`
- **Data models**: `src/models.py` (Pydantic v2)
- **Template**: `src/templates/index.html.j2` (Jinja2)
- **Output**: `docs/` (committed to git, deployed via GitHub Pages)
- **History**: `models.json` (root, committed for version history)

## Key Behaviors

- **Free model filter**: Only `pricing.prompt == "0" AND pricing.completion == "0"`
- **Sort order**: `coding_index` desc (None last), then `intelligence_index` desc
- **OpenRouter URL**: `https://openrouter.ai/{model.id}` (not canonical_slug)
- **Change detection**: coding_index Δ≥5 OR context_length Δ≥10%
- **Error rate**: computed from `uptime_last_30m` (100 - avg uptime)
- **Throughput/Latency/Token Vol**: Always N/A (API returns null)

## CI Gotchas

- Workflow runs daily 6 AM UTC + on push to `src/**`, `pyproject.toml`, `uv.lock`, `.python-version`
- Must use `git stash; git pull --rebase; git stash pop` before commit to avoid conflicts
- `models.json` committed to root (history), `docs/` deployed via `actions/deploy-pages`

## Code Style

- Python 3.13, type hints required
- Ruff: line-length=100, target=py313
- Imports: `from src.models import ...` (not relative)

## Common Issues

| Problem | Fix |
|---------|-----|
| CI push rejected | Workflow uses stash/pull/pop pattern |
| Relative import error | Use `from src.models import ...` |
| Missing endpoint data | latency/throughput always null in API |
| Template not updating | Run all 3 generators in order |