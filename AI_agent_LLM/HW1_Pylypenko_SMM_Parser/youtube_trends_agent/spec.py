"""Версіонований Agent Spec для YouTube Trends Agent."""

AGENT_SPEC = {
    "name": "youtube_trends_react_agent",
    "version": "1.0.0",
    "spec_revision": "2026-08-29",
    "goal": (
        "Знайти загальні або тематичні YouTube-тренди за визначений період, "
        "перевірити публічні перегляди та повернути топ відео з доказовими посиланнями."
    ),
    "tools": [
        "search_recent_videos",
        "enrich_video_statistics",
        "rank_trending_videos",
        "analyze_topic_signals",
    ],
    "policies": [
        "Спочатку виконати пошук, потім збагачення статистикою, потім ранжування.",
        "Використовувати лише dataset_id, повернений попереднім інструментом.",
        "Не вигадувати перегляди, лайки, назви, канали або URL.",
        "Для загального аналізу використовувати порожню topic; для тематичного — запит користувача.",
    ],
    "constraints": {
        "read_only": True,
        "max_top_n": 20,
        "max_candidates": 50,
        "max_period_days": 30,
        "comments_collected": False,
        "private_data": False,
    },
    "non_goals": [
        "Не завантажувати відео або коментарі.",
        "Не ставити лайки, не публікувати контент і не змінювати YouTube.",
        "Не обходити квоти, авторизацію або правила платформи.",
        "Не підтримувати інші соціальні мережі у версії 1.0.",
    ],
    "completion": [
        "Є збагачений набір відео і хоча б один рейтинг.",
        "Або спрацював max_steps, timeout, loop detector чи сталася контрольована помилка.",
    ],
    "output": "TrendReport JSON: rankings by views and trend score, links, signals, confidence, limitations, stop_reason.",
}
