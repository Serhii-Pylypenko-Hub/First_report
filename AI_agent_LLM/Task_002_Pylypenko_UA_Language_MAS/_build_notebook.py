"""Генератор відтворюваного notebook; сам notebook є артефактом здачі."""

from pathlib import Path

import nbformat as nbf


ROOT = Path(__file__).resolve().parent
nb = nbf.v4.new_notebook()
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
nb["metadata"]["language_info"] = {"name": "python", "version": "3.11"}


def md(text: str) -> None:
    nb.cells.append(nbf.v4.new_markdown_cell(text))


def code(text: str) -> None:
    nb.cells.append(nbf.v4.new_code_cell(text))


md("""# Практичне завдання №2: безпечна MAS для перевірки українського тексту

Notebook дублює основний Python workflow логічними блоками: JSON-вхід → guardrails → supervisor і спеціалісти → контрольований RAG → verifier → HITL → виправлена копія → CrewAI parity → MCP і тести.

**Важливо:** текст документа вважається недовіреними даними. Оригінальний JSON не мутується, а адміністративні функції агентам недоступні.""")

md("## 1. Імпорти та відтворюваний вхід")
code("""from pathlib import Path
import json, os, subprocess, sys
import pandas as pd
from IPython.display import display, Markdown, JSON, HTML

PROJECT_DIRNAME = "Task_002_Pylypenko_UA_Language_MAS"
cwd = Path.cwd().resolve()
bases = [cwd, *cwd.parents]
candidates = [*bases, *(base / PROJECT_DIRNAME for base in bases)]
ROOT = next(
    (path for path in candidates if (path / "language_mas").is_dir() and (path / "mcp_server.py").is_file()),
    None,
)
if ROOT is None:
    raise RuntimeError(
        f"Не знайдено каталог {PROJECT_DIRNAME}. "
        "Відкрийте notebook із каталогу завдання або його батьківської робочої папки."
    )

# VS Code/Jupyter може запускати kernel із батьківської папки workspace.
# Додаємо знайдений проєкт до import path і використовуємо його для всіх відносних шляхів.
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
print(f"Корінь проєкту: {ROOT}")

# Якщо kernel уже виконував старішу версію проєкту, Python тримає її в sys.modules.
# Очищаємо лише модулі цього навчального пакета, щоб повторний Run All читав актуальні файли.
for module_name in list(sys.modules):
    if module_name == "language_mas" or module_name.startswith("language_mas.") or module_name == "mcp_server":
        del sys.modules[module_name]

from language_mas.fixtures import load_fixture, demo_review_payload
from language_mas.knowledge import SecureKnowledgeBase
from language_mas.langgraph_mas import create_langgraph_mas
from language_mas.crewai_mas import create_crewai_mas
from language_mas.models import ActorContext
from language_mas.reporting import render_text_report, render_corrected_document, save_corrected_document
from language_mas.document_ingestion import DocumentIntakeAgent
from language_mas.audit import JsonlTracer

REQUEST = load_fixture()
ACTOR = ActorContext(tenant_id="notebook-tenant", user_id="notebook-user")
THREAD_ID = "notebook-language-demo"
display(JSON(REQUEST))""")

md("## 2. Архітектура та мінімальні права")
code("""roles = pd.DataFrame([
    ["Document Intake Agent", "Вибір parser і перетворення файла у JSON без мовних змін", "Лише fixtures/documents і parse_document"],
    ["Supervisor", "Маршрутизація, бюджети, агрегація статусів", "Лише метадані запиту; без tools редагування"],
    ["Grammar Agent", "Орфографія, пунктуація, граматика, узгодження та відмінювання", "Потрібні node.text, правила правопису і словозміни"],
    ["Style Agent", "Кальки, канцеляризми, ясність, лаконічність, офіційні формулювання", "Поточний документ і правила стилю"],
    ["Terminology Agent", "Узгодженість термінів і користувацького глосарія", "Документ і owner-scoped glossary поточного користувача"],
    ["Structure Agent", "Повтори, нумерація, посилання, довгі або дубльовані фрагменти", "node_id, порядок, заголовки та потрібний текст"],
    ["Verifier Agent", "Evidence, confidence, збереження цифр, назв і фактів", "Findings, відповідні фрагменти та retrieved rules"],
], columns=["Агент", "Функція", "Доступ лише до"])
display(roles)""")

md("## 3. Візуалізований intake: TXT, DOCX, PDF і зображення")
code("""intake = DocumentIntakeAgent(trace_path=ROOT / "traces" / "notebook_intake_secure.jsonl")
files = ["example.txt", "example.docx", "example.pdf", "example.png"]
INTAKE_RESULTS = {
    name: intake.parse(name, request_id=f'notebook-{Path(name).suffix[1:]}')
    for name in files
}

rows = []
for name, result in INTAKE_RESULTS.items():
    assert result["status"] == "ok", result
    source = result["data"]["source"]
    nodes = result["data"]["request"]["document"]["nodes"]
    rows.append({
        "Файл": name,
        "Формат": source["format"].upper(),
        "Розмір, байт": source["size_bytes"],
        "Метод": source["extraction_method"],
        "Статус": result["status"],
        "JSON-вузлів": len(nodes),
        "Текст": " ".join(node["text"] for node in nodes)[:120],
        "Попередження": "; ".join(source["warnings"]) or "—",
    })

display(pd.DataFrame(rows))

# Візуальна звірка: зліва оригінальна сторінка/файл, справа JSON саме для передачі в MAS.
import base64, html, io
from docx import Document as WordDocument
from PIL import Image as PILImage
import pdfplumber

def image_data_uri(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

def original_preview(name):
    path = ROOT / "fixtures" / "documents" / name
    suffix = path.suffix.lower()
    if suffix == ".txt":
        body = html.escape(path.read_text(encoding="utf-8"))
        return f'<div class="paper"><pre>{body}</pre></div>'
    if suffix == ".docx":
        parts = []
        for paragraph in WordDocument(path).paragraphs:
            if not paragraph.text.strip():
                continue
            tag = "h3" if paragraph.style.name.startswith("Heading") else "p"
            parts.append(f'<{tag}>{html.escape(paragraph.text)}</{tag}>')
        return '<div class="paper">' + "".join(parts) + '</div>'
    if suffix == ".pdf":
        with pdfplumber.open(path) as pdf:
            images = [page.to_image(resolution=100).original for page in pdf.pages]
        return "".join(
            f'<p><b>Сторінка {index}</b></p><img class="page-image" src="{image_data_uri(image)}" alt="Сторінка {index} PDF">'
            for index, image in enumerate(images, start=1)
        )
    with PILImage.open(path) as image:
        return f'<img class="page-image" src="{image_data_uri(image.copy())}" alt="Вхідне зображення">'

def show_document_pipeline(name):
    result = INTAKE_RESULTS[name]
    transfer_json = html.escape(json.dumps(result["data"]["request"], ensure_ascii=False, indent=2))
    source = result["data"]["source"]
    warning = "; ".join(source["warnings"]) or "немає"
    display(Markdown(
        f'### {name}\\n\\n'
        f'[Відкрити оригінальний файл](./fixtures/documents/{name})  \\n'
        f'**Метод розпізнавання:** `{source["extraction_method"]}` · '
        f'**Статус:** `{result["status"]}` · **JSON-вузлів:** `{len(result["data"]["request"]["document"]["nodes"])}`'
    ))
    display(HTML(f'''<style>
      .compare-grid {{display:grid;grid-template-columns:minmax(300px,1fr) minmax(380px,1fr);gap:18px;align-items:start}}
      .compare-panel {{border:1px solid #777;border-radius:8px;padding:12px;overflow:auto;max-height:620px}}
      .paper {{background:white;color:#111;min-height:300px;padding:38px;box-shadow:0 2px 10px #0003;font:17px/1.5 Georgia,serif}}
      .paper pre {{white-space:pre-wrap;font:16px/1.5 Consolas,monospace}}
      .page-image {{display:block;max-width:100%;height:auto;margin:auto;background:white}}
      .json-transfer {{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.35 Consolas,monospace}}
      @media(max-width:900px) {{.compare-grid {{grid-template-columns:1fr}}}}
    </style>
    <p><b>Попередження:</b> {html.escape(warning)}</p>
    <div class="compare-grid">
      <section><h4>1. Фізичний вигляд оригіналу</h4><div class="compare-panel">{original_preview(name)}</div></section>
      <section><h4>2. JSON, переданий у LangGraph MAS</h4><div class="compare-panel"><pre class="json-transfer">{transfer_json}</pre></div></section>
    </div>'''))

    analysis = DOCUMENT_ANALYSES[name]
    agent_outputs = analysis["agent_results"]
    display(Markdown("#### 3. Результати перевірки саме цього JSON"))
    display(pd.DataFrame([{
        "Агент": agent_name,
        "Статус": agent_outputs[agent_name]["status"],
        "Знахідок": agent_outputs[agent_name].get(
            "finding_count", agent_outputs[agent_name].get("verified_count", 0)
        ),
    } for agent_name in ("grammar", "style", "terminology", "structure", "verifier")]))

    verified = agent_outputs["verifier"]["findings"]
    display(pd.DataFrame([{
        "Агент": item["agent"],
        "Розташування в оригіналі": f'{item.get("section_ref") or "Фрагмент"} · {item["node_id"]}',
        "Категорія": item["category"],
        "Було": item["original_text"],
        "Пропонується": item.get("suggested_fix") or "Потрібне рішення людини",
        "Пояснення": item["reason"],
        "Впевненість": f'{item["confidence"]:.0%}',
    } for item in verified]).fillna("—"))

assert all(item["status"] == "ok" for item in INTAKE_RESULTS.values())
assert {item["data"]["source"]["format"] for item in INTAKE_RESULTS.values()} == {"txt", "docx", "pdf", "png"}

# Кожен JSON, створений Document Intake Agent, окремо проходить той самий LangGraph MAS.
DOCUMENT_ANALYSES = {}
for name, intake_result in INTAKE_RESULTS.items():
    parsed_mas = create_langgraph_mas()
    parsed_thread = f'parsed-{Path(name).suffix[1:]}'
    parsed_mas.start(intake_result["data"]["request"], ACTOR, thread_id=parsed_thread)
    DOCUMENT_ANALYSES[name] = parsed_mas.result(ACTOR, thread_id=parsed_thread)

assert all(result["agent_results"]["verifier"]["status"] == "completed" for result in DOCUMENT_ANALYSES.values())""")

md("""## 3.1. Оригінал → JSON → результати мовних агентів

Нижче кожен контрольний документ із навмисними помилками показано в **окремій клітинці**. Ліворуч міститься фізичний вигляд файлу, праворуч — точний JSON, який Document Intake Agent передав у LangGraph MAS. Під ними наведено знайдені орфографічні, пунктуаційні, граматичні, стилістичні, термінологічні та структурні проблеми.""")

code("""show_document_pipeline("example.txt")""")
code("""show_document_pipeline("example.docx")""")
code("""show_document_pipeline("example.pdf")""")
code("""show_document_pipeline("example.png")""")

md("## 4. Контрольована база знань")
code("""kb = SecureKnowledgeBase()
sources = pd.DataFrame([{
    "ID правила": item["rule_id"],
    "Назва": item["title"],
    "Установа": item["authority"],
    "Версія": item["version"],
    "Довіра": item["trust_level"],
    "Джерело": item["source_url"],
} for item in kb.entries])
display(sources.fillna("—"))
print(f"Перевірених записів: {len(kb.entries)}; checksum кожного запису валідовано під час завантаження.")""")

md("## 5. LangGraph: явний Plan-and-Execute до Human-in-the-Loop")
code("""TRACE_PATH = ROOT / "traces" / "notebook_langgraph_secure.jsonl"
langgraph_mas = create_langgraph_mas(trace_path=TRACE_PATH)
langgraph_mas.start(REQUEST, ACTOR, thread_id=THREAD_ID)
PENDING = langgraph_mas.result(ACTOR, thread_id=THREAD_ID)
print("Статус:", PENDING["status"])
print("Наступний вузол:", PENDING["next"])
print("Однозначних:", len(PENDING["certain_findings"]))
print("Потребують перегляду:", len(PENDING["needs_review"]))""")

md("## 6. Результати кожного агента")
code("""def findings_table(items):
    rows = [{
        "ID": x["finding_id"], "Агент": x["agent"],
        "Розташування": f'{x.get("section_ref") or "Фрагмент"} · {x["node_id"]}',
        "Категорія": x["category"],
        "Було": x["original_text"], "Пропозиція": x.get("suggested_fix") or "—",
        "Причина": x["reason"], "Впевненість": f'{x["confidence"]:.0%}',
        "Джерело": x["evidence"][0]["source_url"] if x.get("evidence") else "—",
    } for x in items]
    return pd.DataFrame(rows).fillna("—")

AGENT_RESULTS = PENDING["agent_results"]
supervisor = AGENT_RESULTS["supervisor"]
verifier = AGENT_RESULTS["verifier"]
display(pd.DataFrame([
    ["Supervisor", supervisor["status"], " → ".join(supervisor["routing_order"]), supervisor["step_count"], supervisor["budget_limit"]],
    ["Verifier", verifier["status"], f'{verifier["received_count"]} отримано / {verifier["verified_count"]} підтверджено', "—", "—"],
], columns=["Агент", "Статус", "Результат/маршрут", "Кроків", "Ліміт"]))

for key, title in [
    ("grammar", "Grammar Agent"),
    ("style", "Style Agent"),
    ("terminology", "Terminology Agent"),
    ("structure", "Structure Agent"),
]:
    output = AGENT_RESULTS[key]
    display(Markdown(f'### {title}: {output["finding_count"]} findings'))
    if output["findings"]:
        display(findings_table(output["findings"]))
    else:
        display(Markdown("Порушень не виявлено."))

display(Markdown("### Verifier Agent: перевірений набір"))
display(pd.DataFrame([{
    "Отримано": verifier["received_count"],
    "Підтверджено": verifier["verified_count"],
    "Відфільтровано": verifier["filtered_count"],
    "Однозначні": verifier["certain_count"],
    "На перегляд": verifier["needs_review_count"],
}]))

display(Markdown("## Наскрізна перевірка кожного розпарсеного документа"))
summary_rows = []
for file_name, analysis in DOCUMENT_ANALYSES.items():
    for agent_name in ("grammar", "style", "terminology", "structure", "verifier"):
        output = analysis["agent_results"][agent_name]
        summary_rows.append({
            "Файл": file_name,
            "Агент": agent_name,
            "Статус": output["status"],
            "Знахідок": output.get("finding_count", output.get("verified_count", 0)),
        })
display(pd.DataFrame(summary_rows))

for file_name, analysis in DOCUMENT_ANALYSES.items():
    outputs = analysis["agent_results"]
    display(Markdown(f"### {file_name}"))
    route = outputs["supervisor"]
    display(pd.DataFrame([{
        "Агент": "Supervisor",
        "Статус": route["status"],
        "Маршрут": " → ".join(route["routing_order"]),
        "Кроків": route["step_count"],
        "Бюджет": route["budget_limit"],
    }]))
    for agent_name, title in [
        ("grammar", "Grammar Agent: орфографія, пунктуація, граматика й відмінювання"),
        ("style", "Style Agent: офіційність, ясність і лаконічність"),
        ("terminology", "Terminology Agent: термінологічна узгодженість"),
        ("structure", "Structure Agent: дублювання і тавтологія"),
    ]:
        output = outputs[agent_name]
        display(Markdown(f'#### {title} — {output["finding_count"]}'))
        if output["findings"]:
            display(findings_table(output["findings"]))
        else:
            display(Markdown("Порушень не виявлено."))
    checked = outputs["verifier"]
    display(Markdown("#### Verifier Agent"))
    display(pd.DataFrame([{
        "Отримано": checked["received_count"],
        "Підтверджено": checked["verified_count"],
        "Відфільтровано": checked["filtered_count"],
        "Однозначні": checked["certain_count"],
        "На перегляд людиною": checked["needs_review_count"],
    }]))
    if checked["findings"]:
        display(findings_table(checked["findings"]))""")

md("## 7. Однозначні пропозиції")
code("""display(findings_table(PENDING["certain_findings"]))""")

md("## 8. Сумнівні пропозиції — рішення людини")
code("""display(findings_table(PENDING["needs_review"]))

# У реальному UI користувач обирає approve/edit/reject для кожної позиції.
REVIEW = demo_review_payload(PENDING)
display(JSON(REVIEW))""")

md("## 9. Resume і застосування тільки підтверджених правок")
code("""langgraph_mas.resume(REVIEW, ACTOR, thread_id=THREAD_ID)
FINAL = langgraph_mas.result(ACTOR, thread_id=THREAD_ID)
print("Фінальний статус:", FINAL["status"])
print("Застосовано:", len(FINAL["applied"]))
print("Відхилено:", len(FINAL["rejected"]))
corrected_text = render_corrected_document(FINAL)

display(Markdown("### Фінальний виправлений текст"))
display(HTML(
    '<div style="background:#f7fff7;color:#111;border:2px solid #38a169;'
    'border-radius:10px;padding:24px;font:17px/1.6 Georgia,serif;white-space:pre-wrap">'
    + html.escape(corrected_text) + '</div>'
))

display(Markdown("### Порівняння оригіналу та погодженої копії"))
original_nodes = {node["node_id"]: node["text"] for node in REQUEST["document"]["nodes"]}
corrected_nodes = {node["node_id"]: node["text"] for node in FINAL["corrected_document"]["nodes"]}
display(pd.DataFrame([{
    "Розташування": node["section_ref"],
    "Оригінал": original_nodes[node["node_id"]],
    "Після HITL": corrected_nodes[node["node_id"]],
} for node in REQUEST["document"]["nodes"]]))

display(Markdown("### JSON виправленої копії"))
display(JSON(FINAL["corrected_document"]))
corrected_path = save_corrected_document(FINAL, ROOT / "outputs" / "notebook_corrected_document.txt")
display(Markdown(f"[Відкрити нову погоджену TXT-копію]({corrected_path.as_posix()})"))
display(Markdown("### Записи, додані до персональної пам’яті після write-gate"))
display(pd.DataFrame(FINAL["memory_updates"]))
assert FINAL["memory_updates"][0]["preferred_text"] == 'кінцевий термін'""")

md("## 9.1. Перевірка пам’яті в новому thread")
code("""FOLLOW_UP = {
    "request_id": "notebook-memory-follow-up",
    "document": {
        "document_id": "follow-up-document",
        "language": "uk",
        "register": "official",
        "nodes": [{
            "node_id": "follow-up-001",
            "node_type": "paragraph",
            "section_ref": "Абзац 1",
            "text": "Будь ласка, погодьте дедлайн підготовки звіту.",
        }],
    },
}
langgraph_mas.start(FOLLOW_UP, ACTOR, thread_id="notebook-memory-follow-up")
MEMORY_RESULT = langgraph_mas.result(ACTOR, thread_id="notebook-memory-follow-up")
remembered = [
    item for item in MEMORY_RESULT["agent_results"]["terminology"]["findings"]
    if item["rule_id"].startswith("MEMORY.USER.")
]
display(Markdown("**Новий документ містить «дедлайн». Нижче — пропозиція, згадана лише для поточного користувача:**"))
display(findings_table(remembered))
assert remembered[0]["suggested_fix"] == 'кінцевий термін'""")

md("## 10. Простий текстовий звіт")
code("""print(render_text_report(FINAL))""")

md("## 11. CrewAI: той самий кейс і тотожність результатів")
code("""crew = create_crewai_mas(trace_path=ROOT / "traces" / "notebook_crewai_secure.jsonl")
CREW_RESULT = crew.run_scripted(REQUEST, ACTOR)

def signature(result):
    items = [*result.get("certain_findings", []), *result.get("needs_review", [])]
    return {(x["rule_id"], x["node_id"], x.get("suggested_fix") or "") for x in items}

parity = signature(PENDING) == signature(CREW_RESULT)
display(pd.DataFrame([
    ["LangGraph", len(signature(PENDING)), "HITL + persistence"],
    ["CrewAI scripted", len(signature(CREW_RESULT)), "Відтворювана перевірка без API"],
], columns=["Реалізація", "Кількість findings", "Режим"]))
print("Результати до HITL тотожні:", parity)
assert parity""")

md("## 12. Справжній FastMCP discovery через stdio: рівно 4 tools")
code("""probe = subprocess.run([
    sys.executable, "-c",
    "import asyncio; from language_mas.mcp_integration import list_language_mcp_tool_names; print(asyncio.run(list_language_mcp_tool_names()))"
], cwd=ROOT, capture_output=True, text=True, timeout=30)
print(probe.stdout.strip().splitlines()[-1] if probe.stdout.strip() else probe.stderr)
assert probe.returncode == 0
assert "apply_approved_corrections" in probe.stdout
assert "lookup_terminology" not in probe.stdout""")

md("## 13. Security red-team smoke tests")
code("""unsafe = load_fixture("unsafe_request.json")
blocked = create_langgraph_mas()
blocked.start(unsafe, ACTOR, thread_id="notebook-red-team")
blocked_result = blocked.result(ACTOR, thread_id="notebook-red-team")
display(JSON(blocked_result))
assert blocked_result["status"] == "blocked"
assert "PROMPT_INJECTION_DETECTED" in json.dumps(blocked_result)""")

md("## 14. JSON-траєкторія без сирого тексту та з hash-chain")
code("""trace_rows = langgraph_mas.tracer.events
display(pd.DataFrame(trace_rows).fillna("—"))
assert trace_rows
assert "original_text" not in json.dumps(trace_rows, ensure_ascii=False)
all_trace_rows = [json.loads(line) for line in TRACE_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
assert JsonlTracer.verify_chain(all_trace_rows)
print("Цілісність audit hash-chain: підтверджено")""")

md("## 15. Pytest")
code("""# Під час виконання самого notebook artifact-тест ще не може бачити всі execution_count.
# Його перевіряємо окремим фінальним запуском pytest після збереження notebook.
tests = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "--ignore=tests/test_artifacts.py"],
    cwd=ROOT,
    capture_output=True,
    text=True,
    timeout=120,
)
print(tests.stdout)
if tests.stderr:
    print(tests.stderr)
assert tests.returncode == 0""")

md("""## 16. Валідація вимог і висновок за завданням

| Вимога | Реалізація |
|---|---|
| LangGraph supervisor + 3+ agents | Supervisor, 4 specialists і Verifier |
| CrewAI той самий кейс | scripted parity + native hierarchical Crew |
| FastMCP 3–4 tools | рівно 4 tools, stdio discovery і per-agent allowlist |
| Tracing | LangSmith `@traceable` + локальний JSONL hash-chain |
| Guardrails | injection detection, tool allowlist/validation, PII redaction |
| HITL | `interrupt()` та рішення approve/edit/reject для кожної позиції |
| Pytest | MCP, guardrails, workflows, intake й артефакти |

Реалізовано дві версії одного MAS-кейсу: контрольований LangGraph supervisor workflow та рольову CrewAI-реалізацію. Система використовує власний FastMCP-сервер, мінімальні права, контрольований RAG із provenance/checksum, три рівні guardrails, PII-redaction, persistence, структуроване tracing і динамічний HITL. Document Intake Agent уже перетворює TXT, DOCX, PDF і PNG/JPEG на спільний JSON-контракт. Після рішення людини створюється нова TXT-копія, а оригінал залишається незмінним. Scripted режим забезпечує відтворювану демонстрацію без API; native CrewAI і LangSmith вмикаються конфігурацією середовища.""")

target = ROOT / "Task_002_Пилипенко_Мовна_MAS.ipynb"
nbf.write(nb, target)
print(target)
