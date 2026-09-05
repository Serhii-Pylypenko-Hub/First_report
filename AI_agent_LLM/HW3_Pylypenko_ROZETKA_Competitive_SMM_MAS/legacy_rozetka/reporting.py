"""Спільне представлення результату для Notebook, CLI та test runner."""

from __future__ import annotations

from copy import deepcopy


DEFAULT_REQUEST = (
    "Проаналізуй контент-маркетинг ROZETKA в Instagram, Facebook, Threads і Telegram "
    "за 30 днів: частоту, формати, перегляди, лайки, коментарі, funnel, "
    "inferred-аудиторію та 5 найсильніших патернів."
)


def build_agent_result(values: dict) -> dict:
    """Повернути однаковий канонічний результат незалежно від способу запуску."""

    analysis = deepcopy(values.get("analysis", {}))
    return {
        "brand": analysis.get("brand", "ROZETKA"),
        "period_days": analysis.get("period_days", 30),
        "posts_collected": len(values.get("posts", [])),
        "source_status": deepcopy(values.get("source_status", {})),
        "knowledge_hits": len(values.get("knowledge_hits", [])),
        "analysis": analysis,
        "workflow": {
            "goal": values.get("goal"),
            "plan": list(values.get("plan", [])),
            "current_step": values.get("current_step", 0),
            "report_status": values.get("report_status"),
            "report_path": values.get("report_path"),
            "completed": values.get("completed", False),
        },
    }
