"""Unit-тести max_steps, timeout і loop detection."""

from youtube_trends_agent.safety import LoopDetector, SafetyConfig, execution_limit_reason


def test_max_steps() -> None:
    config = SafetyConfig(max_steps=4, timeout_seconds=10, max_repeats=3)
    assert execution_limit_reason(step_count=4, started_at=100, config=config, now=101) == "max_steps"


def test_timeout() -> None:
    config = SafetyConfig(max_steps=10, timeout_seconds=2, max_repeats=3)
    assert execution_limit_reason(step_count=1, started_at=100, config=config, now=102) == "timeout"


def test_loop_detector_after_three_identical_calls() -> None:
    detector = LoopDetector(max_repeats=3)
    recent: list[str] = []
    call = [{"name": "search_recent_videos", "args": {"topic": "AI"}}]
    recent, loop = detector.update(recent, call)
    assert not loop
    recent, loop = detector.update(recent, call)
    assert not loop
    _, loop = detector.update(recent, call)
    assert loop
