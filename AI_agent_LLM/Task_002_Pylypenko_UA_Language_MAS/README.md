# Практичне завдання №2 — безпечна мовна MAS

Навчальний проєкт перевіряє український текст, поданий як структурований JSON. Результат містить доказові `Finding`, два списки пропозицій для людини та виправлену **копію** JSON лише після Human-in-the-Loop. Оригінал не мутується.

Проєкт має відтворюваний `scripted` режим без API, нативний LangGraph workflow, нативну CrewAI-конфігурацію, власний FastMCP-сервер, LangSmith hooks, локальне JSONL tracing і pytest.

Для першого запуску використовуйте [покрокову інструкцію користувача](USER_GUIDE.md). У ній команди відокремлено від прикладів результату, щоб JSON-вивід випадково не вводився в PowerShell.

## Архітектура

```text
TXT / DOCX / PDF / PNG-JPEG або готовий JSON
   │
   ▼
Document Intake Agent ── scoped parser → незмінений структурований JSON
   │
   ▼
Input guardrail ── injection → blocked/quarantine
   │
   ▼
Supervisor (без tools, step budget)
   ├── Grammar Agent ───── search_language_rules + lookup_word_forms
   ├── Style Agent ─────── search_language_rules
   ├── Terminology Agent ─ search_language_rules(category=terminology)
   └── Structure Agent ─── без зовнішніх tools
           │
           ▼
Verifier Agent ─ grounding, deduplication, незмінність цифр/фактів
           │
           ▼
Human review: approve / edit / reject
           │
           ▼
apply_approved_corrections (ризиковий MCP tool, окремий executor)
           │
           ▼
PII redaction → JSON + TXT report + нова погоджена TXT-копія
```

Supervisor використовує структурований `Command(goto=...)`, а не пошук службових слів у тексті LLM. Кожен спеціаліст повертає diff стану і передає керування supervisor. `interrupt()` формує динамічний approval gate; `Command(resume=...)` відновлює той самий `thread_id`.

Workflow має явний детермінований Plan-and-Execute план: `grammar → style → terminology → structure → verify → approval`. Для відомого стабільного процесу LLM-planner навмисно не використовується: це усуває проблему ненадійних текстових маркерів у плані та не витрачає токени на маршрутизацію. Supervisor виконує план за структурованими `step_id` і статусами.

### Агенти та права

| Агент | Дані | Дозволені MCP tools | Делегування |
|---|---|---|---|
| Document Intake | один файл із `fixtures/documents` | `parse_document` | заборонено |
| Supervisor | метадані та статуси | немає | лише відомим спеціалістам |
| Grammar | вузли поточного документа | `search_language_rules`, `lookup_word_forms` | заборонено |
| Style | вузли поточного документа | `search_language_rules` | заборонено |
| Terminology | поточний документ і scoped glossary | `search_language_rules` | заборонено |
| Structure | `node_id`, порядок і поточний текст | немає | заборонено |
| Verifier | findings, вихідні фрагменти, evidence | read-only lookup | заборонено |
| Approval executor | підтверджені рішення | `apply_approved_corrections` | заборонено |

Адміністративних tools у workflow немає. Роль, `tenant_id` і `user_id` не читаються з користувацького JSON: їх передає серверний `ActorContext`.

## JSON-контракт

Приклад знаходиться у `fixtures/demo_request.json`:

```json
{
  "request_id": "demo-001",
  "document": {
    "document_id": "official-letter-001",
    "language": "uk",
    "register": "official",
    "nodes": [
      {"node_id": "p-001", "node_type": "paragraph", "text": "Текст для перевірки."}
    ]
  }
}
```

Pydantic v2 забороняє зайві поля, дублікати `node_id`, невідомі options, непідтримувану мову і невалідні HITL-рішення. Усі tool-відповіді мають контракт `status + data/error`.

## FastMCP

`mcp_server.py` експонує рівно чотири tools відповідно до умови завдання:

1. `parse_document` — безпечне TXT/DOCX/PDF/image → JSON перетворення;
2. `search_language_rules` — контрольований RAG із provenance і checksum;
3. `lookup_word_forms` — словозміна і відмінювання;
4. `apply_approved_corrections` — ризикова зміна копії JSON.

Термінологічний пошук виконує `search_language_rules` з категорією `terminology`, тому окремий дублюючий tool не потрібен. Ризиковий apply фізично не входить до allowlist жодного модельного спеціаліста й доступний тільки детермінованому approval executor після HITL.

Intake приймає лише відносне ім’я файла з серверного `fixtures/documents`, перевіряє resolved path, розмір і сигнатуру. Додатково обмежено кількість і сумарний розпакований розмір DOCX, PDF — до 50 сторінок, зображення — до 25 млн пікселів, витягнутий текст — до 60 000 символів. TXT читається як UTF-8, DOCX через `python-docx`, PDF через текстовий шар `pypdf`. Для PNG/JPEG використовується локальний Tesseract, якщо він установлений. Навчальний PNG без Tesseract використовує явно позначений fixture test double з metadata — це забезпечує offline-відтворюваність, але не видається за production OCR.

LangGraph adapter реалізований у `language_mas/mcp_integration.py` через `MultiServerMCPClient`. CrewAI native agents використовують `MCPServerStdio` і окремий `create_static_tool_filter` для кожної ролі.

Перевірка discovery:

```powershell
..\.venv\Scripts\python.exe -c "import asyncio; from language_mas.mcp_integration import list_language_mcp_tool_names; print(asyncio.run(list_language_mcp_tool_names()))"
```

MCP Inspector:

```powershell
npx @modelcontextprotocol/inspector ..\.venv\Scripts\python.exe mcp_server.py
```

## Контрольований RAG

Локальний корпус `knowledge/language_rules.json` використовує лише allowlisted джерела, authority, версію, trust level і SHA-256 checksum. Агенти не мають web-доступу.

Основні джерела:

- [Український правопис, офіційне видання 2026](https://mon.gov.ua/static-objects/mon/sites/1/zagalna%20serednya/Pravopys.2019/ukrayinskii-pravopis-oficiine-vidannia-2026.pdf);
- [Стандарт державної мови «Український правопис»](https://mova.gov.ua/diyalnist-i-proyekti/termini/pravopys-ukrainskoi-movy);
- [Стандарти української термінології](https://mova.gov.ua/diyalnist-i-proyekti/termini);
- [опис системи «Словники України»](https://lcorp.ulif.org.ua/pdf/Pro_Systemu.pdf);
- [Закон про функціонування української мови як державної](https://zakon.rada.gov.ua/go/2704-19) — джерело політики застосування, не граматичних замін.

Навчальний fixture містить короткі авторські узагальнення правил, а не копії повних документів.

## Встановлення

У поточному навчальному workspace вже використовується спільне середовище `C:\Study\AI_agent_LLM\.venv`, тому команди нижче мають префікс `..\.venv\Scripts\python.exe`.

Для запуску розпакованого архіву на іншому комп’ютері створіть локальне середовище:

```powershell
cd C:\Study\AI_agent_LLM\Task_002_Pylypenko_UA_Language_MAS
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Після активації локального `.venv` замініть у прикладах `..\.venv\Scripts\python.exe` на звичайне `python`.

Не додавайте API-ключі до Git. Скопіюйте `.env.example` у `.env` і заповнюйте тільки локально.

## Запуск

### Найкоротша перевірка

Перебуваючи в каталозі проєкту, виконайте по черзі:

```powershell
..\.venv\Scripts\python.exe -m pytest -q
..\.venv\Scripts\python.exe run_demo.py
notepad outputs\corrected_document.txt
```

Успішний результат: `45 passed`, `status=completed`, `applied=12`, `rejected=0`, `langgraph_crewai_findings_equal=true`. Це приклад очікуваного виводу, а не додаткові PowerShell-команди.

### Повний offline demo

```powershell
..\.venv\Scripts\python.exe run_demo.py
```

Створюються:

- `outputs/demo_result.json`;
- `outputs/linguistic_report.txt`;
- `outputs/corrected_document.txt` — нова копія лише з погодженими змінами;
- `traces/langgraph_demo_secure.jsonl`;
- `traces/crewai_demo_secure.jsonl`;
- `traces/mcp.jsonl`.

### LangGraph із ручним HITL

```powershell
..\.venv\Scripts\python.exe run_langgraph.py start --thread-id check-001
```

Команда зупиниться перед застосуванням змін і створить `outputs/review_template.json`. Відредагуйте для кожного finding поле `decision` (`approve`, `edit`, `reject`). Для `edit` додайте `edited_fix`.

```powershell
..\.venv\Scripts\python.exe run_langgraph.py resume --thread-id check-001 --review outputs/review_template.json
..\.venv\Scripts\python.exe run_langgraph.py state --thread-id check-001
```

Стан зберігається у `workflow_state.db` через `SqliteSaver`. Підтверджене рішення `edit` додатково записується у `user_correction_memory.db`: у наступних потоках того самого користувача воно замінює стандартну пропозицію агента. `approve` і `reject` нових правил не створюють.

Приклад власного рішення у review-файлі:

```json
{
  "finding_id": "f-...",
  "decision": "edit",
  "edited_fix": "кінцевий термін",
  "reason": "Бажана термінологія користувача"
}
```

### Парсинг різних документів

Приклади вже збережені у `fixtures/documents`. Команда нижче показує JSON Document Intake Agent і результати всіх мовних агентів до HITL:

| Файл | Навчальний зміст |
|---|---|
| `example.txt` | наказ: Коваленко/Журавель, керування відмінками, кальки, термін, повтор і дубльований абзац |
| `example.docx` | службова записка: Бондар/Круть, російські кальки, канцеляризми, тавтологія і дублювання |
| `example.pdf` | двосторінковий протокол: Журавель/Швець/Коваленко, помилки на обох сторінках і точні page references |
| `example.png` | оголошення: OCR, Швець і правильна контрольна форма жіночого прізвища Журавель, кальки й тавтологія |

Усі ПІБ у fixtures вигадані. Чоловічі прізвища подано як контрольовані помилки відмінювання; жіночі прізвища на приголосний — як коректні негативні приклади, які агент не повинен позначати.

```powershell
..\.venv\Scripts\python.exe run_ingestion.py --file example.pdf --analyze
```

Замість `example.pdf` можна передати `example.txt`, `example.docx` або `example.png`. Довільні абсолютні шляхи та вихід за межі intake-каталогу блокуються.

### CrewAI

Відтворюваний режим без ключа:

```powershell
..\.venv\Scripts\python.exe run_crewai.py --mode scripted
```

Нативний hierarchical CrewAI з manager-agent і MCP:

```powershell
$env:GOOGLE_API_KEY="ваш_ключ"
..\.venv\Scripts\python.exe run_crewai.py --mode native --model gemini/gemini-2.5-flash
```

У native-режимі зовнішня модель може формулювати текст інакше. Для pytest і точного порівняння використовується спільний deterministic domain layer.

### Jupyter Notebook

Відкрийте `Task_002_Пилипенко_Мовна_MAS.ipynb` і виконайте `Run All`. Notebook автоматично знаходить каталог проєкту та показує реальні TXT/DOCX/PDF/PNG fixtures, JSON кожного parser, права і результати кожного агента, RAG-джерела, два списки findings, HITL, виправлену копію, TXT-звіт, CrewAI parity, MCP discovery, red-team і pytest.

## Tracing

Локальне JSONL tracing працює завжди й навмисно не містить сирого тексту, prompt, query або запропонованої заміни. Логуються лише контрольні метадані: `timestamp`, `event`, `node_name/agent_name/tool_name`, `request_id`, `document_id`, tenant/user ID, статус, error code, тривалість, використані ліміти та лічильники. Записи з’єднані полями `previous_hash`/`record_hash`; пошкоджений hash-chain не можна непомітно продовжити.

| Контрольована точка | Що фіксується |
|---|---|
| Document Intake | формат, розмір, SHA-256 джерела, кількість JSON-вузлів, час, статус |
| Supervisor і спеціалісти | маршрут, agent, кількість findings, step/finding budget, час |
| Verifier | скільки findings отримано й підтверджено |
| MCP | назва tool, статус, error code, час — без аргументів |
| HITL | кількість `approve/edit/reject` — без текстів рішень |
| Apply/output | кількість застосованих змін та ім’я нової копії |

Для LangSmith:

```powershell
$env:LANGSMITH_TRACING="true"
$env:LANGSMITH_API_KEY="ваш_ключ"
$env:LANGSMITH_PROJECT="task-002-language-mas"
..\.venv\Scripts\python.exe run_demo.py
```

LangGraph автоматично передає graph traces, а обидві реалізації мають `@traceable` entrypoints. Для здачі зробіть screenshot trace або експортуйте його JSON після запуску зі своїм ключем. Локальна траєкторія генерується notebook і `run_demo.py`; санітизований приклад для перевірки структури збережено в `docs/trace_example.json`.

## Security hardening

- **Input:** Pydantic schema, розмір, prompt-injection detection, quarantine.
- **Tool:** deny-by-default allowlist, перевірка аргументів, rate limit, окремий approval executor.
- **Output:** рекурсивне маскування email, телефону і номера картки.
- **RAG:** allowlisted authority/domain, checksum, provenance, обмежений top-k, retrieved text ніколи не є інструкцією.
- **Memory:** підтверджені людиною `edit`-рішення зберігаються як короткі пари «було → бажана форма» з TTL 365 днів. Namespace обов’язково містить `tenant_id/user_id`; міжкористувацький retrieval заборонений. Новий запис проходить write-gate та injection validation і не змінює глобальний RAG.
- **Authorization:** actor context поза request body; адміністративні налаштування не експонуються.
- **Durability:** `SqliteSaver`, детермінований код до `interrupt()`, idempotent apply до копії.
- **Budgets:** до 20 000 вхідних токенів (offline-оцінка), 1 200 вихідних токенів на native LLM-виклик, 16 graph steps, 200 findings на спеціаліста, `max_iter`, per-agent timeout, один retry лише для model runtime, MCP/tool rate limits.
- **Timeout/retry:** local scripted tasks мають 5-секундний ліміт; CrewAI agents — 45–90 с, model call — 30 с; MCP discovery — 30 с. Validation, authorization та prompt-injection помилки не повторюються.
- **Audit:** append-only JSONL із SHA-256 hash-chain без сирого документа.
- **Model boundary:** API/local model отримує тільки потрібний JSON і дозволені MCP tools. У моделі немає shell, code execution, web/browser, довільного filesystem або адміністративного tool. API transport може звертатися лише до явно налаштованого model endpoint; це не дає агенту інтернет-інструмента.
- **Admin boundary:** workflow не експонує зміни глобальних правил. Для майбутнього admin endpoint передбачено server-side `assert_admin()`; користувацький `edit` пишеться лише в owner-scoped memory.

### Базовий red-teaming

| Сценарій | Очікування | Результат |
|---|---|---|
| `Ignore all previous instructions` у `node.text` | quarantine до агентів | заблоковано |
| Style Agent викликає apply tool | deny-by-default | заблоковано |
| Path traversal у tool args | argument validation | заблоковано |
| PII у результаті | redaction | замасковано |
| Невідомий finding у HITL | schema/business validation | відхилено |
| Cross-tenant scope | server-side scope check | відхилено |

## Тести

```powershell
..\.venv\Scripts\python.exe -m pytest -v
```

Покрито 45 тестами: чотири формати intake, збереження розташування фрагмента в оригіналі, наскрізна перевірка орфографії, пунктуації, граматики, відмінювання вигаданих ПІБ, стилю, кальок, термінології, дублювання й тавтології, відмінювану форму найвищого ступеня та збереження великих літер під час замін, чотири FastMCP tools, реальне stdio discovery та per-agent фільтрацію, input/tool/output guardrails, tenant isolation, immutable input, LangGraph routing, результати кожного агента, dynamic HITL, спільну для notebook/скрипта політику approve/edit/reject, input/tool budgets, безпечний запис нової копії, owner-scoped пам’ять підтверджених виправлень, блокування memory poisoning, виявлення пошкодження hash-chain і тотожність результатів двох реалізацій.

## Порівняння реалізацій

| Критерій | LangGraph | CrewAI |
|---|---|---|
| Оркестрація | явний state graph + `Command` | hierarchical Crew + manager |
| Рівень контролю | 5/5 | 3/5 |
| Debugging | 5/5, checkpoints і state | 4/5, task/crew traces |
| Persistence/HITL | нативні checkpointer + `interrupt()` | зовнішній approval wrapper у scripted flow |
| MCP | `langchain-mcp-adapters` | `mcps` + `MCPServerStdio` filters |
| Least privilege | явна матриця + guardrail | per-agent MCP filters |
| LOC основного workflow | 361 | 234 |
| Координаційні LLM-виклики | 0 у scripted graph | 1+ на крок у hierarchical native mode |
| Точна відтворюваність | висока | scripted — висока; native — залежить від LLM |
| Token usage | 0 у scripted mode | 0 scripted; native повертає usage metrics |
| Вартість offline demo | $0 | $0 |

LOC пораховано для `language_mas/langgraph_mas.py` і `language_mas/crewai_mas.py` у поточній версії. Фактичне token/cost значення native-запуску залежить від моделі та її тарифу; `run_native()` зберігає `token_usage`, якщо провайдер його повертає.

## Відповіді на аналітичні питання

1. **Чому supervisor, а не swarm?** Ризикова операція й різні права потребують централізованого, передбачуваного маршруту та єдиного audit trail.
2. **Навіщо MCP, якщо функції локальні?** MCP відділяє reasoning від мовних сервісів, дає стабільні схеми tools і дозволяє пізніше замінити локальний словник зовнішнім сервісом без зміни агентів.
3. **Чому apply tool не видається мовним агентам?** Аналіз і побічна дія мають різний рівень ризику. Навіть скомпрометований спеціаліст не повинен змінити документ.
4. **Де LangGraph зручніший за CrewAI?** У persistence, точному routing, state inspection і HITL. CrewAI коротше описує ролі, але hierarchical manager додає координаційні LLM-виклики.
5. **Як підтримуються документи?** Окремий Document Intake Agent уже перетворює TXT/DOCX/PDF/PNG-JPEG на чинний JSON-контракт. Для довільних фото production-розширення замінює fixture test double локальним Tesseract/OCR backend без зміни мовних агентів.

## Матриця відповідності умовам практичного завдання

| Обов’язкова вимога | Де реалізовано | Статус |
|---|---|---|
| LangGraph supervisor/coordinator + 3+ agents | `language_mas/langgraph_mas.py`: supervisor, 4 specialists, verifier | виконано |
| Ролі, tools, handoff | `SPECIALISTS`, `EXECUTION_PLAN`, `TOOL_PERMISSIONS`, таблиця вище | виконано |
| Той самий кейс у CrewAI | `language_mas/crewai_mas.py`: scripted parity + native hierarchical Crew | виконано |
| Порівняння LOC/control/debug/tokens | розділ «Порівняння реалізацій» | виконано |
| FastMCP із 3–4 tools | `mcp_server.py`: рівно 4 tools | виконано |
| MCP інтегровано | LangChain MCP adapter та CrewAI `MCPServerStdio` filters | виконано |
| LangSmith/Langfuse tracing | `@traceable`, змінні `LANGSMITH_*`; локальний trace показано в notebook | виконано кодом; cloud trace потребує особистого ключа |
| Input guardrail | багатомовна injection/encoded payload detection до запуску агентів | виконано |
| Tool guardrail | deny-by-default allowlist, Pydantic/argument/path validation, rate limits | виконано |
| Output guardrail | рекурсивне PII redaction | виконано |
| HITL ризикового tool | LangGraph `interrupt()`; apply недоступний модельним агентам | виконано |
| MCP ≥3 + guardrails ≥3 tests | повний набір `pytest`; фактична кількість наведена вище | виконано |
| README, notebook, trace JSON | цей файл, виконаний `.ipynb`, `docs/trace_example.json` | виконано |
| Коментарі українською, структурований код | пакет `language_mas`, окремі CLI/tests/fixtures | виконано |

Єдина зовнішня дія перед здачею: якщо викладач вимагає саме скріншот хмарного LangSmith UI, запустіть demo зі своїм `LANGSMITH_API_KEY` і додайте скріншот. Без секретного ключа проєкт уже показує санітизований локальний trace та ті самі `@traceable` spans.

## Межі поточної версії

- Мовне ядро завжди приймає JSON; окремий Document Intake Agent уже перетворює TXT, DOCX, PDF та PNG/JPEG у цей контракт.
- Повноцінний OCR довільних фото потребує локального Tesseract з українською моделлю; bundled PNG fallback є лише прозоро позначеним test double.
- Словниковий fixture демонструє патерн, але не замінює повної морфологічної бази.
- Реальний LangSmith trace та native CrewAI token usage потребують особистого API-ключа.
- Жодне виправлення не застосовується до оригіналу й не стає глобальним правилом.
