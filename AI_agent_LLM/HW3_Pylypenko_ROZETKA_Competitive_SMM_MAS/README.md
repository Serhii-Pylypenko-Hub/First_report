# HW3 — ROZETKA Competitive SMM Production MAS

Фінальне ДЗ розширює одноагентний `Task_001_Pylypenko_ROZETKA_SMM` на зафіксованому коміті `91981dd` до production-oriented мультиагентної системи. Цільовий бренд — ROZETKA; порівнюються COMFY, ALLO, Фокстрот та Епіцентр.

Система збирає й нормалізує публікації, відокремлює підтверджену рекламу, аналізує аудиторні сегменти та funnel, будує порівняльні дашборди, формує п'ять оригінальних рекламних чернеток, перевіряє їх мовною MAS і передає людині на вибір та редагування.

> `fixtures/competitive_posts.json` є синтетичним навчальним snapshot. Він демонструє систему, але не видається за актуальну статистику брендів.

## Архітектура

```text
START
  ↓
input guardrail + rolling rate limit
  ↓
Supervisor ── structured RouteDecision ── conditional edges
  ├── Collector Agent ── вкладений LangGraph ReAct
  ├── Researcher Agent ── Agentic RAG / ChromaDB
  ├── Analyst Agent ── конкурентні метрики, audience, funnel
  ├── Strategist Agent ── Plan → Execute → Replan subgraph
  ├── Language MAS
  │     ├── Grammar
  │     ├── Style
  │     ├── Terminology
  │     ├── Structure
  │     └── Verifier
  └── content-selection interrupt()
          ↓
      interrupt_before=["risky_export"]
          ↓
      approval executor → outputs/*.json
```

Supervisor використовує `with_structured_output(RouteDecision)` за наявності дозволеного LLM API. Відтворюваний fixture-запуск застосовує детермінований router і явно має нуль зовнішніх LLM-викликів.

### Handoff і права

| Агент | Роль | Дозволені tools |
|---|---|---|
| Supervisor | Маршрутизація | немає |
| Collector | Збір п'яти брендів | `collect_brand_posts` |
| Researcher | Правила метрик і funnel | `search_smm_knowledge` |
| Analyst | Нормалізація і порівняння | `calculate_competitive_metrics` |
| Strategist | Content brief | `generate_content_brief` |
| Language/Verifier | Мовна й доказова перевірка | лише read-only knowledge |
| Approval executor | Погоджений файловий експорт | `export_smm_report` |

Ризиковий export фізично відсутній у ReAct-наборі та недоступний supervisor.

## Виправлення за коментарем лектора

Executor не шукає `COLLECT_PLATFORMS` або інші маркери у вільному тексті. Planner повертає `ExecutionPlan → PlanStep.operation: PlanOperation`; dispatcher обирає handler за enum. Порожній план, невідома операція та некоректна залежність відхиляються Pydantic-валідацією.

Окремі тести доводять, що довільний опис кроку без текстового маркера не впливає на routing. У README також додано самостійний розділ із п'ятьма аналітичними питаннями.

## Дані та методика

Канонічна модель містить `brand`, `platform`, `post_id`, `source_type`, `ad_status`, `ad_evidence`, формат, тему, текст, URL, provenance, confidence та метрики.

- Відсутнє значення — `null`, не `NaN` і не нуль.
- `views_status` пояснює `available`, `not_public`, `not_applicable` або `missing_in_source`.
- Рекламні TOP містять лише `source_type=paid_ad` і `ad_status=confirmed`.
- Percentile обчислюється всередині однакової `platform + content_type`.
- `audience_inference` не видається за фактичну демографію.
- `conversion_signal_score` не видається за продаж, CTR або ROAS.

Без first-party рекламного кабінету недоступні spend, clicks, conversions, CPA та ROAS. У майбутній live-версії вони можуть надходити лише через окремий валідований owner-scoped JSON/API-конектор.

## MCP Server

`mcp_server.py` на FastMCP містить три типи примітивів.

### Tools

1. `collect_brand_posts` — fixture/live adapter п'яти брендів.
2. `search_smm_knowledge` — ChromaDB RAG із injection guardrail.
3. `calculate_competitive_metrics` — рейтинги, теми, audience і funnel.
4. `generate_content_brief` — п'ять оригінальних content brief.
5. `export_smm_report` — ризиковий ідемпотентний експорт лише після HITL.

### Resources

- `smm://metric-dictionary`;
- `smm://brand-safety-policy`.

### Prompt

- `competitive_content_brief(brand, platform, goal)`.

Реальна інтеграція виконана через `MultiServerMCPClient` і stdio у `hw3_smm/mcp_integration.py`. `mcp_langgraph_demo.py` створює LangGraph agent node та виконує два справжні MCP-виклики: collection і knowledge search. На Windows notebook запускає MCP-демо в ізольованих процесах, оскільки `ipykernel` не надає stdio file descriptor, потрібний MCP subprocess.

## Guardrails і надійність

- Input: українські й англійські injection-патерни, encoded payload, length/token check.
- Output: email, телефон, картка, UA IBAN, ІПН і паспорт.
- Tool: deny-by-default allowlist та валідація аргументів.
- Rate limit: rolling window окремо для кожного `session_id`.
- Brand safety: зброя, hate, adult, fraud і self-harm показуються як warning.
- ReAct: `max_steps`, timeout, signature loop detection.
- MAS: глобальні step/token/time budgets.
- Persistence: файловий SqliteSaver і `thread_id`.
- HITL 1: `interrupt()` для вибору TOP і постів, підтримує відсікання та edit.
- HITL 2: `interrupt_before=["risky_export"]` перед side effect.
- Export: лише `outputs/`, path containment, Pydantic і idempotency key.
- Audit: process-safe обмежений JSON hash chain із `agent_name`, node, tool, status, thread і budgets; PII маскується, а повторні CLI/notebook/pytest-запуски не спричиняють необмеженого росту журналу.
- Degradation: fixture fallback і чесні partial/error statuses.

## Jupyter Notebook

`HW3_Пилипенко_ROZETKA_Competitive_SMM_MAS.ipynb` виконаний і містить видимі результати:

- нормалізований snapshot;
- статус кожного агента;
- порівняльну таблицю п'яти брендів;
- три дашборди;
- п'ять окремих рекламних TOP;
- теми, сегменти та funnel;
- початкові чернетки;
- findings Grammar, Style, Terminology, Structure і Verifier;
- brand-safety warning;
- інтерактивні чекбокси, «вибрати все», «зняти все», edit і confirm;
- фінальні виправлені пости;
- MCP permissions;
- evals, red-team і pytest.

Детальний сценарій для користувача: `USER_GUIDE.md`.

## Встановлення і запуск

```powershell
cd C:\Study\AI_agent_LLM\HW3_Pylypenko_ROZETKA_Competitive_SMM_MAS
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe -m pytest -v
```

CLI без ручного JSON:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id manual-001
..\.venv\Scripts\python.exe run_agent.py review --thread-id manual-001 --decision approve
..\.venv\Scripts\python.exe run_agent.py export --thread-id manual-001 --decision approve
```

Відновлення стану іншим процесом:

```powershell
..\.venv\Scripts\python.exe run_agent.py state --thread-id manual-001
```

Повний технічний state виводиться лише за явним `--full`; без нього CLI показує короткий зрозумілий підсумок.

MCP:

```powershell
..\.venv\Scripts\python.exe mcp_demo.py
..\.venv\Scripts\python.exe -m pytest test_mcp_server.py -v
```

Evals і red-team:

```powershell
..\.venv\Scripts\python.exe evals.py
..\.venv\Scripts\python.exe red_team.py
```

## Observability

Скопіюйте `.env.example` у локальний `.env`, додайте власний LangSmith key і встановіть:

```text
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=hw3-rozetka-competitive-mas
```

Ключі не комітяться. `traces/trace_example.json` описує очікувану локальну ієрархію, але чесно позначений як **не зовнішній trace**. Перед здачею з максимальним балом потрібно виконати один live-запуск і додати до `screenshots/` власний скріншот dashboard та URL trace.

## Scenario evals і red-team

`eval_results.json` містить п'ять сценаріїв: full workflow, RAG, analytics, Plan-and-Execute generation і Language MAS. Поля: `scenario_id`, `query`, `expected_behavior`, `actual`, `pass`, `latency_ms`, `agents_used`, `tools_called`.

`red_team_results.json` містить prompt injection, український jailbreak, PII leak, scope confusion і path traversal/tool misuse.

## LangGraph та CrewAI: фактичне порівняння

`comparison_results.json` генерується автоматично. Поточний scripted fixture-прогін:

| Критерій | LangGraph | CrewAI |
|---|---:|---:|
| LOC orchestration | 374 | 78 |
| Зовнішні LLM tokens | 0 | 0 |
| Coordination LLM calls | 0 | 0 |
| Контроль, 1–5 | 5 | 3 |
| Debugging, 1–5 | 5 | 4 |

Latency зберігається у JSON, оскільки змінюється між машинами. Час розробки не вигадується ретроспективно: відповідні поля залишено `null`, їх треба заповнити за власним фактичним таймером. Для чесного live-порівняння токенів також потрібен API key; scripted-режим реально витрачає нуль зовнішніх токенів.

LangGraph обрано для production через explicit state, conditional edges, два HITL-гейти й контроль persistence. CrewAI значно коротший і зручний для прототипування ролей, але має менше явного контролю над кожним переходом.

Важливо: команда `mas_crewai.py` запускає відтворюваний offline pipeline без зовнішньої LLM. Функція `create_crew()` створює справжні CrewAI `Agent/Task/Crew`, однак live `Crew.kickoff()`, MCP adapter усередині CrewAI та реальне вимірювання токенів потребують налаштованого LLM API. Тому offline-результат не видається за live CrewAI trace.

## П'ять аналітичних питань

### 1. Чому тут потрібна MAS, а не один агент?

Збір, нормалізація, стратегія, мовна перевірка й side effect мають різні права та критерії помилки. Розділення зменшує blast radius і дозволяє незалежно перевірити висновки.

### 2. Чому supervisor, а не swarm?

Workflow має контрольований порядок і ризиковий експорт. Централізований typed router передбачуваніший, простіше трасується і забезпечує deny-by-default handoff.

### 3. Де застосовано ReAct, Plan-and-Execute і RAG?

Collector використовує вкладений циклічний ReAct; Strategist — структурований Plan-and-Execute; Researcher — Agentic RAG у ChromaDB. Кожен патерн застосовано лише там, де він потрібний.

### 4. Як система уникає хибного висновку про успішність реклами?

Paid-рейтинг потребує confirmed evidence; метрики нормалізуються в сумісних групах; conversion без clicks/purchases називається лише signal. У звіті присутні provenance, confidence та limitations.

### 5. Який фреймворк обрано для production і прототипу?

LangGraph — для production-контролю, persistence та HITL. CrewAI — для швидкого прототипування ролей. Висновок базується на реалізованих LOC, runtime та explicit-state debugging, а не лише на лекційній таблиці.

## OWASP ASI 2026 mitigation matrix

| ASI | Актуальність і мітигація | Що залишилось немітигованим |
|---|---|---|
| ASI01 Goal Hijack | Input guardrail, data/instruction boundary, quarantine | Нові семантичні injection без відомих сигнатур |
| ASI02 Tool Misuse | Per-agent allowlist, Pydantic, path containment | Помилка в логіці самого дозволеного tool |
| ASI03 Identity & Privilege Abuse | Deny-by-default, server-side role, supervisor без tools | Прототип не має зовнішнього OAuth/IdP |
| ASI04 Supply Chain | Fixed versions, ізольований MCP subprocess | Немає SBOM/signature verification усіх wheels |
| ASI05 RCE/Sandbox Escape | Немає shell/eval tools, файловий scope `outputs/` | MCP-процес не запущений в окремому контейнері |
| ASI06 Memory Poisoning | Curated Chroma documents, injection scan, provenance | Адміністратор усе ще може додати помилковий trusted документ |
| ASI07 Insecure Inter-Agent Communication | Typed state, Pydantic, hash-chained audit | Немає криптографічного network signing між окремими hosts |
| ASI08 Cascading Failures | Timeouts, bounded retry, loop detector, budgets, rate limit | Зовнішня платформа може довго деградувати до fallback |
| ASI09 Human-Agent Trust Exploitation | Два HITL-гейти, показ доказів, edit/reject | Людина може помилково погодити переконливу погану рекомендацію |
| ASI10 Rogue Agents | Least privilege, tracing, verifier, red-team | Компрометацію базової LLM неможливо виключити повністю |

Прийнятні для навчального прототипу, але не закриті production-ризики: зовнішній OAuth/IdP, контейнерна sandbox-ізоляція MCP та повна перевірка supply chain.

## Артефакти

- `mas_langgraph.py`, `mas_crewai.py`;
- `mcp_server.py`, `test_mcp_server.py`;
- `tools_legacy.py`, `trajectory_logger.py`;
- `guardrails.py`, `hitl.py`, `observability.py`;
- `evals.py`, `red_team.py`;
- `eval_results.json`, `red_team_results.json`, `comparison_results.json`;
- `agent_state.db`, `trajectory.json`, `chroma_db/` — генеровані демонстрацією;
- виконаний Jupyter Notebook;
- pinned `requirements.txt`, `.env.example` та ця інструкція.
