"""Unit-тести HTML parser helpers без мережі."""

from youtube_trends_agent.youtube_client import (
    extract_initial_data,
    parse_age_days,
    parse_compact_number,
    walk_video_renderers,
)


def test_extract_initial_data_and_renderer() -> None:
    html = '<script>var ytInitialData = {"items":[{"videoRenderer":{"videoId":"abc123"}}]};</script>'
    data = extract_initial_data(html)
    rows = list(walk_video_renderers(data))
    assert rows[0]["videoId"] == "abc123"


def test_parse_view_counts() -> None:
    assert parse_compact_number("1.2M views") == 1_200_000
    assert parse_compact_number("850K views") == 850_000
    assert parse_compact_number("1,5 млн переглядів") == 1_500_000


def test_parse_relative_age() -> None:
    assert parse_age_days("12 hours ago") == 0.5
    assert parse_age_days("3 days ago") == 3
    assert parse_age_days("1 week ago") == 7
