"""LangGraph ReAct-агент для загальних і тематичних YouTube-трендів."""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from .logger import TrajectoryLogger, compact
from .llm_factory import create_chat_model
from .models import RankedVideo, TrendReport
from .safety import LoopDetector, SafetyConfig, execution_limit_reason
from .spec import AGENT_SPEC
from .store import TrendDataStore
from .tools import build_tools
from .youtube_client import YouTubeClient


class AgentState(TypedDict, total=False):
    """Стан, який передається між вузлами LangGraph."""

    messages: Annotated[list[AnyMessage], add_messages]
    step_count: int
    started_at: float
    stop_reason: str
    recent_tool_calls: list[str]
    final_report: dict


SYSTEM_PROMPT = """Ти — read-only ReAct-агент для аналізу YouTube-трендів.

Працюй українською. Дотримуйся строгого порядку:
1) search_recent_videos;
2) enrich_video_statistics з точним dataset_id з кроку 1;
3) rank_trending_videos для trend_score і views, top_n не більше 20;
4) analyze_topic_signals;
5) коротко повідом, що аналіз завершено.

Порожня topic — загальні тренди, непорожня topic — тематичні. Не вигадуй dataset_id,
метрики або посилання. Не повторюй однаковий tool call. Не викликай інструменти,
яких немає. Усі фактичні дані бери тільки з tool results.
"""


def _tool_calls(message: AnyMessage) -> list[dict]:
    calls = getattr(message, "tool_calls", None) or []
    return [
        {
            "name": str(call.get("name", "")),
            "args": dict(call.get("args") or {}),
            "id": str(call.get("id", "")),
        }
        for call in calls
    ]


class YouTubeTrendsAgent:
    """Збирає ізольований LangGraph для кожного запуску."""

    def __init__(
        self,
        *,
        client: YouTubeClient,
        llm: BaseChatModel | None = None,
        llm_provider: str | None = None,
        safety: SafetyConfig | None = None,
    ) -> None:
        self.client = client
        self.llm = llm or create_chat_model(llm_provider)
        self.safety = safety or SafetyConfig()

    def run(self, query: str, trajectory_path: str | Path | None = None) -> dict:
        """Виконати один запит і повернути report, trajectory та службові метрики."""

        run_id = f"run-{uuid.uuid4().hex[:10]}"
        logger = TrajectoryLogger(run_id)
        store = TrendDataStore()
        detector = LoopDetector(self.safety.max_repeats)
        tools = build_tools(self.client, store)
        tool_node = ToolNode(tools, handle_tool_errors=True)
        llm_with_tools = self.llm.bind_tools(tools)

        def limit_reason(state: AgentState) -> str:
            return execution_limit_reason(
                step_count=state.get("step_count", 0),
                started_at=state.get("started_at", logger.started_at),
                config=self.safety,
            )

        def agent_node(state: AgentState) -> dict:
            started = time.monotonic()
            reason = limit_reason(state)
            if reason:
                message = AIMessage(content=f"Виконання зупинено: {reason}. Повертаю частковий результат.")
                output = {
                    "messages": [message],
                    "step_count": state.get("step_count", 0),
                    "stop_reason": reason,
                }
                logger.log_step(
                    node_name="agent",
                    input_data={"step_count": state.get("step_count", 0)},
                    output_data=output,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
                return output

            response = llm_with_tools.invoke(state["messages"])
            calls = _tool_calls(response)
            output = {
                "messages": [response],
                "step_count": state.get("step_count", 0) + 1,
            }
            logger.log_step(
                node_name="agent",
                input_data={"last_message": compact(state["messages"][-1].content)},
                output_data={"content": compact(response.content), "tool_calls": calls},
                tool_calls=calls,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return output

        def tools_node(state: AgentState) -> dict:
            started = time.monotonic()
            reason = limit_reason(state)
            calls = _tool_calls(state["messages"][-1])
            recent, loop_detected = detector.update(state.get("recent_tool_calls", []), calls)
            if loop_detected:
                reason = "loop_detected"
            if reason:
                tool_messages = [
                    ToolMessage(
                        content=json.dumps({"error": reason, "status": "stopped"}),
                        tool_call_id=call["id"],
                        name=call["name"],
                    )
                    for call in calls
                ]
                output = {
                    "messages": tool_messages,
                    "step_count": state.get("step_count", 0),
                    "stop_reason": reason,
                    "recent_tool_calls": recent,
                }
            else:
                tool_result = tool_node.invoke(state)
                output = {
                    "messages": tool_result.get("messages", []),
                    "step_count": state.get("step_count", 0) + 1,
                    "recent_tool_calls": recent,
                }
            logger.log_step(
                node_name="tools",
                input_data={"tool_calls": calls},
                output_data=[compact(message.content) for message in output.get("messages", [])],
                tool_calls=calls,
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return output

        def formatter_node(state: AgentState) -> dict:
            started = time.monotonic()
            dataset = store.latest()
            stop_reason = state.get("stop_reason") or "completed"
            report = self._build_report(dataset=dataset, stop_reason=stop_reason)
            message = AIMessage(content=report.model_dump_json(indent=2))
            output = {"messages": [message], "final_report": report.model_dump(mode="json")}
            logger.log_step(
                node_name="formatter",
                input_data={"dataset_id": dataset.get("dataset_id") if dataset else None},
                output_data=output["final_report"],
                duration_ms=int((time.monotonic() - started) * 1000),
            )
            return output

        def route_after_agent(state: AgentState) -> Literal["tools", "formatter"]:
            if state.get("stop_reason"):
                return "formatter"
            return "tools" if _tool_calls(state["messages"][-1]) else "formatter"

        def route_after_tools(state: AgentState) -> Literal["agent", "formatter"]:
            return "formatter" if state.get("stop_reason") else "agent"

        graph = StateGraph(AgentState)
        graph.add_node("agent", agent_node)
        graph.add_node("tools", tools_node)
        graph.add_node("formatter", formatter_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", route_after_agent)
        graph.add_conditional_edges("tools", route_after_tools)
        graph.add_edge("formatter", END)
        app = graph.compile()

        initial_state: AgentState = {
            "messages": [
                SystemMessage(content=SYSTEM_PROMPT + "\nAgent Spec:\n" + json.dumps(AGENT_SPEC, ensure_ascii=False)),
                HumanMessage(content=query),
            ],
            "step_count": 0,
            "started_at": logger.started_at,
            "stop_reason": "",
            "recent_tool_calls": [],
        }
        try:
            result = app.invoke(
                initial_state,
                config={"recursion_limit": self.safety.max_steps * 3 + 10},
            )
            report = TrendReport.model_validate(result["final_report"])
            stop_reason = report.stop_reason
            error = ""
        except Exception as exc:  # контрольований фінальний стан замість crash
            stop_reason = "error"
            error = f"{type(exc).__name__}: {exc}"
            report = self._build_report(dataset=store.latest(), stop_reason=stop_reason, error=error)
            logger.log_step(
                node_name="error_handler",
                input_data=query,
                output_data=error,
            )

        trajectory = logger.as_dict(stop_reason=stop_reason)
        if trajectory_path is not None:
            logger.save(trajectory_path, stop_reason=stop_reason)
        return {
            "report": report.model_dump(mode="json"),
            "trajectory": trajectory,
            "steps": trajectory["total_steps"],
            "elapsed_ms": trajectory["total_time_ms"],
            "tool_calls": [
                call["name"]
                for step in trajectory["trajectory"]
                if step.get("node_name") == "tools"
                for call in step.get("tool_calls", [])
            ],
            "error": error,
        }

    def _build_report(
        self,
        *,
        dataset: dict | None,
        stop_reason: str,
        error: str = "",
    ) -> TrendReport:
        if dataset is None:
            return TrendReport(
                status="error" if error else "partial",
                mode="general",
                topic="",
                period_days=7,
                region_code="UA",
                source_mode=self.client.source_mode,
                generated_at=datetime.now(UTC),
                candidates_found=0,
                videos_analyzed=0,
                top_overall=[],
                top_by_views=[],
                trend_terms=[],
                leading_channels=[],
                summary=error or "Аналіз завершився до створення набору даних.",
                confidence=0.0,
                limitations=["Немає результатів пошуку для формування рейтингу."],
                stop_reason=stop_reason,
            )

        query = dataset["query"]
        rankings = dataset.get("rankings") or {}
        videos = dataset.get("videos") or []
        complete = bool(rankings.get("trend_score")) and stop_reason == "completed"
        available = len(rankings.get("trend_score") or [])
        limitations = [
            "Коментарі та тексти коментарів не збираються у версії 1.0.",
            "Рейтинг формується лише з кандидатів, отриманих із публічного HTML YouTube або fixture-набору.",
        ]
        if self.client.source_mode == "fixture":
            limitations.append("Fixture-режим використовує синтетичні відтворювані дані, а не поточний YouTube.")
        if self.client.source_mode == "html" and not topic:
            limitations.append(
                "Без YouTube API загальний топ є broad-category approximation: trending/home з fallback на music, news, sports і technology."
            )
        if available < 20:
            limitations.append(f"Доступно лише {available} позицій для загального топу.")
        if stop_reason != "completed":
            limitations.append(f"Виконання примусово завершено: {stop_reason}.")
        topic = str(query.get("topic") or "")
        summary = (
            f"Проаналізовано {len(videos)} відео за останні {query['days']} днів; "
            f"сформовано {available} позицій загального рейтингу"
            + (f" за темою «{topic}»." if topic else f" для регіону {query['region_code']}.")
        )
        confidence = 0.7 if self.client.source_mode == "html" else 0.75
        if not complete:
            confidence = min(confidence, 0.45)
        return TrendReport(
            status="success" if complete else ("error" if error else "partial"),
            mode="thematic" if topic else "general",
            topic=topic,
            period_days=int(query["days"]),
            region_code=str(query["region_code"]),
            source_mode=self.client.source_mode,
            generated_at=datetime.now(UTC),
            candidates_found=len(videos),
            videos_analyzed=len(videos) if dataset.get("statistics_enriched") else 0,
            top_overall=[RankedVideo.model_validate(row) for row in rankings.get("trend_score", [])],
            top_by_views=[RankedVideo.model_validate(row) for row in rankings.get("views", [])],
            trend_terms=list(dataset.get("signals", {}).get("trend_terms", [])),
            leading_channels=list(dataset.get("signals", {}).get("leading_channels", [])),
            summary=summary,
            confidence=confidence,
            limitations=limitations,
            stop_reason=stop_reason,
        )
