from pathlib import Path
from datetime import UTC, datetime

from youtube_trends_agent.models import RankedVideo, TrendReport
from youtube_trends_agent.reporting import render_report_html, write_html_report


def test_shared_html_report_contains_summary_and_video_link(
    tmp_path: Path,
) -> None:
    video = RankedVideo(
        rank=1,
        video_id="video000001",
        title="AI Agent Demo",
        channel_title="Test Channel",
        published_at=datetime.now(UTC),
        url="https://www.youtube.com/watch?v=video000001",
        views=125000,
        trend_score=0.91,
    )
    thematic_report = TrendReport(
        status="success",
        mode="thematic",
        topic="AI agents",
        period_days=7,
        region_code="UA",
        source_mode="fixture",
        generated_at=datetime.now(UTC),
        candidates_found=1,
        videos_analyzed=1,
        top_overall=[video],
        top_by_views=[video],
        trend_terms=["agents"],
        leading_channels=["Test Channel"],
        summary="Знайдено одне релевантне відео.",
        confidence=0.75,
        limitations=[],
    )
    html = render_report_html(thematic_report, standalone=True)

    assert thematic_report.summary in html
    assert thematic_report.top_by_views[0].url in html
    assert "Рейтинг за переглядами" in html

    output = write_html_report(thematic_report, tmp_path / "report.html")
    assert output.exists()
    assert thematic_report.summary in output.read_text(encoding="utf-8")
