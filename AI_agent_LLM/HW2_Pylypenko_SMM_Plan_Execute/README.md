# HW2 — YouTube SMM Plan-and-Execute Agent

## 1. Опис

Проєкт розвиває YouTube Trends Agent із ДЗ №1 до архітектури
`planner → executor → replanner`. Агент спочатку створює повний план, потім
виконує по одному кроку й після кожного результату вирішує, чи продовжувати,
перепланувати або завершити workflow.

Додано три обов'язкові production-механізми з навчального матеріалу:

- file-backed persistence через `SqliteSaver` і `thread_id`;
- Agentic RAG через персистентну ChromaDB;
- Human-in-the-Loop через `interrupt()` і `Command(resume=...)`.

Основний демонстраційний артефакт —
`HW2_Pylypenko_SMM_Plan_Execute.ipynb`. Notebook використовує ті самі Python-модулі,
тому не дублює бізнес-логіку.

## 2. Доменна задача

Запит-приклад:

> Проаналізуй YouTube-тренди про AI agents за останні 7 днів, перевір brand
> safety та заплануй SMM-кампанію.

Агент знаходить кандидатів, самостійно звертається до бази знань за правилами,
формує два користувацькі списки та зупиняється:

1. `approved` — позиції, що не збіглися із retrieved-заборонами;
2. `needs_review` — контекстно неоднозначні позиції.

Hard-block контент (порнографія і графічне насильство) зберігається окремо в
`blocked` та не може бути повернений звичайним review. Людина може прийняти всі
сумнівні позиції, відхилити всі або передати конкретні `video_id`. Прийняті
позиції об'єднуються з наявним топом і повторно сортуються за `trend_score`.

## 3. Архітектура

```text
START
  ↓
planner ── Plan(goal, steps)
  ↓
executor ── один tool / один крок
  ↓
replanner ── ReplanDecision(continue | replan | finish)
  ├── executor
  ├── moderation_review ── interrupt ──→ replanner
  ├── campaign_approval ── interrupt ──→ replanner
  └── END
```

Обов'язкові три вузли з умови — `planner`, `executor`, `replanner`. Два додаткові
вузли є approval gates і не замінюють Plan-and-Execute цикл.

### Structured outputs

- `Plan`: `goal`, `steps`;
- `ReplanDecision`: `action`, `updated_steps`, `reasoning`.

Production-провайдери використовують `with_structured_output(...)`. Для
відтворюваних тестів є `ScriptedPlanExecuteLLM` із тим самим контрактом.

## 4. Інструменти

| Tool | Тип | Призначення |
|---|---|---|
| `search_recent_videos` | read-only | Пошук свіжих YouTube-кандидатів |
| `search_knowledge` | Agentic RAG | Пошук brand-safety правил у ChromaDB |
| `evaluate_trends` | read-only analysis | `approved / needs_review / blocked` і топ |
| `schedule_campaign` | risky write | Симуляція планування кампанії після approval |

Кожен tool має окрему Pydantic v2 input-схему з валідацією та описом.

## 5. База знань

`knowledge_documents.json` містить 12 змістовних документів:

- sexual/pornographic content;
- graphic violence;
- child safety;
- hate and extremism;
- self-harm і dangerous challenges;
- sensitive news, war і спортивні бої;
- scams;
- privacy/doxxing;
- medical/financial claims;
- copyright/reused content;
- brand tone;
- human review і campaign approval.

Документи індексуються у `chroma_db/` через `chromadb.PersistentClient`.
Локальний детермінований embedding не потребує завантаження моделі й робить
fixture-тести відтворюваними. `POL-01` і `POL-02` є обов'язковими hard-block
правилами в policy set, щоб критична заборона не випадала через retrieval miss.

## 6. Human-in-the-Loop

### Gate 1: content moderation

Payload показує обидва списки та raw metadata відео. Відповідь:

```json
{
  "decision": "approve_selected",
  "acceptable_video_ids": ["boxingai01"],
  "reason": "Спортивний не-графічний контекст прийнятний"
}
```

Також підтримуються `approve_all` і `reject_all`.

### Gate 2: campaign approval

Перед `schedule_campaign` UI/CLI отримує точні параметри дії. Варіанти:

```json
{"decision": "approve"}
```

```json
{
  "decision": "edit",
  "edits": {"planned_date": "2026-09-05", "note": "Після legal review"}
}
```

```json
{"decision": "reject", "reason": "Кампанію потрібно доопрацювати"}
```

`edit` має allowlist полів, а `video_ids` можуть містити лише позиції з
фінального схваленого топу.

## 7. Persistence

`agent_state.db` — звичайний SQLite-файл, не `:memory:`. Checkpoint зберігає
стан на кожному superstep. Повторне створення Python-процесу з тим самим
`thread_id` відновлює interrupt і весь прогрес. Інший `thread_id` має незалежний
state.

CLI-демонстрація трьома окремими процесами:

```powershell
python run_agent.py start --thread-id demo-001

python run_agent.py resume --thread-id demo-001 `
  --decision '{\"decision\":\"approve_selected\",\"acceptable_video_ids\":[\"boxingai01\"]}'

python run_agent.py resume --thread-id demo-001 `
  --decision '{\"decision\":\"approve\"}'

python run_agent.py state --thread-id demo-001
```

## 8. Встановлення і запуск

```powershell
cd C:\Study\AI_agent_LLM\HW2_Pylypenko_SMM_Plan_Execute
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Відтворюваний режим без API-ключа:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id local-demo
```

Gemini:

```powershell
Copy-Item .env.example .env
# Додати GOOGLE_API_KEY
..\.venv\Scripts\python.exe run_agent.py --llm gemini start --thread-id gemini-demo
```

## 9. Тести й демонстраційні артефакти

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe test_runner.py
```

`test_runner.py` створює `demo_results.json`, наповнює `agent_state.db` і
доказово показує:

- чотирикроковий план;
- pause на moderation gate;
- відновлення після закриття і повторного створення агента;
- незалежність двох `thread_id`;
- додавання обраної людиною позиції до топу;
- окремий campaign approval і фактичне виконання лише після approve.

## 10. Аналіз результатів

Контрольний fixture-запуск формує повний план із чотирьох кроків та виконує
інструменти послідовно: `search_recent_videos`, `search_knowledge`,
`evaluate_trends`, `schedule_campaign`. База знань містить 12 документів, тому
вимога про щонайменше 8 доменних документів виконується.

Після автоматичної перевірки агент повертає 10 однозначно прийнятних позицій,
2 сумнівні та 2 hard-block позиції. У демонстраційному HITL-сценарії оператор
схвалює тільки `boxingai01`: кількість схвалених позицій зростає до 11, відео
додається до відсортованого `final_top`, а інша сумнівна позиція не додається.
Після другого approval gate `schedule_campaign` виконується, статус кампанії
стає `scheduled`, а workflow завершується з `completed=True`.

Окремий reject-тест підтверджує, що ризиковий tool не виконується після відмови.
Повторне створення агента з тим самим `thread_id` відновлює checkpoint, тоді як
інший `thread_id` має незалежний стан. Автоматизована перевірка завершується
результатом `5 passed`.

## 11. Обмеження

- Fixture-режим призначений для оцінювання архітектури, а не поточного YouTube.
- Safety-перевірка аналізує лише title/description/tags. Вона не переглядає
  кадри, audio або transcript і не заявляє повної модерації відео.
- `schedule_campaign` є навчальною симуляцією write-дії та записує append-only
  `campaign_actions.jsonl`; реальна публікація не виконується.
- Реалізація навмисно обмежена механізмами навчальних тем 3–4.

## 12. Структура

```text
HW2_Pylypenko_SMM_Plan_Execute/
├── HW2_Pylypenko_SMM_Plan_Execute.ipynb
├── smm_plan_agent/
│   ├── graph.py
│   ├── models.py
│   ├── tools.py
│   ├── knowledge.py
│   ├── data_source.py
│   ├── scripted.py
│   └── factory.py
├── fixtures/youtube_videos.json
├── knowledge_documents.json
├── tests/test_workflow.py
├── run_agent.py
├── test_runner.py
├── agent_state.db
├── demo_results.json
└── requirements.txt
```
