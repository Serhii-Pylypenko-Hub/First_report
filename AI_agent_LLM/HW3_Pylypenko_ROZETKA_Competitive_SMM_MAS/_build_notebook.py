"""Зібрати україномовний демонстраційний notebook з видимими результатами."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
NOTEBOOK = ROOT / "HW3_Пилипенко_ROZETKA_Competitive_SMM_MAS.ipynb"


def md(text: str):
    return nbf.v4.new_markdown_cell(text)


def code(text: str):
    return nbf.v4.new_code_cell(text)


cells = [
    md("""# Фінальне ДЗ №3: production-ready MAS конкурентної SMM-аналітики

Цільовий бренд — **ROZETKA**. Конкуренти — **COMFY, ALLO, Фокстрот та Епіцентр**.

Notebook показує кожний проміжний результат, але чітко розділяє синтетичний fixture та поточні production-дані. Рекламні TOP містять лише записи з `paid_ad + confirmed`; аудиторні сегменти є inference, а не фактичною демографією."""),
    md("""## 1. Підготовка

Notebook можна відкрити з каталогу проєкту або з батьківської папки. Код сам знаходить корінь — помилки «відкрийте notebook з каталогу…» не буде."""),
    code("""from pathlib import Path
import asyncio, json, subprocess, sys, uuid
import pandas as pd
from IPython.display import display, HTML, JSON, Markdown

ROOT = Path.cwd()
if not (ROOT / "hw3_smm").exists():
    candidate = ROOT / "HW3_Pylypenko_ROZETKA_Competitive_SMM_MAS"
    if candidate.exists(): ROOT = candidate
if not (ROOT / "hw3_smm").exists():
    raise RuntimeError("Не знайдено корінь HW3. Відкрийте репозиторій AI_agent_LLM або каталог HW3.")
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
print("Корінь проєкту:", ROOT)

from tools_legacy import default_request
from mas_langgraph import create_mas
from hitl import approve_all_payload
from hw3_smm.fixtures import build_fixture_posts
from hw3_smm.dashboard import brand_table, ad_ranking_table, create_dashboards
from hw3_smm.mcp_integration import integration_summary
from notebook_ui import display_review_widget
from evals import run_evals
from red_team import run_red_team
from mas_crewai import CrewCompetitiveSMMMAS
from comparison_metrics import collect_metrics"""),
    md("""## 2. Вхід і guardrails

У production `session_id` надходить від server-side авторизації. Вхід перевіряється на injection, розмір і rate limit до виклику агентів."""),
    code("""REQUEST = default_request("notebook-request", "notebook-session")
display(JSON(REQUEST.model_dump(mode="json"), expanded=False))"""),
    md("## 3. Нормалізований snapshot п’яти брендів"),
    code("""fixture_posts = build_fixture_posts()
fixture_df = pd.DataFrame([post.model_dump(mode="json") for post in fixture_posts])
summary = fixture_df.groupby(["brand", "source_type"], observed=True).size().reset_index(name="Кількість")
summary = summary.rename(columns={"brand": "Бренд", "source_type": "Тип джерела"})
display(summary)
print("Усього публікацій:", len(fixture_df))
print("NaN не передаються у JSON; відсутні перегляди зберігаються як null + views_status.")"""),
    md("## 4. Повний LangGraph MAS і результати кожного агента"),
    code("""THREAD_ID = "notebook-" + uuid.uuid4().hex[:8]
MAS = create_mas(ROOT, ROOT / "notebook_state.db")
STATE = MAS.start(REQUEST, THREAD_ID)
print("Наступний вузол:", STATE["next"])
print("Interrupt:", STATE["interrupts"][0]["gate"])
agent_rows = []
for agent, result in STATE["values"]["agent_results"].items():
    agent_rows.append({"Агент": agent, "Статус": result.get("status", "completed"), "Поля результату": ", ".join(result.keys())})
display(pd.DataFrame(agent_rows))"""),
    md("## 5. Порівняльна таблиця брендів"),
    code("""ANALYSIS = STATE["values"]["analysis"]
display(brand_table(ANALYSIS))"""),
    md("## 6. Порівняльні дашборди"),
    code("""figures = create_dashboards(ANALYSIS)
for figure in figures: display(figure)"""),
    md("## 7. TOP підтвердженої реклами за окремими метриками"),
    code("""for key, title in [
    ("top_by_views", "Перегляди"), ("top_by_likes", "Вподобання"),
    ("top_by_comments", "Коментарі"), ("top_by_shares", "Поширення"),
    ("top_by_normalized_score", "Комплексний нормалізований бал")]:
    display(Markdown(f"### TOP: {title}"))
    display(ad_ranking_table(ANALYSIS, key))"""),
    md("## 8. Порівняння однакових тематик, сегментів і funnel"),
    code("""theme_rows = [{
    "Тема": row["topic"], "Лідер": row["leader"], "Бал": row["leader_score"],
    "Формат": row["dominant_format"], "Етап воронки": row["funnel_stage"],
    "Сегмент": row["audience"]["label_uk"], "Confidence": row["audience"]["confidence"]
} for row in ANALYSIS["theme_comparison"]]
display(pd.DataFrame(theme_rows))"""),
    md("## 8.1. Рекомендації Content Intelligence Agent за темами"),
    code("""display(pd.DataFrame(ANALYSIS["recommendations"]))"""),
    md("""## 9. П’ять рекламних чернеток

Це оригінальні тексти на основі агрегованих тем і форматів. У навчальні чернетки навмисно додано мовні помилки, щоб робота мовних агентів була видимою."""),
    code("""RAW_DRAFTS = STATE["values"]["agent_results"]["strategist"]["drafts"]
display(pd.DataFrame([{"ID": x["draft_id"], "Тема": x["topic"], "Воронка": x["funnel_stage"], "Початковий текст": x["text"]} for x in RAW_DRAFTS]))"""),
    md("## 10. Результати кожного мовного агента"),
    code("""LANGUAGE = STATE["values"]["language_review"]
for agent, result in LANGUAGE["agent_results"].items():
    display(Markdown(f"### {agent.title()} Agent — {len(result['findings'])} зауважень"))
    display(pd.DataFrame(result["findings"]))
display(Markdown("### Verifier Agent"))
display(pd.DataFrame(LANGUAGE["verifier"]["findings"]))"""),
    md("## 11. Попередження про заборонені теми"),
    code("""warnings = STATE["values"].get("forbidden_warnings", [])
if warnings:
    display(HTML('<div style="padding:12px;border:2px solid #c53030;background:#fff5f5"><b>Заборонені теми виявлено.</b> Автопогодження вимкнено.</div>'))
    display(JSON(warnings))
else:
    display(HTML('<div style="padding:12px;border:2px solid #38a169;background:#f0fff4"><b>Brand safety:</b> заборонених тем не виявлено.</div>'))"""),
    md("""## 12. Інтерактивне погодження

Позначте потрібну TOP-рекламу й фінальні пости. Є кнопки **«Вибрати все»** та **«Зняти все»**. Тексти можна редагувати прямо у великих полях. Непозначені елементи відсікаються. Після цього workflow окремо зупиниться перед файловим експортом."""),
    code("""REVIEW_WIDGET = display_review_widget(MAS, THREAD_ID, STATE)"""),
    md("""## 13. Відтворювана демонстрація погодження і фінального тексту

Наступний блок використовує окремий thread і програмно моделює «Вибрати все», щоб після `Run All` фінальні тексти були видимі навіть до натискання інтерактивної кнопки вище."""),
    code("""AUTO_THREAD = "notebook-auto-" + uuid.uuid4().hex[:8]
AUTO_MAS = create_mas(ROOT, ROOT / "notebook_state.db")
AUTO_STATE = AUTO_MAS.start(default_request("notebook-auto", "notebook-auto-session"), AUTO_THREAD)
AUTO_STATE = AUTO_MAS.resume_selection(AUTO_THREAD, approve_all_payload(AUTO_STATE))
FINAL_POSTS = AUTO_STATE["values"]["approved_drafts"]
for post in FINAL_POSTS:
    display(HTML(f'''<div style="margin:12px 0;padding:18px;border:1px solid #38a169;border-radius:8px;background:#f0fff4">
    <b>{post["draft_id"]} · {post["topic"]} · {post["funnel_stage"]}</b><p style="font-size:16px">{post["text"]}</p></div>'''))
print("Workflow зупинено перед risky_export:", AUTO_STATE["next"])
AUTO_STATE = AUTO_MAS.resume_export(AUTO_THREAD, "edit", "outputs/notebook_report.json")
print("Фінальний статус:", AUTO_STATE["values"]["status"])
print("Файл:", AUTO_STATE["values"]["export_result"]["data"]["path"])
AUTO_MAS.close()"""),
    md("## 14. Реальна MCP stdio-інтеграція та allowlist"),
    code("""mcp_process = subprocess.run(
    [sys.executable, "mcp_demo.py"], cwd=ROOT, capture_output=True, text=True, timeout=90,
)
assert mcp_process.returncode == 0, mcp_process.stderr
MCP_PERMISSIONS = json.loads(mcp_process.stdout.strip().splitlines()[-1])
display(pd.DataFrame([{"Агент": key, "MCP tools": ", ".join(value) or "немає"} for key, value in MCP_PERMISSIONS.items()]))

mcp_graph_process = subprocess.run(
    [sys.executable, "mcp_langgraph_demo.py"], cwd=ROOT, capture_output=True, text=True, timeout=120,
)
assert mcp_graph_process.returncode == 0, mcp_graph_process.stderr
MCP_GRAPH_RESULTS = json.loads(mcp_graph_process.stdout.strip().splitlines()[-1])
display(Markdown("### Два MCP-виклики з LangGraph agent node"))
display(pd.DataFrame(MCP_GRAPH_RESULTS))"""),
    md("""## 15. Альтернативна CrewAI-структура та порівняння

Нижче запускається контрольований offline-сценарій того самого кейсу без API-витрат. Він перевіряє тотожність бізнес-результатів. `create_crew()` містить CrewAI Agent/Task/Crew, але live `kickoff()` і реальні token traces потребують налаштованої LLM."""),
    code("""CREW_RESULT = CrewCompetitiveSMMMAS().run({"request_id": "notebook-crew", "session_id": "notebook-crew-session"})
display(pd.DataFrame([{
    "Статус": CREW_RESULT["status"],
    "Брендів": len(CREW_RESULT["analysis"]["brand_summary"]),
    "Публікацій": len(CREW_RESULT["analysis"]["posts"]),
    "TOP-реклам": len(CREW_RESULT["analysis"]["ad_rankings"]["top_by_normalized_score"]),
    "Чернеток": len(CREW_RESULT["drafts"]),
    "Мовних зауважень": len(CREW_RESULT["language_review"]["verifier"]["findings"]),
}]))
COMPARISON = collect_metrics(ROOT / "comparison_results.json")
display(pd.DataFrame([
    {"Фреймворк": "LangGraph", **COMPARISON["langgraph"]},
    {"Фреймворк": "CrewAI offline demo", **COMPARISON["crewai"]},
]))"""),
    md("""## 16. Evals, red-team і pytest

Artifact-тест самого notebook запускається після його збереження, тому всередині notebook виконується решта тестів. Це не команда для PowerShell, а Python-код у Jupyter cell."""),
    code("""eval_rows = run_evals(ROOT / "eval_results.json")
red_rows = run_red_team(ROOT / "red_team_results.json")
display(pd.DataFrame(eval_rows))
display(pd.DataFrame(red_rows))
assert all(row["pass"] for row in eval_rows)
assert all(row["pass"] for row in red_rows)"""),
    code("""import subprocess
tests = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "--ignore=tests/test_artifacts.py"],
    cwd=ROOT, capture_output=True, text=True, timeout=120,
)
print(tests.stdout)
if tests.stderr: print(tests.stderr)
assert tests.returncode == 0"""),
    md("""## 17. Висновок за завданням

Побудовано supervisor MAS із ReAct, структурованим Plan-and-Execute, Agentic RAG, ChromaDB, SqliteSaver, MCP tools/resources/prompt, двома HITL-рівнями, мовною MAS, guardrails, аудитом, evals і red-team. Fixture-результати демонструють функціональність, але не видаються за актуальну статистику брендів. Реальний LangSmith URL додається після запуску з власним ключем."""),
]

nb = nbf.v4.new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
})
nbf.write(nb, NOTEBOOK)
print(NOTEBOOK)
