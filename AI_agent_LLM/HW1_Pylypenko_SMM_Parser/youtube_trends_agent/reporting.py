"""Спільне HTML-представлення звіту для Notebook і CLI."""

from __future__ import annotations

from html import escape
from pathlib import Path

from .models import TrendReport


def render_report_html(
    report: TrendReport | dict,
    *,
    title: str = "YouTube Trends Intelligence",
    standalone: bool = False,
) -> str:
    """Побудувати однаковий dashboard для Jupyter і звичайного HTML-файлу."""

    model = report if isinstance(report, TrendReport) else TrendReport.model_validate(report)
    rows = model.top_by_views
    max_views = max((video.views for video in rows[:10]), default=1)

    table_rows = "".join(
        "<tr>"
        f"<td>{video.rank}</td>"
        f'<td><a href="{escape(video.url)}" target="_blank">{escape(video.title)}</a></td>'
        f"<td>{escape(video.channel_title)}</td>"
        f"<td>{video.published_at:%Y-%m-%d}</td>"
        f"<td>{video.views:,}</td>"
        f"<td>{video.trend_score:.4f}</td>"
        "</tr>"
        for video in rows
    )
    bars = "".join(
        '<div class="bar-row">'
        f'<span class="bar-title">{escape(video.title[:58])}</span>'
        f'<span class="bar" style="width:{max(3, video.views / max_views * 100):.1f}%">'
        f"{video.views:,}</span></div>"
        for video in reversed(rows[:10])
    )
    limitations = "".join(f"<li>{escape(item)}</li>" for item in model.limitations)
    topic = escape(model.topic) if model.topic else "загальні тренди"
    body = f"""
<section class="yt-dashboard">
  <h1>{escape(title)}</h1>
  <p class="summary"><strong>Підсумок:</strong> {escape(model.summary)}</p>
  <div class="cards">
    <div class="card navy"><b>{model.videos_analyzed}</b><span>відео</span></div>
    <div class="card teal"><b>{model.period_days}</b><span>днів</span></div>
    <div class="card purple"><b>{model.confidence:.0%}</b><span>confidence</span></div>
    <div class="card amber"><b>{escape(model.source_mode)}</b><span>джерело</span></div>
  </div>
  <h2>Рейтинг за переглядами: {topic}</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>№</th><th>Відео</th><th>Канал</th><th>Дата</th><th>Перегляди</th><th>Trend score</th></tr></thead>
    <tbody>{table_rows}</tbody>
  </table></div>
  <h2>Топ-10 за переглядами</h2>
  <div class="bars">{bars}</div>
  <p><strong>Повторювані теми:</strong> {escape(", ".join(model.trend_terms) or "не визначено")}</p>
  <details><summary>Обмеження аналізу</summary><ul>{limitations}</ul></details>
</section>
"""
    styles = """
<style>
body{margin:0;padding:24px;background:#f4f7fb;color:#172033;font-family:Segoe UI,Arial,sans-serif}
.yt-dashboard{max-width:1180px;margin:auto;background:white;padding:26px;border-radius:18px;box-shadow:0 8px 30px #1e3a5f18}
.summary{background:#eff6ff;border-left:5px solid #2563eb;padding:14px;border-radius:8px}
.cards{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}.card{min-width:120px;padding:15px;color:white;border-radius:12px}
.card b{display:block;font-size:24px}.card span{font-size:13px}.navy{background:#172554}.teal{background:#0f766e}
.purple{background:#7c3aed}.amber{background:#b45309}.table-wrap{overflow-x:auto}
table{width:100%;border-collapse:collapse}th,td{padding:10px;border-bottom:1px solid #e5e7eb;text-align:left}
th{background:#eff6ff}a{color:#1d4ed8;text-decoration:none}a:hover{text-decoration:underline}
.bars{padding:8px 0 18px}.bar-row{display:grid;grid-template-columns:minmax(180px,36%) 1fr;gap:10px;align-items:center;margin:7px 0}
.bar-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar{display:block;background:#2563eb;color:white;padding:5px 8px;border-radius:5px;box-sizing:border-box;min-width:72px}
details{margin-top:16px;color:#475569}
</style>
"""
    fragment = styles + body
    if not standalone:
        return fragment
    return (
        "<!doctype html><html lang=\"uk\"><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{escape(title)}</title></head><body>{fragment}</body></html>"
    )


def write_html_report(
    report: TrendReport | dict,
    output_path: str | Path,
    *,
    title: str = "YouTube Trends Intelligence",
) -> Path:
    """Зберегти автономний HTML-звіт і повернути абсолютний шлях."""

    path = Path(output_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_report_html(report, title=title, standalone=True),
        encoding="utf-8",
    )
    return path
