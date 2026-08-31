"""Fetch free models from OpenRouter API."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from src.models import FreeModel

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
MODELS_JSON_PATH = Path(__file__).parent.parent / "models.json"
DOCS_MODELS_JSON_PATH = Path(__file__).parent.parent / "docs" / "models.json"


async def fetch_free_models() -> list[FreeModel]:
    """Fetch all free models from OpenRouter, sorted by coding_index desc."""
    params = {
        "max_price": 0,
        "sort": "coding-high-to-low",
        "limit": 1000,
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(OPENROUTER_MODELS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
    
    models = []
    for m in data.get("data", []):
        # Filter: only truly free (prompt=0 AND completion=0)
        pricing = m.get("pricing", {})
        if pricing.get("prompt") != "0" or pricing.get("completion") != "0":
            continue
        
        # Create FreeModel with all data
        model = FreeModel(**m)
        models.append(model)
    
    # Sort: coding_index desc (None last), then intelligence_index desc
    models.sort(key=lambda m: (
        m.coding_index is None,
        -(m.coding_index or -1),
        -(m.intelligence_index or -1),
    ))
    
    # Assign ranks
    for i, model in enumerate(models, 1):
        model.rank = i
    
    return models


def load_previous_models() -> list[FreeModel]:
    """Load previously fetched models from models.json."""
    if not MODELS_JSON_PATH.exists():
        return []
    
    try:
        with open(MODELS_JSON_PATH) as f:
            data = json.load(f)
        
        models = []
        for m in data.get("models", []):
            model = FreeModel(**m)
            models.append(model)
        return models
    except (json.JSONDecodeError, KeyError, TypeError):
        return []


def save_models(models: list[FreeModel]) -> None:
    """Save models to models.json (both root and docs)."""
    output = {
        "fetched_at": datetime.now(UTC).isoformat(),
        "count": len(models),
        "models": [m.model_dump(mode="json") for m in models],
    }
    
    # Save to root (for git history)
    MODELS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODELS_JSON_PATH, "w") as f:
        json.dump(output, f, indent=2)
    
    # Save to docs (for GitHub Pages)
    DOCS_MODELS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DOCS_MODELS_JSON_PATH, "w") as f:
        json.dump(output, f, indent=2)


def detect_changes(old_models: list[FreeModel], new_models: list[FreeModel]) -> dict[str, list[FreeModel]]:
    """Detect new, updated, and removed models."""
    old_map = {m.id: m for m in old_models}
    new_map = {m.id: m for m in new_models}
    
    changes = {"new": [], "updated": [], "removed": []}
    
    for mid, model in new_map.items():
        if mid not in old_map:
            changes["new"].append(model)
        else:
            old_model = old_map[mid]
            # Significant change: coding_index change >= 5, or context change >= 10%
            coding_diff = abs((model.coding_index or 0) - (old_model.coding_index or 0))
            context_diff = 0
            if old_model.context_length > 0:
                context_diff = abs(model.context_length - old_model.context_length) / old_model.context_length
            
            if coding_diff >= 5 or context_diff >= 0.1:
                changes["updated"].append(model)
    
    for mid, old_model in old_map.items():
        if mid not in new_map:
            changes["removed"].append(old_model)
    
    return changes


async def main() -> None:
    """Main entry point for fetching and saving models."""
    print("Fetching free models from OpenRouter...")
    models = await fetch_free_models()
    print(f"Found {len(models)} free models")
    
    old_models = load_previous_models()
    if old_models:
        print(f"Loaded {len(old_models)} previous models")
        changes = detect_changes(old_models, models)
        print(f"Changes: {len(changes['new'])} new, {len(changes['updated'])} updated, {len(changes['removed'])} removed")
    else:
        print("No previous data found (first run)")
        changes = {"new": models, "updated": [], "removed": []}
    
    save_models(models)
    print(f"Saved to {MODELS_JSON_PATH} and {DOCS_MODELS_JSON_PATH}")
    
    # Save changes for feed generation
    changes_path = Path(__file__).parent.parent / "docs" / "changes.json"
    changes_path.parent.mkdir(parents=True, exist_ok=True)
    with open(changes_path, "w") as f:
        json.dump({
            "fetched_at": datetime.now(UTC).isoformat(),
            "new": [m.model_dump(mode="json") for m in changes["new"]],
            "updated": [m.model_dump(mode="json") for m in changes["updated"]],
            "removed": [m.model_dump(mode="json") for m in changes["removed"]],
        }, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())