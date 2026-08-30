# Task 001 — одноагентний ROZETKA Cross-Platform SMM Analyzer

## 1. Мета

Практична робота розвиває попередній YouTube/SMM-проєкт у light-систему
аналізу контент-маркетингу одного бренду на кількох платформах. Агент аналізує
30-денний період для ROZETKA: частоту публікацій, формати, перегляди, лайки,
коментарі, поширення, етапи маркетингової воронки, приблизну цільову аудиторію
та п'ять повторюваних контентних патернів.

Це **один агент**, а не multi-agent система. Platform adapters, tools і вузли
графа є компонентами одного workflow. У майбутньому їх можна винести в окремих
Instagram/Facebook/Analytics агентів без зміни канонічної моделі даних.

У Jupyter Notebook усі назви колонок у користувацьких таблицях подано
українською, відсутні значення відображаються як `—` із поясненням причини,
а після блоку pytest наведено підсумкову маркетингову аналітику та рекомендації.

## 2. Архітектура

```text
START
  ↓
planner ── Plan(goal, steps) через with_structured_output
  ↓
executor ── вкладений Guarded ReAct: LLM → tool → observation → LLM
  ↓
replanner ── ReplanDecision(continue | replan | finish)
  ├── executor
  ├── risky_export  ← interrupt_before + approve/edit/reject
  └── END
```

Вкладений ReAct має три обов'язкові guardrails:

- `max_steps=10`;
- `timeout_seconds=120`;
- signature-based детекція повторного tool call.

Кожне рішення та observation потрапляє до `trajectory.json` із timestamp,
назвою інструмента, статусом і кодом помилки.

## 3. Доменні інструменти

| Tool | Призначення |
|---|---|
| `collect_public_posts` | Light HTML/metadata спроба без API |
| `load_fixture_posts` | Відтворюваний fallback після login-wall або неповного HTML |
| `knowledge_search` | Agentic RAG у ChromaDB |
| `analyze_marketing_patterns` | Platform-топи, частота, funnel, audience inference, 5 патернів |
| `export_smm_report` | Ризикова файлова write-операція після HITL |

Кожен tool має Pydantic v2 `BaseModel`, `Field`, `field_validator`, заборону
зайвих полів та однаковий вихід:

```json
{"status": "ok", "data": {}}
```

або

```json
{"status": "error", "error": {"code": "...", "message": "...", "details": {}}}
```

## 4. Platform adapters і нормалізація

`collect_public_posts` маршрутизує запит до різних внутрішніх компонентів:

```text
Instagram/Facebook → OpenGraph metadata + login-wall detection
Threads            → embedded profile metadata + availability detection
Telegram           → server-rendered t.me/s HTML
```

Парсери не є окремими агентами або tools. Вони реалізують спільний контракт і
повертають дані до єдиної моделі `SocialPost`. Якщо public HTML недоступний або
не містить достатніх метрик, ReAct отримує `status=error`, не повторює той самий
виклик і самостійно переходить до `load_fixture_posts`.

Канонічні поля: `platform`, `post_id`, `published_at`, `content_type`, `topic`,
`views`, `views_status`, `likes`, `comments`, `shares`, `url`, `source_mode`, `confidence`.
Специфічні показники (`saves`, `reactions`, `forwards`) не губляться і
зберігаються у `platform_metrics`.

`profile_status` зберігається окремо від `post_count`. Тому система розрізняє
підтверджений офіційний профіль без постів у snapshot, непідтверджений профіль і
помилку збору. Для нульового результату додається `zero_posts_reason`.

`views=None` не означає нуль переглядів. Поле `views_status` пояснює причину:
`not_public` для недоступного public counter, `not_applicable` для статичного
формату, `missing_in_source` для неповного джерела або `available`. Наприклад,
Facebook video може мати views, а photo/text — лише reactions і comments.

Сирі показники різних платформ не порівнюються напряму. Для cross-platform top
агент обчислює percentile кожної доступної метрики всередині відповідної
платформи й усереднює їх у `normalized_score`.

## 5. Дані та чесні обмеження

`fixtures/social_posts.json` — синтетичний навчальний snapshot із 22 постів за
умовний 30-денний період зі сталою датою зрізу `2026-08-30T12:00:00Z`:

- Instagram — 8;
- Facebook — 7;
- Telegram — 7;
- Threads — 0; офіційний профіль не підтверджено в social hub, тому система
  показує `profile_status=not_verified` і `zero_posts_reason`, а не робить
  бездоказовий висновок про відсутність сторінки.

`fixture://...` не є посиланнями на реальні публікації. Це навмисно: система не
вигадує офіційні URL або поточні метрики ROZETKA. Live-режим намагається
прочитати лише публічний HTML; при блокуванні виконується прозорий fallback.

Без API та first-party analytics недоступні reach, saves для всіх постів,
реальні demographics і конверсії. Вік, регіон та сегмент аудиторії мають
позначку `inferred`, confidence і пояснення. Тексти коментарів не збираються —
аналізується лише їхня публічна кількість.

## 6. Agentic RAG

`knowledge_documents.json` містить 12 документів про:

- marketing funnel;
- метрики Instagram, Facebook, Threads і Telegram;
- нормалізацію між платформами;
- контентні патерни;
- inferred-аудиторію;
- частоту публікацій;
- provenance, fallback і HITL.

Документи індексуються через `chromadb.PersistentClient`. Для відтворюваного
запуску використовується локальний детермінований embedding без завантаження
моделі. `knowledge_search` не виконується автоматично на кожен запит: ReAct
викликає його лише для кроку, який потребує доменних правил.

## 7. Persistence та Human-in-the-Loop

`agent_state.db` є звичайним SQLite-файлом, не `:memory:`. `SqliteSaver`
зберігає кожен superstep за `thread_id`. Після закриття процесу новий екземпляр
агента відновлює стан через `get_state()`.

Перед вузлом `risky_export` граф компілюється з:

```python
graph.compile(checkpointer=saver, interrupt_before=["risky_export"])
```

Людина бачить raw path і приймає одне з рішень:

- `approve` — виконати експорт;
- `edit` — змінити безпечний відносний JSON-шлях і виконати;
- `reject` — завершити workflow без запуску tool.

## 8. Встановлення

```powershell
cd C:\Study\AI_agent_LLM\Task_001_Pylypenko_ROZETKA_SMM
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 9. CLI-демонстрація

Початок; граф зупиниться перед `risky_export`:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id demo-001
```

Підтвердження експорту (`approve`) у Windows PowerShell:

```powershell
..\.venv\Scripts\python.exe run_agent.py resume --thread-id demo-001 --decision approve
```

Відхилення експорту (`reject`) в окремому потоці:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id demo-reject
..\.venv\Scripts\python.exe run_agent.py resume --thread-id demo-reject --decision reject --reason "Потрібна ручна перевірка"
```

Редагування шляху (`edit`) в окремому потоці. Перед кожним `resume` спочатку
потрібно виконати `start` із тим самим `thread_id`:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id demo-edit
..\.venv\Scripts\python.exe run_agent.py resume --thread-id demo-edit --decision edit --path outputs/edited_report.json
```

Перегляд збереженої контрольної точки:

```powershell
..\.venv\Scripts\python.exe run_agent.py state --thread-id demo-001
```

Необов'язкова спроба отримання публічного HTML перед переходом до навчального
snapshot:

```powershell
..\.venv\Scripts\python.exe run_agent.py --live start --thread-id live-001
```

## 10. Тести й демонстрація

```powershell
..\.venv\Scripts\python.exe -m pytest -v
..\.venv\Scripts\python.exe test_runner.py
```

Контрольний результат: `12 passed`. Тести охоплюють 8 негативних/позитивних
перевірок схем, JSON-контракт tools, ChromaDB, ReAct fallback, guardrails,
persistence, незалежність `thread_id`, approve та reject.

`test_runner.py` створює:

- `demo_results.json`;
- `agent_state.db` зі збереженими approve/reject threads;
- `trajectory.json`;
- `outputs/rozetka_smm_report.json` після approve.

Каталоги `chroma_db/`, `outputs/` і файл `agent_state.db` є відтворюваними
runtime-артефактами, тому не додаються до Git. Вони автоматично створюються
під час запуску та включені до готового архіву для демонстрації persistence.

Notebook, CLI та `test_runner.py` використовують спільні `DEFAULT_REQUEST` і
`agent.result()`. У scripted/fixture-режимі їхній канонічний аналітичний
результат є тотожним; різняться лише `thread_id`, checkpoint і рішення HITL.

## 11. Валідація вимог практичного завдання

| Обов'язкова вимога | Реалізація | Статус |
|---|---|---|
| 3–5 Pydantic tools | 5 tools із `Field`, `field_validator`, JSON-контрактом | ✅ |
| Guarded ReAct | LangGraph, 10 кроків, 120 с, repeat detection, trajectory | ✅ |
| Plan-and-Execute | `planner → executor → replanner`, structured outputs | ✅ |
| Persistence | file-backed `SqliteSaver`, resume, `get_state()` | ✅ |
| Agentic RAG | ChromaDB, 12 документів, tool викликається за рішенням агента | ✅ |
| HITL | `interrupt_before`, approve/edit/reject | ✅ |
| Тести | 8 schema checks + tools, RAG, ReAct, persistence та HITL | ✅ |
| Артефакти | README, Notebook, trajectory, knowledge base, pytest output | ✅ |

## 12. Аналіз демонстраційного результату

Контрольний запуск зібрав 22 fixture-пости й отримав 8 RAG-документів. Для
кожної платформи спочатку зафіксовано контрольовану помилку public source, після
чого ReAct сам обрав fallback без повторення виклику.

П'ять патернів у контрольному результаті, у порядку підсумкового бала:
contest, humor, product guide, discount та gift guide. Це не твердження про
поточну кампанію ROZETKA, а доказ роботи
аналітичного контуру. Threads повертається як coverage gap, а не заповнюється
вигаданими постами. Approve виконує export і завершує workflow зі статусом
`exported`; reject завершує його зі статусом `rejected` без файлової дії.

## 13. Структура

```text
Task_001_Pylypenko_ROZETKA_SMM/
├── Task_001_Пилипенко_ROZETKA.ipynb
├── rozetka_smm_agent/
│   ├── models.py
│   ├── data_source.py
│   ├── knowledge.py
│   ├── tools.py
│   ├── react.py
│   ├── plan_execute.py
│   ├── scripted.py
│   ├── reporting.py
│   └── factory.py
├── fixtures/social_posts.json
├── knowledge_documents.json
├── tests/test_system.py
├── run_agent.py
├── test_runner.py
├── trajectory.json
├── agent_state.db
├── demo_results.json
└── requirements.txt
```
