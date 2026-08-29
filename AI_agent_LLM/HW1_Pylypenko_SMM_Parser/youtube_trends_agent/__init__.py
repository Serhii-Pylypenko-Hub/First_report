"""ReAct-агент для пошуку та аналізу YouTube-трендів.

Імпорти ліниві, щоб unit-тести parser/models не завантажували весь LangGraph.
"""

from typing import Any

__all__ = ["TrendReport", "YouTubeTrendsAgent"]


def __getattr__(name: str) -> Any:
    if name == "YouTubeTrendsAgent":
        from .agent import YouTubeTrendsAgent

        return YouTubeTrendsAgent
    if name == "TrendReport":
        from .models import TrendReport

        return TrendReport
    raise AttributeError(name)
