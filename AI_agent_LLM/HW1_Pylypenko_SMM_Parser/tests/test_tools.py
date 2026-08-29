"""Окремі інтеграційні тести всіх чотирьох tools."""

import json
from pathlib import Path

from youtube_trends_agent.store import TrendDataStore
from youtube_trends_agent.tools import build_tools
from youtube_trends_agent.youtube_client import FixtureYouTubeClient


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "youtube_videos.json"


def test_full_tool_chain() -> None:
    store = TrendDataStore()
    tools = {item.name: item for item in build_tools(FixtureYouTubeClient(FIXTURE), store)}

    search = json.loads(
        tools["search_recent_videos"].invoke(
            {"topic": "AI agents", "days": 7, "region_code": "UA", "max_candidates": 50}
        )
    )
    assert search["candidates_found"] >= 10

    statistics = json.loads(
        tools["enrich_video_statistics"].invoke({"dataset_id": search["dataset_id"]})
    )
    assert statistics["videos_enriched"] == search["candidates_found"]

    rankings = json.loads(
        tools["rank_trending_videos"].invoke(
            {
                "dataset_id": search["dataset_id"],
                "metrics": ["trend_score", "views"],
                "top_n": 20,
            }
        )
    )
    assert rankings["rankings"]["views"][0]["views"] >= rankings["rankings"]["views"][-1]["views"]
    assert rankings["rankings"]["views"][0]["url"].startswith("https://www.youtube.com/watch?v=")

    signals = json.loads(
        tools["analyze_topic_signals"].invoke({"dataset_id": search["dataset_id"], "top_n": 5})
    )
    assert signals["trend_terms"]
    assert signals["leading_channels"]
