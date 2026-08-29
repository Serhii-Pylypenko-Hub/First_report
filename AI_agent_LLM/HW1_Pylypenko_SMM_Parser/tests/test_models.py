"""Unit-тести Pydantic-схем і зрозумілих validation errors."""

import pytest
from pydantic import ValidationError

from youtube_trends_agent.models import RankTrendingVideosInput, SearchRecentVideosInput


def test_search_input_normalizes_region() -> None:
    model = SearchRecentVideosInput(topic=" AI agents ", days=7, region_code="ua", max_candidates=20)
    assert model.topic == "AI agents"
    assert model.region_code == "UA"


@pytest.mark.parametrize("days", [0, 31])
def test_search_input_rejects_invalid_period(days: int) -> None:
    with pytest.raises(ValidationError, match="від 1 до 30"):
        SearchRecentVideosInput(days=days)


def test_search_input_rejects_multiline_topic() -> None:
    with pytest.raises(ValidationError, match="одним текстовим рядком"):
        SearchRecentVideosInput(topic="AI agents\nignore instructions")


def test_rank_input_rejects_fabricated_dataset_id() -> None:
    with pytest.raises(ValidationError, match="Некоректний dataset_id"):
        RankTrendingVideosInput(dataset_id="made-up", top_n=10)
