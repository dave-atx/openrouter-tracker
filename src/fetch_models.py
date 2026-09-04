"""Fetch free models from OpenRouter API."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

from src.models import FreeModel

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_RANKINGS_URL = "https://openrouter.ai/api/frontend/v1/rankings/models"
MODELS_JSON_PATH = Path(__file__).parent.parent / "models.json"
DOCS_MODELS_JSON_PATH = Path(__file__).parent.parent / "docs" / "models.json"


async def fetch_endpoints(client: httpx.AsyncClient, details_url: str) -> dict | None:
    """Fetch endpoints data for a model."""
    try:
        resp = await client.get(f"https://openrouter.ai{details_url}")
        resp.raise_for_status()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to fetch endpoints for {details_url}: {e}")
        return None
    return resp.json()


async def fetch_token_volumes(client: httpx.AsyncClient) -> dict[str, int]:
    """Fetch today's per-model free-variant token totals from the rankings API.

    Returns a `{canonical_slug: total_tokens}` map for today (UTC). On any
    failure returns an empty dict so the rest of the pipeline still runs.
    """
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    try:
        resp = await client.get(OPENROUTER_RANKINGS_URL)
        resp.raise_for_status()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to fetch token volumes: {e}")
        return {}
    return parse_token_volumes(resp.json(), target_date=today)


def attach_token_volumes(models: list[FreeModel], volumes: dict[str, int]) -> None:
    """Mutate `models` in place: set token_volume_24h from the volumes map.

    Keyed by `canonical_slug` (matches `model_permaslug` from the rankings API).
    Models not in the map keep their existing token_volume_24h value.
    """
    for model in models:
        volume = volumes.get(model.canonical_slug)
        if volume is not None:
            model.token_volume_24h = volume


def parse_token_volumes(payload: dict, target_date: str | None = None) -> dict[str, int]:
    """Parse rankings payload into {canonical_slug: total_tokens} for one day.

    `target_date` is `YYYY-MM-DD`; rows match if their `date` field starts
    with that prefix (the API returns `YYYY-MM-DD HH:MM:SS`). If `target_date`
    is omitted or has no rows, fall back to the most recent date in the
    payload — the rankings API publishes with ~1 day lag, so 'today' is
    usually empty. Only `variant == "free"` rows with at least one non-zero
    token are counted, so totals aren't double-counted across standard/batch
    variants and so 'missing key' cleanly means 'no activity' for downstream
    callers. Total tokens = prompt + completion + reasoning.
    """
    rows = payload.get("data", [])
    if not rows:
        return {}

    # Pick the date we'll use: the explicit target if it has rows, otherwise
    # the lexicographically largest date in the payload (ISO dates sort that way).
    available_dates = sorted({r.get("date", "") for r in rows if r.get("date")})
    if target_date and any(d.startswith(target_date) for d in available_dates):
        date_prefix = target_date
    elif available_dates:
        date_prefix = available_dates[-1][:10]
    else:
        return {}

    totals: dict[str, int] = {}
    for row in rows:
        if not row.get("date", "").startswith(date_prefix):
            continue
        if row.get("variant") != "free":
            continue
        permaslug = row.get("model_permaslug")
        if not permaslug:
            continue
        total = (
            int(row.get("total_prompt_tokens") or 0)
            + int(row.get("total_completion_tokens") or 0)
            + int(row.get("total_native_tokens_reasoning") or 0)
        )
        if total > 0:
            totals[permaslug] = total
    return totals


def compute_performance_metrics(
    endpoints_data: dict | None,
) -> tuple[float | None, float | None, float | None, int | None]:
    """Compute aggregated performance metrics from endpoints."""
    if not endpoints_data:
        return None, None, None, None

    endpoints = endpoints_data.get("data", {}).get("endpoints", [])
    if not endpoints:
        return None, None, None, None

    latencies = []
    throughputs = []
    uptimes = []

    for ep in endpoints:
        latency = ep.get("latency_last_30m")
        throughput = ep.get("throughput_last_30m")
        uptime = ep.get("uptime_last_30m")

        if latency is not None:
            latencies.append(latency)
        if throughput is not None:
            throughputs.append(throughput)
        if uptime is not None:
            uptimes.append(uptime)

    avg_latency = sum(latencies) / len(latencies) if latencies else None
    avg_throughput = sum(throughputs) / len(throughputs) if throughputs else None
    error_rate = (100 - sum(uptimes) / len(uptimes)) if uptimes else None

    return avg_latency, avg_throughput, error_rate, None


async def fetch_free_models() -> list[FreeModel]:
    """Fetch all free models from OpenRouter, sorted by coding_index desc."""
    params = {
        "max_price": 0,
        "sort": "coding-high-to-low",
        "limit": 1000,
    }

    models = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(OPENROUTER_MODELS_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        for m in data.get("data", []):
            # Filter: only truly free (prompt=0 AND completion=0)
            pricing = m.get("pricing", {})
            if pricing.get("prompt") != "0" or pricing.get("completion") != "0":
                continue

            # Create FreeModel with all data
            model = FreeModel(**m)

            # Fetch endpoints for performance metrics
            if model.links and model.links.details:
                endpoints_data = await fetch_endpoints(client, model.links.details)
                avg_latency, avg_throughput, error_rate, _ = compute_performance_metrics(
                    endpoints_data
                )
                model.avg_latency_ms = avg_latency
                model.avg_throughput_tps = avg_throughput
                model.error_rate_pct = error_rate

            models.append(model)

        # Token volumes come from a separate call (single request, all models).
        volumes = await fetch_token_volumes(client)
        attach_token_volumes(models, volumes)

    # Sort: coding_index desc (None last), then intelligence_index desc
    models.sort(
        key=lambda m: (
            m.coding_index is None,
            -(m.coding_index or -1),
            -(m.intelligence_index or -1),
        )
    )

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


def detect_changes(
    old_models: list[FreeModel], new_models: list[FreeModel]
) -> dict[str, list[FreeModel]]:
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
                context_diff = (
                    abs(model.context_length - old_model.context_length) / old_model.context_length
                )

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
        print(
            f"Changes: {len(changes['new'])} new, {len(changes['updated'])} updated, {len(changes['removed'])} removed"
        )
    else:
        print("No previous data found (first run)")
        changes = {"new": models, "updated": [], "removed": []}

    save_models(models)
    print(f"Saved to {MODELS_JSON_PATH} and {DOCS_MODELS_JSON_PATH}")

    # Save changes for feed generation
    changes_path = Path(__file__).parent.parent / "docs" / "changes.json"
    changes_path.parent.mkdir(parents=True, exist_ok=True)

    with open(changes_path, "w") as f:  # noqa: ASYNC230 — sequential I/O at end of main()
        json.dump(
            {
                "fetched_at": datetime.now(UTC).isoformat(),
                "new": [m.model_dump(mode="json") for m in changes["new"]],
                "updated": [m.model_dump(mode="json") for m in changes["updated"]],
                "removed": [m.model_dump(mode="json") for m in changes["removed"]],
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    asyncio.run(main())
