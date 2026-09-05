# Інструкція користувача

## 1. Підготовка

Відкрийте PowerShell і перейдіть до каталогу проєкту:

```powershell
cd C:\Study\AI_agent_LLM\Task_002_Pylypenko_UA_Language_MAS
```

Усі наведені нижче команди вводьте **по одній** і після кожної натискайте Enter. JSON, який програма надрукує у відповідь, повторно вводити в PowerShell не потрібно.

Команди розраховано на поточний навчальний workspace зі спільним `..\.venv`. Якщо проєкт запущено з окремо розпакованого архіву, створіть і активуйте локальний `.venv` за README та використовуйте `python` замість `..\.venv\Scripts\python.exe`.

## 2. Автоматична перевірка

```powershell
..\.venv\Scripts\python.exe -m pytest -v
```

Очікуваний підсумок — `45 passed`. Попередження `IncompleteFieldDefinitionWarning` надходить зі сторонньої залежності MCP/Pydantic і не є падінням тестів.

## 3. Повна offline-демонстрація

```powershell
..\.venv\Scripts\python.exe run_demo.py
```

Програма повинна повідомити:

- `status: completed`;
- `applied: 12`;
- `rejected: 0`;
- `langgraph_crewai_findings_equal: true`.

Цей сценарій використовує ті самі правила, що й notebook. Людина погоджує коректні пропозиції та один раз подає власний варіант: `дедлайн → кінцевий термін`.

Відкрийте результати:

```powershell
notepad outputs\corrected_document.txt
notepad outputs\linguistic_report.txt
notepad outputs\demo_result.json
```

`[EMAIL_REDACTED]` у вихідному тексті — очікувана робота захисту від витоку персональних даних.

## 4. Jupyter Notebook

Відкрийте `Task_002_Пилипенко_Мовна_MAS.ipynb` у VS Code, натисніть `Restart`, потім `Run All`.

Notebook показує:

1. оригінальні TXT, DOCX, PDF і PNG;
2. JSON після Document Intake Agent;
3. окремі результати Grammar, Style, Terminology, Structure і Verifier;
4. однозначні та сумнівні пропозиції;
5. рішення людини `approve/edit/reject`;
6. повний виправлений текст;
7. таблицю `Оригінал → Після HITL`;
8. CrewAI parity, MCP discovery, red-team, audit hash-chain і pytest.

Якщо notebook показує старі імпорти або результати, закрийте вкладку, відкрийте файл повторно, натисніть `Restart` і `Run All`.

## 5. Перевірка окремого документа

Файл має лежати у серверному каталозі `fixtures/documents`. Довільні абсолютні шляхи навмисно блокуються.

```powershell
..\.venv\Scripts\python.exe run_ingestion.py --file example.pdf --request-id manual-pdf --analyze
```

Замість `example.pdf` можна використати `example.txt`, `example.docx` або `example.png`. У відповіді `intake.status=ok` підтверджує парсинг, а `analysis.status=awaiting_review` означає, що пропозиції готові, але ще не застосовані без людини.

## 6. Ручний Human-in-the-Loop

Запустіть новий workflow з унікальним `thread-id`:

```powershell
..\.venv\Scripts\python.exe run_langgraph.py start --thread-id manual-001
```

Буде створено `outputs/review_template.json`. За замовчуванням усі позиції мають безпечне рішення `reject`.

Для погодження змініть відповідну позицію на:

```json
{"finding_id": "f-...", "decision": "approve", "reason": "Погоджено"}
```

Для власної редакції використайте:

```json
{"finding_id": "f-...", "decision": "edit", "edited_fix": "кінцевий термін", "reason": "Варіант користувача"}
```

Для відмови залиште:

```json
{"finding_id": "f-...", "decision": "reject", "reason": "Не погоджено"}
```

Кожен finding повинен мати рівно одне рішення. Після збереження файла продовжте той самий thread:

```powershell
..\.venv\Scripts\python.exe run_langgraph.py resume --thread-id manual-001 --review outputs\review_template.json
```

Перегляд стану:

```powershell
..\.venv\Scripts\python.exe run_langgraph.py state --thread-id manual-001
```

Якщо всі рішення залишено `reject`, текст закономірно не отримає мовних замін. Це правильна поведінка HITL, а не помилка.

## 7. CrewAI та MCP

Відтворюваний CrewAI-compatible режим без API:

```powershell
..\.venv\Scripts\python.exe run_crewai.py --mode scripted
```

Статус `awaiting_review` є правильним: CrewAI виконав аналіз, але не має права самостійно застосувати ризиковий tool.

Перевірка чотирьох FastMCP tools:

```powershell
..\.venv\Scripts\python.exe -c "import asyncio; from language_mas.mcp_integration import list_language_mcp_tool_names; print(asyncio.run(list_language_mcp_tool_names()))"
```

Мають відобразитися `parse_document`, `search_language_rules`, `lookup_word_forms` та `apply_approved_corrections`.

## 8. Native CrewAI і LangSmith

Цей крок необов’язковий для offline-перевірки та потребує власних ключів. Скопіюйте `.env.example` у `.env`, але ніколи не додавайте `.env` до Git.

```powershell
$env:GOOGLE_API_KEY="ваш_ключ"
..\.venv\Scripts\python.exe run_crewai.py --mode native --model gemini/gemini-2.5-flash
```

Для LangSmith встановіть `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY` і `LANGSMITH_PROJECT`, після чого запустіть `run_demo.py`.

## 9. Типові ситуації

- `Unexpected token ':'` — JSON-результат помилково введено як команду. Натисніть Esc або Ctrl+C і вводьте лише команди з блоків `powershell`.
- `awaiting_review` — workflow штатно чекає рішення людини.
- Усі зміни відхилені — у `review_template.json` залишилися лише `reject`.
- `ModuleNotFoundError` — команда запущена не з каталогу проєкту або вибрано інший Python.
- Старий код у notebook — виконайте `Restart` і `Run All`.
- `Traceback` — це справжня помилка; збережіть повний текст від першого рядка `Traceback` до останнього повідомлення.
