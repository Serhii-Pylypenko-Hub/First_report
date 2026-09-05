"""Перевірка notebook і людинозрозумілого звіту."""

from pathlib import Path

import nbformat

from language_mas.reporting import render_text_report


ROOT = Path(__file__).resolve().parents[1]


def test_notebook_contains_executed_logical_blocks():
    notebook = nbformat.read(ROOT / "Task_002_Пилипенко_Мовна_MAS.ipynb", as_version=4)
    source = "\n".join(cell.source for cell in notebook.cells)
    assert "Human-in-the-Loop" in source
    assert "CrewAI" in source
    assert "FastMCP" in source
    assert "Pytest" in source
    assert "Візуалізований intake: TXT, DOCX, PDF і зображення" in source
    assert "Результати кожного агента" in source
    assert "Фінальний виправлений текст" in source
    assert "Порівняння оригіналу та погодженої копії" in source
    assert "example.png" in source
    assert all(cell.get("execution_count") is not None for cell in notebook.cells if cell.cell_type == "code")


def test_text_report_has_two_review_sections():
    report = render_text_report({"request_id": "r", "document_id": "d", "status": "completed"})
    assert "ОДНОЗНАЧНІ ПРОПОЗИЦІЇ" in report
    assert "ПОТРЕБУЮТЬ РІШЕННЯ ЛЮДИНИ" in report
