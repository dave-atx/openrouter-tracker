"""Generate HTML page from models data."""

import json
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.models import FreeModel, coding_index_color, humanize_tokens, reasoning_summary

TEMPLATES_DIR = Path(__file__).parent / "templates"
ASSETS_DIR = TEMPLATES_DIR / "assets"
DOCS_DIR = Path(__file__).parent.parent / "docs"
MODELS_JSON_PATH = Path(__file__).parent.parent / "models.json"

MODALITY_LABELS = {
    "text": "Text",
    "image": "Image",
    "video": "Video",
    "audio": "Audio",
    "file": "File",
}
MODALITY_ORDER = ["text", "image", "video", "audio", "file"]


def modalities_present(models: list[FreeModel]) -> list[str]:
    """Distinct input modalities across all models, in canonical display order."""
    seen = {m for model in models for m in model.architecture.input_modalities}
    return [m for m in MODALITY_ORDER if m in seen]


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


def get_last_updated() -> str:
    """Get the last updated timestamp."""
    if not MODELS_JSON_PATH.exists():
        return "Unknown"

    with open(MODELS_JSON_PATH) as f:
        data = json.load(f)

    fetched_at = data.get("fetched_at")
    if fetched_at:
        try:
            dt = datetime.fromisoformat(fetched_at)
            return dt.strftime("%B %d, %Y at %H:%M UTC")
        except ValueError:
            pass
    return "Unknown"


def main() -> None:
    """Generate index.html from template."""
    models = load_models()
    last_updated = get_last_updated()

    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Add custom filters and globals
    env.filters["humanize_tokens"] = humanize_tokens
    env.filters["coding_index_color"] = coding_index_color
    env.filters["reasoning_summary"] = reasoning_summary
    env.globals["coding_index_color"] = coding_index_color

    template = env.get_template("index.html.j2")

    html = template.render(
        models=models,
        last_updated=last_updated,
        total_count=len(models),
        github_username="dave-atx",
        repo_name="openrouter-tracker",
        modality_list=modalities_present(models),
        modality_labels=MODALITY_LABELS,
    )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DOCS_DIR / "index.html"
    with open(output_path, "w") as f:
        f.write(html)

    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, DOCS_DIR / "assets", dirs_exist_ok=True)

    print(f"Generated {output_path} with {len(models)} models")


if __name__ == "__main__":
    main()
