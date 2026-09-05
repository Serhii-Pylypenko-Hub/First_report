"""Простий ipywidgets-інтерфейс вибору TOP-реклами та фінальних постів."""

from __future__ import annotations

from typing import Any

import ipywidgets as widgets
from IPython.display import HTML, clear_output, display

from mas_langgraph import CompetitiveSMMMAS


class ContentReviewWidget:
    def __init__(self, mas: CompetitiveSMMMAS, thread_id: str, state: dict[str, Any]) -> None:
        self.mas = mas
        self.thread_id = thread_id
        values = state["values"]
        self.output = widgets.Output()
        self.top_checks = {
            row["post_id"]: widgets.Checkbox(value=True, description=f'{row["brand"]}: {row["topic"]} ({row["post_id"]})', indent=False)
            for row in values["analysis"]["ad_rankings"]["top_by_normalized_score"]
        }
        self.draft_checks = {}
        self.draft_editors = {}
        for draft in values["drafts"]:
            draft_id = draft["draft_id"]
            self.draft_checks[draft_id] = widgets.Checkbox(value=True, description=f'{draft_id}: {draft["topic"]}', indent=False)
            self.draft_editors[draft_id] = widgets.Textarea(
                value=draft["text"], layout=widgets.Layout(width="100%", height="105px"),
                description="Текст:", style={"description_width": "55px"},
            )
        self.widget = self._build(values)

    @staticmethod
    def _toggle(items: dict[str, widgets.Checkbox], value: bool) -> None:
        for item in items.values():
            item.value = value

    def _build(self, values: dict[str, Any]):
        warning_rows = values.get("forbidden_warnings", [])
        warning = (
            '<div style="padding:12px;border:2px solid #c53030;background:#fff5f5"><b>Увага:</b> '
            f'виявлено заборонених тем: {len(warning_rows)}. Такі чернетки не можна підтвердити автоматично.</div>'
            if warning_rows else
            '<div style="padding:12px;border:1px solid #38a169;background:#f0fff4"><b>Brand safety:</b> заборонених тем не виявлено.</div>'
        )
        top_all = widgets.Button(description="Вибрати всю TOP-рекламу", button_style="info")
        top_none = widgets.Button(description="Зняти всю TOP-рекламу")
        draft_all = widgets.Button(description="Вибрати всі пости", button_style="info")
        draft_none = widgets.Button(description="Зняти всі пости")
        confirm = widgets.Button(description="Підтвердити вибране", button_style="success", icon="check")
        top_all.on_click(lambda _: self._toggle(self.top_checks, True))
        top_none.on_click(lambda _: self._toggle(self.top_checks, False))
        draft_all.on_click(lambda _: self._toggle(self.draft_checks, True))
        draft_none.on_click(lambda _: self._toggle(self.draft_checks, False))
        confirm.on_click(self._confirm)
        draft_boxes = []
        for draft_id in self.draft_checks:
            draft_boxes.append(widgets.VBox([self.draft_checks[draft_id], self.draft_editors[draft_id]]))
        return widgets.VBox([
            widgets.HTML("<h3>Людське погодження контенту</h3>" + warning),
            widgets.HTML("<h4>1. TOP-реклама для використання як доказ патернів</h4>"),
            widgets.HBox([top_all, top_none]), *self.top_checks.values(),
            widgets.HTML("<h4>2. Нові рекламні пости ROZETKA</h4><p>Зніміть зайві, відредагуйте текст і підтвердьте. Непозначені елементи буде відсічено.</p>"),
            widgets.HBox([draft_all, draft_none]), *draft_boxes, confirm, self.output,
        ])

    def _confirm(self, _button) -> None:
        payload = {
            "decision": "approve",
            "selected_top_ids": [key for key, item in self.top_checks.items() if item.value],
            "selected_draft_ids": [key for key, item in self.draft_checks.items() if item.value],
            "edited_drafts": {key: editor.value for key, editor in self.draft_editors.items()},
        }
        with self.output:
            clear_output()
            try:
                state = self.mas.resume_selection(self.thread_id, payload)
                display(HTML(
                    '<div style="padding:12px;background:#ebf8ff;border:1px solid #3182ce">'
                    f'Погоджено постів: <b>{len(state["values"].get("approved_drafts", []))}</b>. '
                    'Workflow зупинено перед файловим експортом. Для експорту потрібне окреме підтвердження.'
                    '</div>'
                ))
            except Exception as exc:
                display(HTML(f'<div style="color:#c53030">Помилка: {exc}</div>'))


def display_review_widget(mas: CompetitiveSMMMAS, thread_id: str, state: dict[str, Any]) -> ContentReviewWidget:
    component = ContentReviewWidget(mas, thread_id, state)
    display(component.widget)
    return component
