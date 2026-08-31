# OpenRouter Free Models Tracker

A static site that tracks free models on OpenRouter, ranked by coding capability (Artificial Analysis Coding Index), with an Atom feed for new/updated models.

## Features

- **Live data** from OpenRouter API (`/api/v1/models`)
- **Free models only** (prompt=0 AND completion=0)
- **Ranked by coding ability** using Artificial Analysis Coding Index
- **Responsive table** with sortable columns
- **Dark mode** (auto-detects OS preference)
- **Apple-optimized** system fonts (San Francisco on macOS/iOS)
- **Copy model ID** button with toast notification
- **Atom 1.0 feed** for new/updated models
- **Daily updates** via GitHub Actions

## Live Site

https://dave-atx.github.io/openrouter-tracker/

## Atom Feed

https://dave-atx.github.io/openrouter-tracker/atom.xml

## Local Development

### Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) (fast Python package manager)

### Setup

```bash
# Clone the repo
git clone https://github.com/dave-atx/openrouter-tracker.git
cd openrouter-tracker

# Install dependencies
uv sync

# Fetch models and generate site
uv run python src/fetch_models.py
uv run python src/generate_html.py
uv run python src/generate_atom.py

# Output in docs/
ls docs/
# index.html  atom.xml  models.json
```

### Run with a local server

```bash
cd docs
python -m http.server 8000
# Open http://localhost:8000
```

## Project Structure

```
openrouter-tracker/
├── .github/workflows/update-models.yml  # GitHub Action (daily + on push)
├── src/
│   ├── fetch_models.py      # Fetch from OpenRouter API
│   ├── generate_html.py     # Render index.html with Jinja2
│   ├── generate_atom.py     # Generate Atom 1.0 feed
│   ├── models.py            # Pydantic data models
│   └── templates/
│       └── index.html.j2    # HTML template
├── docs/                    # GitHub Pages output (generated)
├── models.json              # Cached model data (committed for history)
├── pyproject.toml           # uv project config
├── uv.lock                  # Locked dependencies
├── .python-version          # Python 3.14
└── README.md
```

## GitHub Actions Workflow

The workflow (`.github/workflows/update-models.yml`):

1. Runs daily at 6 AM UTC
2. Runs on push to `src/`, `pyproject.toml`, `uv.lock`, `.python-version`
3. Runs manually via workflow_dispatch
4. Fetches free models from OpenRouter
5. Generates `index.html` and `atom.xml`
6. Commits `models.json` to git (keeps history)
7. Deploys `docs/` to GitHub Pages via `actions/deploy-pages`

## Data Model

Each model includes:

- **Rank** (by coding_index desc)
- **Name & ID** (copyable)
- **Coding Index** (Artificial Analysis, color-coded)
- **Intelligence Index** (Artificial Analysis)
- **Context Length** (humanized: 128K, 1M, etc.)
- **Modalities** (badges: 📝 Text, 🖼️ Image, 🎥 Video, 🔊 Audio)
- **Release Date** (from canonical_slug)
- **Reasoning** (mandatory/optional, supported efforts)
- **Description** (truncated, full on hover)
- **Expired badge** (if expiration_date passed)

## Atom Feed

The feed includes:
- New free models
- Significant updates (coding_index change ≥5, or context_length change ≥10%)
- Each entry: title, link to OpenRouter, summary with key specs

## License

MIT