"""Структурований Plan-and-Execute без маршрутизації за текстовими маркерами."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import ExecutionPlan, PlanOperation, PlanStep


def default_plan() -> ExecutionPlan:
    operations = [
        (PlanOperation.COLLECT_BRAND_CONTENT, "collector"),
        (PlanOperation.SEARCH_KNOWLEDGE, "researcher"),
        (PlanOperation.NORMALIZE_METRICS, "analyst"),
        (PlanOperation.COMPARE_COMPETITORS, "analyst"),
        (PlanOperation.GENERATE_DRAFTS, "strategist"),
        (PlanOperation.LANGUAGE_REVIEW, "language"),
        (PlanOperation.VERIFY_RESULTS, "verifier"),
        (PlanOperation.PREPARE_EXPORT, "report"),
    ]
    return ExecutionPlan(
        goal="Порівняти рекламу п'яти брендів і створити перевірені пости ROZETKA.",
        steps=[
            PlanStep(step_id=index, operation=operation, agent_name=agent, depends_on=[] if index == 1 else [index - 1])
            for index, (operation, agent) in enumerate(operations, start=1)
        ],
    )


class StructuredPlanExecutor:
    """Диспетчер викликає handler лише за enum operation, ніколи за підрядком."""

    def __init__(self, handlers: dict[PlanOperation, Callable[[dict[str, Any]], dict[str, Any]]]) -> None:
        self.handlers = handlers

    def execute_step(self, step: PlanStep, state: dict[str, Any]) -> dict[str, Any]:
        handler = self.handlers.get(step.operation)
        if handler is None:
            raise ValueError(f"Для операції {step.operation.value} handler не зареєстровано")
        return handler(state)
