# Spotify Tracks MongoDB Analytics

Проєкт виконує домашнє завдання з MongoDB Atlas на датасеті Spotify Tracks: завантажує CSV у `tracks_raw`, трансформує документи у колекцію `tracks`, запускає запити, aggregation pipelines, індекси та `explain()`.

## Покроковий Запуск У VS Code

1. Відкрийте папку проєкту у VS Code:

```text
C:\Study\NOSKL\nosql_1
```

2. Створіть файл `.env` у корені проєкту за прикладом `.env.example`:

```env
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB=spotify
CSV_PATH=dataset.csv
```

У `MONGO_URI` має бути реальний рядок підключення з MongoDB Atlas. Файл `.env` не комітиться в Git, бо містить приватні дані.

3. Покладіть `dataset.csv` у корінь проєкту:

```text
C:\Study\NOSKL\nosql_1\dataset.csv
```

4. Відкрийте термінал у VS Code: `Terminal -> New Terminal`.

5. Перейдіть у папку проєкту:

```powershell
cd C:\Study\NOSKL\nosql_1
```

6. Запустіть повну Python-версію завдання:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_python.ps1
```

Цей скрипт:

- встановлює Python-залежності з `requirements.txt`;
- завантажує CSV у MongoDB Atlas у колекцію `tracks_raw`;
- трансформує дані в колекцію `tracks`;
- виконує запити з частини 2;
- виконує aggregation pipelines з частини 3;
- створює індекси і збирає `explain()` для частини 4;
- зберігає результати у `outputs/results.json`.

Успішний запуск завершується повідомленням:

```text
Report saved to: C:\Study\NOSKL\nosql_1\outputs\results.json
Done.
```

## Як Подивитися Результати

Після запуску відкрийте файл:

```text
outputs/results.json
```

У ньому є основні блоки:

```json
{
  "load": "...",
  "transform": "...",
  "part2_queries": "...",
  "part3_aggregations": "...",
  "part4_indexes": "..."
}
```

Щоб відкрити файл із термінала VS Code:

```powershell
code outputs\results.json
```

## Перевірка JS/mongosh Скриптів

Python-скрипт достатній для повної перевірки логіки. Якщо потрібно окремо перевірити JS-файли через MongoDB Shell, після успішного Python-запуску виконайте:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_all.ps1 -SkipLoad
```

Прапорець `-SkipLoad` потрібен, щоб не завантажувати CSV повторно. Скрипт перевірить:

- `scripts/02_transform.js`;
- `queries/part2_queries.js`;
- `queries/part3_aggregations.js`;
- `queries/part4_indexes.js`.

## Що Комітити В Git

У Git потрібно додати код і документацію:

```text
README.md
requirements.txt
run_python.ps1
run_all.ps1
.env.example
.gitignore
scripts/
queries/
outputs/results.json
```

Не потрібно комітити:

```text
.env
dataset.csv
venv311/
__pycache__/
*.pyc
*.zip
```

Ці файли вже додані в `.gitignore`, бо `.env` містить приватний MongoDB URI, `dataset.csv` великий, а `venv311/` є локальним середовищем.

Приклад команд для Git:

```powershell
cd C:\Study
git add NOSKL\nosql_1
git commit -m "Add MongoDB Atlas Spotify analytics homework"
```

Після цього репозиторій можна опублікувати на GitHub і додати посилання в LMS.

## Формат Здачі

За умовою завдання потрібно здати:

- zip-архів із назвою `[Ваше_прізвище]_nosql_1`;
- посилання на GitHub-репозиторій із кодом, скриптами та README.

README вже містить:

- інструкцію запуску проєкту;
- опис структури даних;
- відповіді на теоретичні питання;
- результати та пояснення для індексів;
- фактичні значення `explain()` для частини 4.

## Швидкий Запуск

```powershell
cd C:\Study\NOSKL\nosql_1
powershell -ExecutionPolicy Bypass -File .\run_python.ps1
```

Результати Python-запуску зберігаються у `outputs/results.json`.

Якщо запускаєте окремі JS-файли через `mongosh`:

```powershell
.\run_all.ps1
```

Перед запуском потрібно створити `.env`:

```env
MONGO_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGO_DB=spotify
CSV_PATH=dataset.csv
```

Файл `dataset.csv` має лежати в корені проєкту або шлях до нього треба вказати у `CSV_PATH`.

## Структура

- `scripts/01_load_data.py` - завантаження CSV у `tracks_raw`.
- `scripts/02_transform.js` - трансформація `tracks_raw` у `tracks`.
- `scripts/03_run_all_python.py` - повний запуск без `mongosh`.
- `queries/part2_queries.js` - запити до даних.
- `queries/part3_aggregations.js` - аналітика через aggregation pipeline.
- `queries/part4_indexes.js` - індекси та `explain()`.

## Схема Колекції `tracks`

Після трансформації документ має таку логіку:

```json
{
  "track_id": "...",
  "track_name": "...",
  "album_name": "...",
  "artists": ["Artist 1", "Artist 2"],
  "explicit": false,
  "popularity": 72,
  "popularity_tier": "high",
  "duration_ms": 210000,
  "duration_sec": 210.0,
  "track_genre": "pop",
  "audio_features": {
    "danceability": 0.78,
    "energy": 0.81,
    "loudness": -5.2,
    "speechiness": 0.04,
    "acousticness": 0.12,
    "instrumentalness": 0.0,
    "liveness": 0.1,
    "valence": 0.73,
    "tempo": 122.4,
    "key": 5,
    "mode": 1,
    "time_signature": 4
  }
}
```

## Частина 1. Схема

Аудіо-характеристики винесені в об'єкт `audio_features`, бо вони описують одну групу властивостей треку. Так документ легше читати, а запити на кшталт `"audio_features.energy"` залишаються зрозумілими. Таке вкладення вигідне, коли ці поля часто читаються разом. Воно може заважати, якщо вкладений об'єкт надмірно росте або його частини часто оновлюються незалежно.

`artists` зберігається як масив, бо один трек може мати кількох виконавців. Це спрощує пошук треків конкретного артиста, запити з `$in` або `$all`, а також групування через `$unwind`.

`$out` записує результат aggregation pipeline у нову або наявну колекцію, повністю замінюючи її вміст. Це зручно для повної перебудови `tracks` із `tracks_raw`. `$merge` гнучкіший: він може оновлювати, вставляти або об'єднувати документи з наявною колекцією, тому краще підходить для інкрементальних оновлень.

## Частина 2. Запити

Реалізовано 4 запити:

- треки для вечірки: `danceability > 0.7`, `energy > 0.7`, тривалість 3-5 хвилин;
- виконавці, у яких мінімум 3 треки і всі мають `popularity >= 60`;
- нетипові треки, де `tempo > avg_tempo + 2 * stdDevPop` у межах жанру;
- треки для фонової роботи: тихі, не explicit, з низькою `speechiness` і високою `instrumentalness`.

`$unwind` використовується для перетворення масиву `artists` на окремі рядки pipeline. Завдяки цьому один трек із кількома виконавцями враховується в статистиці кожного виконавця окремо.

`$stdDevPop` рахує стандартне відхилення для всієї популяції даних у групі. `$stdDevSamp` рахує вибіркове відхилення з поправкою, тому зазвичай дає трохи більше значення. Для всіх треків жанру доречний `$stdDevPop`, бо ми аналізуємо всю групу в датасеті.

## Частина 3. Aggregation

Реалізовано:

- топ виконавців за середньою популярністю з фільтром `track_count >= 5`;
- розподіл настроїв за `valence` та `energy`;
- жанри з найвищим середнім танцювальним score;
- додатковий приклад `$lookup` через колекцію `artist_stats`.

Якщо знизити поріг для топ-виконавців із 5 треків до 1, у результат можуть потрапити артисти з одним дуже популярним треком, тому рейтинг стане менш стабільним. Якщо підняти поріг до 50, залишаться лише дуже представлені артисти, рейтинг буде стабільнішим, але менш різноманітним.

Якщо для жанрів знизити поріг зі 100 до 50 треків, у результат потрапить більше нішевих жанрів. Це може змінити лідерів, але середні значення будуть менш надійними через меншу кількість треків.

## Частина 4. Індекси Та Explain

Для запиту:

```js
db.tracks.find({
  track_genre: "pop",
  "audio_features.danceability": { $gte: 0.7 }
}).sort({ popularity: -1 })
```

створено індекс:

```js
db.tracks.createIndex({
  track_genre: 1,
  popularity: -1,
  "audio_features.danceability": 1
})
```

Після створення індексу в плані виконання з'явився `IXSCAN`, а кількість прочитаних документів суттєво зменшилася.

Фактичні значення з `explain()`:

| Перевірка | executionTimeMillis | totalKeysExamined | totalDocsExamined | nReturned |
| --- | ---: | ---: | ---: | ---: |
| До індексу для pop/danceability | 87 | 0 | 113999 | 354 |
| Після індексу для pop/danceability | 2 | 412 | 354 | 354 |

До індексу MongoDB виконував повне сканування колекції (`COLLSCAN`) і перевірив 113999 документів. Після створення compound index план перейшов на `IXSCAN`: MongoDB перевірила 412 ключів індексу і прочитала тільки 354 документи, які відповідають запиту.

Для пошуку музики для роботи створено індекс:

```js
db.tracks.createIndex({
  explicit: 1,
  "audio_features.instrumentalness": 1,
  "audio_features.speechiness": 1
})
```

Для запиту з цим індексом отримано:

| Перевірка | executionTimeMillis | totalKeysExamined | totalDocsExamined | nReturned |
| --- | ---: | ---: | ---: | ---: |
| Work music query з індексом | 38 | 16602 | 16141 | 16141 |

Індекс використовується, бо в winning plan є `IXSCAN` за індексом `idx_work_music`. Поля `explicit`, `audio_features.instrumentalness` і `audio_features.speechiness` входять до індексу, тому MongoDB може швидше знайти кандидатів для цього фільтра.

Початковий запит:

```js
db.tracks.find({
  track_genre: "pop",
  popularity: { $gte: 70 }
})
```

не є covered query, бо без projection MongoDB має прочитати повні документи. Покривний варіант має повертати лише поля з індексу та явно виключати `_id`:

```js
db.tracks.find(
  { track_genre: "pop", popularity: { $gte: 70 } },
  { _id: 0, track_genre: 1, popularity: 1 }
)
```

Підтвердження covered query:

| Перевірка | executionTimeMillis | totalKeysExamined | totalDocsExamined | nReturned |
| --- | ---: | ---: | ---: | ---: |
| Covered query variant | 0 | 317 | 0 | 317 |

Тут `totalDocsExamined: 0`, тобто MongoDB не читала повні документи з колекції. Результат сформовано з індексу, а в плані виконання є `PROJECTION_COVERED`.

## Що Додати Перед Здачею

- Перевірити, що всі скрипти лежать у проєкті: `scripts/`, `queries/`, `README.md`, `requirements.txt`.
- Перевірити, що README містить відповіді на теоретичні питання та фактичні значення `explain()`.
- Створити zip-архів із назвою `[Ваше_прізвище]_nosql_1`.
- Додати посилання на GitHub-репозиторій `[Ваше_прізвище]_nosql_1` в LMS.
- Прикріпити zip-архів у LMS.
