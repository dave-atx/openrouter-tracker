"""Tests for humanize_tokens formatting across magnitude tiers."""

from src.models import humanize_tokens


def test_small_numbers_have_no_suffix() -> None:
    assert humanize_tokens(0) == "0"
    assert humanize_tokens(999) == "999"


def test_thousands_use_k_suffix() -> None:
    assert humanize_tokens(1_000) == "1.0K"
    assert humanize_tokens(2_500) == "2.5K"
    assert humanize_tokens(12_300) == "12.3K"


def test_millions_use_m_suffix() -> None:
    assert humanize_tokens(1_000_000) == "1.0M"
    assert humanize_tokens(4_300_000) == "4.3M"


def test_billions_use_b_suffix() -> None:
    assert humanize_tokens(1_000_000_000) == "1.0B"
    assert humanize_tokens(18_700_825_013) == "18.7B"


def test_trillions_use_t_suffix() -> None:
    assert humanize_tokens(1_000_000_000_000) == "1.0T"
    assert humanize_tokens(5_151_770_633_523) == "5.2T"
