"""Generate Atom 1.0 feed from models data."""

import json
from datetime import UTC, datetime
from pathlib import Path

from feedgen.feed import FeedGenerator

from src.models import FreeModel, humanize_tokens, reasoning_summary

DOCS_DIR = Path(__file__).parent.parent / "docs"
CHANGES_JSON_PATH = Path(__file__).parent.parent / "docs" / "changes.json"
MODELS_JSON_PATH = Path(__file__).parent.parent / "models.json"

GITHUB_USERNAME = "dave-atx"
REPO_NAME = "openrouter-tracker"
BASE_URL = f"https://{GITHUB_USERNAME}.github.io/{REPO_NAME}"
FEED_URL = f"{BASE_URL}/atom.xml"


def load_changes() -> dict:
    """Load changes from changes.json."""
    if not CHANGES_JSON_PATH.exists():
        return {"new": [], "updated": [], "removed": []}

    with open(CHANGES_JSON_PATH) as f:
        return json.load(f)


def load_models() -> list[FreeModel]:
    """Load models from models.json."""
    if not MODELS_JSON_PATH.exists():
        return []

    with open(MODELS_JSON_PATH) as f:
        data = json.load(f)

    models = []
    for m in data.get("models", []):
        model = FreeModel(**m)
        models.append(model)
    return models


def get_fetched_at() -> datetime:
    """Get the fetch timestamp."""
    if not MODELS_JSON_PATH.exists():
        return datetime.now(UTC)

    with open(MODELS_JSON_PATH) as f:
        data = json.load(f)

    fetched_at = data.get("fetched_at")
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt
        except ValueError:
            pass
    return datetime.now(UTC)


def create_feed_entry(fg: FeedGenerator, model: FreeModel, is_new: bool = True) -> None:
    """Create an Atom feed entry for a model."""
    entry = fg.add_entry()

    title = f"{model.name} ({model.id})"
    if not is_new:
        title += " [Updated]"
    entry.title(title)

    entry.link(href=f"https://openrouter.ai/{model.canonical_slug}")

    # Use canonical_slug date for ID
    entry.id(f"tag:openrouter.ai,{model.canonical_slug.split('-')[-1]}:{model.id}")

    # Updated: release date for new, fetch time for updates
    updated = model.release_date.replace(tzinfo=UTC) if is_new else get_fetched_at()
    entry.updated(updated)

    # Summary with key details
    summary_parts = [
        f"<p>{model.description}</p>",
        "<ul>",
        f"<li><strong>Coding Index:</strong> {model.coding_index if model.coding_index is not None else 'N/A'}</li>",
        f"<li><strong>Intelligence Index:</strong> {model.intelligence_index if model.intelligence_index is not None else 'N/A'}</li>",
        f"<li><strong>Context Length:</strong> {humanize_tokens(model.context_length)} tokens</li>",
        f"<li><strong>Modalities:</strong> {', '.join(model.modalities_badges)}</li>",
        f"<li><strong>Reasoning:</strong> {reasoning_summary(model.reasoning)}</li>",
        f"<li><strong>Release Date:</strong> {model.release_date.strftime('%Y-%m-%d')}</li>",
    ]

    if model.is_expired:
        summary_parts.append(
            "<li><strong>⚠️ Expired:</strong> This model has an expiration date</li>"
        )

    if model.expiration_date:
        summary_parts.append(f"<li><strong>Expires:</strong> {model.expiration_date}</li>")

    summary_parts.append("</ul>")

    entry.summary("\n".join(summary_parts), type="html")


def main() -> None:
    """Generate atom.xml feed."""
    changes = load_changes()
    new_models = [FreeModel(**m) for m in changes.get("new", [])]
    updated_models = [FreeModel(**m) for m in changes.get("updated", [])]

    # Sort by release date (newest first)
    all_entries = sorted(
        [(m, True) for m in new_models] + [(m, False) for m in updated_models],
        key=lambda x: x[0].release_date,
        reverse=True,
    )

    fg = FeedGenerator()
    fg.title("OpenRouter Free Models")
    fg.subtitle("New and updated free models on OpenRouter")
    fg.link(href=FEED_URL, rel="self", type="application/atom+xml")
    fg.link(href=BASE_URL, rel="alternate", type="text/html")
    fg.id(f"tag:github.com,{GITHUB_USERNAME}:{REPO_NAME}")
    fg.updated(get_fetched_at())
    fg.author(name=GITHUB_USERNAME)

    for model, is_new in all_entries:
        create_feed_entry(fg, model, is_new)

    # If no changes, add a note
    if not all_entries:
        entry = fg.add_entry()
        entry.title("No new or updated free models")
        entry.link(href=BASE_URL)
        entry.id(f"tag:github.com,{GITHUB_USERNAME}:{REPO_NAME}:no-changes")
        entry.updated(get_fetched_at())
        entry.summary(
            "No new free models or significant updates detected in this fetch.", type="text"
        )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOCS_DIR / "atom.xml"
    fg.atom_file(str(output_path), pretty=True)

    print(f"Generated {output_path} with {len(all_entries)} entries")


if __name__ == "__main__":
    main()
