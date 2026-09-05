# Інструкція для звичайного користувача

## Найпростіший спосіб — Jupyter Notebook

1. Відкрийте папку `HW3_Pylypenko_ROZETKA_Competitive_SMM_MAS` у VS Code.
2. Відкрийте `HW3_Пилипенко_ROZETKA_Competitive_SMM_MAS.ipynb`.
3. Виберіть Python із середовища `C:\Study\AI_agent_LLM\.venv`.
4. Натисніть **Restart**, потім **Run All**.
5. Перегляньте таблиці та три дашборди.
6. У блоці погодження:
   - натисніть **Вибрати всю TOP-рекламу** або зніміть непотрібні позиції;
   - натисніть **Вибрати всі пости** або зніміть зайві;
   - відредагуйте тексти у великих полях;
   - натисніть **Підтвердити вибране**.
7. Непозначені матеріали автоматично відсікаються. Оригінальні вхідні дані не змінюються.
8. Якщо показано червоне попередження про заборонену тему, не погоджуйте цей матеріал без ручної перевірки.

Notebook містить окрему автоматичну демонстрацію, тому фінальні виправлені пости видно одразу після `Run All`, навіть якщо інтерактивні кнопки ще не натискалися.

## Перевірка Python-скриптів

У PowerShell виконуйте лише рядки, що починаються з `..\.venv\Scripts\python.exe`. JSON із результату не є командою PowerShell.

```powershell
cd C:\Study\AI_agent_LLM\HW3_Pylypenko_ROZETKA_Competitive_SMM_MAS
..\.venv\Scripts\python.exe -m pytest -v
```

Почати повний workflow:

```powershell
..\.venv\Scripts\python.exe run_agent.py start --thread-id manual-001
```

Погодити всі TOP-публікації та чернетки:

```powershell
..\.venv\Scripts\python.exe run_agent.py review --thread-id manual-001 --decision approve
```

Підтвердити експорт:

```powershell
..\.venv\Scripts\python.exe run_agent.py export --thread-id manual-001 --decision approve
```

Відмовитися від експорту:

```powershell
..\.venv\Scripts\python.exe run_agent.py export --thread-id manual-001 --decision reject
```

Змінити ім’я вихідного JSON-файлу:

```powershell
..\.venv\Scripts\python.exe run_agent.py export --thread-id manual-001 --decision edit --path outputs/manual_report.json
```

Переглянути збережену контрольну точку:

```powershell
..\.venv\Scripts\python.exe run_agent.py state --thread-id manual-001
```

Для кожної нової перевірки використовуйте новий `thread-id`. Після `start` дочекайтеся
`next: ["approval_gate"]`; після `review` — `next: ["risky_export"]`. JSON, який
виводиться після команди, є результатом, а не наступною командою PowerShell.

## Перевірка MCP, evals, red-team і CrewAI

Виконуйте по одній команді та дочікуйтеся повернення запрошення PowerShell:

```powershell
..\.venv\Scripts\python.exe mcp_demo.py
..\.venv\Scripts\python.exe mcp_langgraph_demo.py
..\.venv\Scripts\python.exe evals.py
..\.venv\Scripts\python.exe red_team.py
..\.venv\Scripts\python.exe mas_crewai.py
..\.venv\Scripts\python.exe comparison_metrics.py
```

- MCP LangGraph demo має повернути два записи зі `status: ok`.
- `evals.py` і `red_team.py` мають повернути `passed: 5, total: 5`.
- `mas_crewai.py` показує короткий offline-підсумок; `--full` виводить повний JSON.
- CrewAI offline demo не викликає зовнішню LLM, тому `llm_tokens` дорівнює нулю.
- Live `Crew.kickoff()` і LangSmith trace запускаються лише після локального додавання API-ключа.

## Важливі позначки

- `fixture` — синтетичні навчальні дані, а не актуальна статистика бренду.
- `null + views_status` — показник недоступний; це не нуль.
- `audience_inference` — припущення за темою та форматом, а не реальна демографія.
- `conversion_signal_score` — непрямий сигнал, а не доведений продаж.
- `paid_ad + confirmed` — запис дозволено включати в рейтинг рекламних матеріалів.
