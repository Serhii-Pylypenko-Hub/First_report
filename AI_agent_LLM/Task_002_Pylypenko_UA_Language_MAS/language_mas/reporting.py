"""Людинозрозуміле TXT-представлення канонічного JSON-результату."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile


CATEGORY_UA = {
    "grammar": "Граматика",
    "orthography": "Орфографія",
    "punctuation": "Пунктуація",
    "calque": "Калька",
    "official_style": "Офіційний стиль",
    "clarity": "Ясність і лаконічність",
    "terminology": "Термінологія",
    "structure": "Структура",
    "content_flag": "Змістове зауваження",
    "security": "Безпека",
}


def render_text_report(result: dict) -> str:
    lines = [
        "ЗВІТ ПРО ЛІНГВІСТИЧНУ ПЕРЕВІРКУ",
        f"Запит: {result.get('request_id', '—')}",
        f"Документ: {result.get('document_id', '—')}",
        f"Статус: {result.get('status', '—')}",
        "",
    ]
    sections = (
        ("ОДНОЗНАЧНІ ПРОПОЗИЦІЇ", result.get("certain_findings", [])),
        ("ПОТРЕБУЮТЬ РІШЕННЯ ЛЮДИНИ", result.get("needs_review", [])),
    )
    for title, findings in sections:
        lines.append(title)
        if not findings:
            lines.append("Пропозицій немає.")
        for index, item in enumerate(findings, 1):
            lines.extend([
                f"{index}. Місце: {item.get('section_ref') or '—'} / {item['node_id']}",
                f"   Категорія: {CATEGORY_UA.get(item['category'], item['category'])}",
                f"   Було: {item['original_text']}",
                f"   Пропозиція: {item.get('suggested_fix') or 'Автоматична заміна не пропонується'}",
                f"   Причина: {item['reason']}",
                f"   Впевненість: {item['confidence']:.0%}",
            ])
            if item.get("evidence"):
                source = item["evidence"][0]
                lines.append(f"   Джерело: {source['title']} — {source['source_url']}")
        lines.append("")
    lines.extend([
        "ВАЖЛИВО",
        "Оригінальний документ не змінено. Заміни виконуються тільки в копії після approve/edit.",
        "Сумнівні й змістові зауваження потребують рішення людини.",
    ])
    return "\n".join(lines)


def save_text_report(result: dict, path: str | Path) -> Path:
    target = Path(path).resolve()
    output_root = (Path(__file__).resolve().parents[1] / "outputs").resolve()
    if output_root not in target.parents:
        raise ValueError("Звіт дозволено зберігати лише у каталозі outputs")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_text_report(result), encoding="utf-8")
    return target


def render_corrected_document(result: dict) -> str:
    """Повертає лише нову погоджену текстову копію; оригінал не змінюється."""

    if result.get("status") != "completed" or not result.get("corrected_document"):
        raise ValueError("Новий документ можна сформувати лише після завершеного HITL")
    nodes = result["corrected_document"].get("nodes", [])
    return "\n\n".join(str(node["text"]) for node in nodes)


def save_corrected_document(result: dict, path: str | Path) -> Path:
    """Ідемпотентно та атомарно записує погоджену копію лише до outputs/."""

    target = Path(path).resolve()
    output_root = (Path(__file__).resolve().parents[1] / "outputs").resolve()
    if output_root not in target.parents or target.suffix.lower() != ".txt":
        raise ValueError("Виправлену копію дозволено зберігати лише як TXT у каталозі outputs")
    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_corrected_document(result)
    with NamedTemporaryFile("w", encoding="utf-8", dir=target.parent, delete=False, suffix=".tmp") as stream:
        stream.write(content)
        temporary = Path(stream.name)
    temporary.replace(target)
    return target
