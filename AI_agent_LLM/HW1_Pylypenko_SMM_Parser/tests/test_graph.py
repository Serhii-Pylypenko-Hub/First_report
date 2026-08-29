"""Інтеграційний тест LangGraph LLM→tools→LLM."""

from pathlib import Path

from youtube_trends_agent.agent import YouTubeTrendsAgent
from youtube_trends_agent.testing import ScriptedReActLLM
from youtube_trends_agent.youtube_client import FixtureYouTubeClient


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "youtube_videos.json"


def test_react_graph_returns_structured_report() -> None:
    agent = YouTubeTrendsAgent(
        client=FixtureYouTubeClient(FIXTURE),
        llm=ScriptedReActLLM(),
    )
    result = agent.run("Знайди тренди про AI agents за останні 7 днів")
    assert result["report"]["status"] == "success"
    assert result["report"]["mode"] == "thematic"
    assert result["report"]["top_by_views"]
    assert result["tool_calls"] == [
        "search_recent_videos",
        "enrich_video_statistics",
        "rank_trending_videos",
        "analyze_topic_signals",
    ]
