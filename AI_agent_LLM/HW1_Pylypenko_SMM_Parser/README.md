# YouTube Trends Intelligence Agent

## 1. Опис проєкту

У проєкті реалізовано ReAct-агента для пошуку загальних і тематичних трендів YouTube за останні сім днів. Агент працює у LangGraph, сам обирає та послідовно викликає read-only tools, ранжує відео за переглядами й свіжістю та повертає строгий Pydantic-звіт із клікабельними посиланнями. Основний LLM-провайдер — Google Gemini 2.5 Flash. YouTube Data API не використовується: live-режим читає публічний HTML, а fixture-режим забезпечує відтворювані тести.

Основний оформлений артефакт: `HW1_Pylypenko_YouTube_Trends_Agent.ipynb`.

## 2. Доменна задача

- **Домен:** SMM Intelligence / конкурентний і контентний аналіз.
- **Що вирішує агент:** знаходить трендові YouTube-відео загалом або за заданою темою, обмежує період, збирає доступні перегляди, формує топ і виділяє повторювані теми та канали.
- **Період за замовчуванням:** 7 днів.
- **Розмір рейтингу:** до 20 відео.
- **Версія 1.0 не збирає:** лайки, коментарі, приватні дані або відеофайли.

### Інструменти

- `search_recent_videos` — знаходить загальні або тематичні відео і створює тимчасовий `dataset_id`.
- `enrich_video_statistics` — нормалізує перегляди, дату, тривалість та обчислює trend score.
- `rank_trending_videos` — формує топ за переглядами і загальним trend score.
- `analyze_topic_signals` — визначає повторювані слова та найактивніші канали.

Кожен tool має окрему Pydantic v2 input-модель з `Field(description=...)`, `field_validator`, забороною зайвих полів і докладним docstring.

## 3. Архітектура

```text
START
  ↓
agent (Gemini + bind_tools)
  ├── tool_calls → tools (ToolNode) ──→ agent
  └── final text → formatter
                         ↓
               TrendReport (Pydantic)
                         ↓
                        END
```

Штатний ReAct-ланцюжок:

```text
search_recent_videos
→ enrich_video_statistics
→ rank_trending_videos
→ analyze_topic_signals
→ structured final report
```

`trend_score` у версії без YouTube API:

```text
0.85 × log-normalized views + 0.15 × freshness
```

### Захисні механізми

- `max_steps = 12`;
- загальний `timeout = 120 секунд` через `time.monotonic()`;
- окремий HTTP timeout;
- зупинка після трьох однакових послідовних tool calls;
- allowlist лише з чотирьох read-only tools;
- ліміт 50 кандидатів і 20 результатів у топі;
- часткова відповідь зі статусом `partial`, якщо спрацював guardrail;
- повний JSON audit trail вузлів графа.

## 4. Налаштування і запуск

### 4.1 Встановлення

```powershell
cd C:\Study\AI_agent_LLM\HW1_Pylypenko_SMM_Parser
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

У поточному workspace можна використовувати спільне середовище:

```powershell
C:\Study\AI_agent_LLM\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4.2 Змінні середовища

Скопіювати `.env.example` у `.env` і підставити власний ключ Gemini:

```dotenv
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_ai_studio_key
GEMINI_MODEL=gemini-2.5-flash
YOUTUBE_DATA_MODE=html
YOUTUBE_HTTP_TIMEOUT=15
```

Секрет не зберігається у notebook, коді, JSON-логах або Git.

Режими даних:

- `html` — актуальні публічні сторінки YouTube без YouTube API;
- `fixture` — локальний стабільний набір для тестів і перевірки без мережі.

### 4.3 Notebook

Відкрити та виконати:

```text
HW1_Pylypenko_YouTube_Trends_Agent.ipynb
```

Notebook уже містить виконані fixture-outputs, дві візуалізації й клікабельні посилання. Після додавання `GOOGLE_API_KEY` та вибору `YOUTUBE_DATA_MODE=html` cells можна повторно виконати для live-режиму.

### 4.4 CLI

Відтворюваний запуск без API-ключів:

```powershell
python run_agent.py "Знайди тренди YouTube про AI agents за останні 7 днів" --mode fixture --llm scripted
```

За замовчуванням CLI одночасно друкує JSON і створює `youtube_trends_report.html`.
HTML-файл використовує той самий renderer, що й Notebook, тому підсумок, картки,
таблиця, рейтинг і посилання в обох інтерфейсах однакові.

Live HTML YouTube без YouTube API та без LLM API (детермінований tool-routing):

```powershell
python run_agent.py "Знайди тренди YouTube про AI agents за останні 7 днів" --mode html --llm scripted
```

Повний запуск із Gemini:

```powershell
python run_agent.py "Знайди тренди YouTube про AI agents за останні 7 днів" --mode html --llm gemini
```

`scripted` призначений для локальної перевірки графа й інструментів. Режими `gemini` та `ollama`
використовують справжню мовну модель для вибору наступної дії.

Лише HTML без великого JSON у консолі:

```powershell
python run_agent.py "Знайди тренди YouTube про AI agents за останні 7 днів" --mode fixture --llm scripted --format html
```

Власне ім'я вихідного файлу задається через `--output report.html`.

### 4.5 Тести

```powershell
python -m pytest -q
python test_runner.py
```

Unit-тести покривають Pydantic-валідацію, HTML helpers, чотири tools, LangGraph і три guardrails.

## 5. Результати тестування

`test_runner.py` генерує п'ять сценаріїв у `test_results.json`:

| Test ID | Сценарій | Очікуваний стан | Фактичний stop reason |
|---|---|---|---|
| TC-001 | Загальні тренди | success | completed |
| TC-002 | Тематичні тренди: AI agents | success | completed |
| TC-003 | Малий max_steps | partial | max_steps |
| TC-004 | Малий timeout | partial | timeout |
| TC-005 | Повторюваний tool call | partial | loop_detected |

Фактичні `steps`, `tool_calls`, `elapsed_ms`, provider та data mode збережені у JSON, а повні вузлові траєкторії — у `trajectory.json`.

## 6. Аналіз результатів

### Чи правильно агент обирав tools?

У двох штатних сценаріях зафіксовано правильну послідовність чотирьох інструментів. `dataset_id` не вигадується моделлю: кожен наступний tool отримує ідентифікатор з Observation попереднього кроку. Ранжування запускається лише після збагачення статистики.

### Де можливі помилки?

Основний ризик — нестабільність публічного HTML YouTube. Платформа може змінити `ytInitialData`, локалізацію чисел і дат, показати consent-сторінку або CAPTCHA. У такому випадку клієнт повертає контрольовану помилку, а не вигадує метрики. Fixture-режим усуває зовнішню нестабільність під час оцінювання.

### Simple vs complex

Повний загальний і тематичний звіти проходять однаковий ReAct-ланцюжок. Тематичний запит додатково звужує кандидатів і зазвичай повертає менший набір. Просте тестування окремих tools показано в notebook до інтеграції у граф.

### Max steps, timeout і loop detection

У штатних запусках ліміти не досягаються. TC-003–TC-005 навмисно змінюють конфігурацію або поведінку test double, щоб доказово продемонструвати кожен механізм. Примусова зупинка не позначається як успіх: повертається `partial` і точний `stop_reason`.

### Залежність часу від складності

У fixture-режимі більшість часу займає проходження графа, а не дані. У live HTML-режимі latency залежить від відповіді YouTube і кількості сторінок. Проєкт обмежує один HTTP-запит на пошук і не відкриває кожне відео окремо.

### Коли tool міг не викликатися?

Системний prompt та Agent Spec задають чітку політику. Якщо модель завершить відповідь раніше, formatter поверне `partial`, оскільки рейтинг відсутній. Це видно у trajectory й не маскується fallback-галюцинацією.

## 7. Відомі обмеження та розвиток

- HTML parsing менш стабільний, ніж офіційний YouTube Data API.
- У публічній видачі немає надійного like count, тому лайки не використовуються.
- Загальні тренди залежать від доступності `/feed/trending` для регіону.
- Якщо `/feed/trending` і неперсоналізована головна порожні, загальний режим використовує broad-category fallback: music, news, sports і technology; це апроксимація, а не офіційний глобальний чарт YouTube.
- Search page повертає обмежену кількість кандидатів без pagination.
- Fixture-дані синтетичні й призначені лише для відтворюваних тестів.

Наступні версії можуть додати YouTube API adapter, пагінацію, планувальник, збереження історичних зрізів і adapters для Telegram, Instagram Reels чи TikTok. Поточний модуль уже придатний як основа майбутнього CIPKO SMM Intelligence.

## 8. Структура файлів

```text
HW1_Pylypenko_SMM_Parser/
├── HW1_Pylypenko_YouTube_Trends_Agent.ipynb
├── youtube_trends_agent/
│   ├── agent.py            # StateGraph, ToolNode, router, formatter
│   ├── models.py           # Pydantic inputs і TrendReport
│   ├── tools.py            # чотири tools
│   ├── youtube_client.py   # HTML parser і fixture client
│   ├── safety.py           # max_steps, timeout, LoopDetector
│   ├── logger.py           # TrajectoryLogger
│   ├── store.py            # проміжні datasets
│   ├── spec.py             # Agent Spec
│   ├── llm_factory.py      # Gemini / Ollama
│   └── testing.py          # test doubles
├── fixtures/
│   └── youtube_videos.json
├── tests/
├── run_agent.py
├── test_runner.py
├── trajectory.json
├── test_results.json
├── requirements.txt
└── .env.example
```
