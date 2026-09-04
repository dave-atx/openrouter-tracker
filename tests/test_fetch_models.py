"""Tests for rankings API token volume parsing and model attachment."""

import json
from pathlib import Path

from src.fetch_models import attach_token_volumes, parse_token_volumes
from src.models import FreeModel

FIXTURE = Path(__file__).parent / "fixtures" / "rankings_sample.json"


def test_sums_prompt_completion_reasoning_per_model() -> None:
    """Total tokens = prompt + completion + reasoning for the target date."""
    payload = json.loads(FIXTURE.read_text())

    result = parse_token_volumes(payload, target_date="2026-09-03")

    assert result["free-org/sum-fields-20260303"] == 10 + 20 + 5
    assert result["free-org/example-free-20260101"] == 1000 + 2000 + 500


def test_filters_to_free_variant_only() -> None:
    """Standard/batch variants must be ignored so totals aren't double-counted."""
    payload = json.loads(FIXTURE.read_text())

    result = parse_token_volumes(payload, target_date="2026-09-03")

    # The standard variant has 999999 tokens; if it were included, this would
    # be ~2M instead of 3,500.
    assert result["free-org/example-free-20260101"] == 3500


def test_zero_activity_model_is_absent() -> None:
    """Models with zero token activity don't appear in rankings and so are
    absent from the result — callers should treat 'missing key' as 'no data'."""
    payload = json.loads(FIXTURE.read_text())

    result = parse_token_volumes(payload, target_date="2026-09-03")

    assert "free-org/another-free-20260202" not in result


def test_other_dates_are_ignored() -> None:
    """Only rows on the target date contribute to the totals."""
    payload = json.loads(FIXTURE.read_text())

    result = parse_token_volumes(payload, target_date="2026-09-03")

    assert "free-org/yesterday-20260101" not in result


def test_empty_payload_returns_empty_dict() -> None:
    """No rows → empty mapping; callers should treat this as 'no data'."""
    assert parse_token_volumes({"data": []}, target_date="2026-09-03") == {}


def test_missing_data_key_returns_empty_dict() -> None:
    """Malformed payload should not raise; return empty so fetch is robust."""
    assert parse_token_volumes({}, target_date="2026-09-03") == {}


def test_uses_most_recent_date_when_target_date_missing() -> None:
    """If target_date has no rows, fall back to the most recent available date.

    The rankings API publishes data with ~1 day lag, so a 'today' query
    typically returns no rows. We want the most recent day's totals.
    """
    payload = json.loads(FIXTURE.read_text())  # has 2026-09-03 and 2026-09-02

    result = parse_token_volumes(payload, target_date="2026-09-04")

    # 2026-09-03 is the most recent date in the fixture
    assert result["free-org/example-free-20260101"] == 3500
    assert result["free-org/sum-fields-20260303"] == 35
    assert "free-org/yesterday-20260101" not in result


def _make_model(slug: str, id_: str | None = None) -> FreeModel:
    """Build a minimal FreeModel with just enough to exercise attachment."""
    return FreeModel(
        id=id_ or slug,
        canonical_slug=slug,
        name=slug,
        description="",
        context_length=1000,
        architecture={
            "modality": "text->text",
            "input_modalities": ["text"],
            "output_modalities": ["text"],
            "tokenizer": "Test",
        },
        pricing={"prompt": "0", "completion": "0"},
        top_provider={"is_moderated": False},
    )


def test_attach_token_volumes_sets_volume_by_canonical_slug() -> None:
    """The volume map is keyed by canonical_slug and gets attached to the model."""
    models = [_make_model("org/foo-20260101"), _make_model("org/bar-20260202")]

    attach_token_volumes(models, {"org/foo-20260101": 1234, "org/bar-20260202": 5678})

    assert models[0].token_volume_24h == 1234
    assert models[1].token_volume_24h == 5678


def test_attach_token_volumes_leaves_missing_models_unchanged() -> None:
    """A model absent from the map keeps whatever token_volume_24h it had."""
    model = _make_model("org/missing-20260303")
    model.token_volume_24h = 42

    attach_token_volumes([model], {"org/other-20260101": 9999})

    assert model.token_volume_24h == 42
