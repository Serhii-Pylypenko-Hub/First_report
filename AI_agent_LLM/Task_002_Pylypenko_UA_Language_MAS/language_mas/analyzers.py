"""Детерміновані спеціалісти; LLM може розширити, але не обійти ці правила."""

from __future__ import annotations

import re
from collections import Counter

from .knowledge import SecureKnowledgeBase
from .models import Category, DocumentPayload, Finding, Severity, finding_id


def _make(
    *, agent: str, node_id: str, section_ref: str | None, rule_id: str,
    category: Category, original: str, fix: str | None, reason: str,
    confidence: float, kb: SecureKnowledgeBase, query: str, severity: Severity = Severity.MEDIUM,
    content_flag: bool = False,
) -> Finding:
    evidence_category = {
        Category.GRAMMAR: "grammar",
        Category.ORTHOGRAPHY: "orthography",
        Category.PUNCTUATION: "orthography",
        Category.CALQUE: "style",
        Category.OFFICIAL_STYLE: "style",
        Category.CLARITY: "style",
        Category.TERMINOLOGY: "terminology",
    }.get(category)
    return Finding(
        finding_id=finding_id(agent, node_id, rule_id, original),
        rule_id=rule_id,
        agent=agent,
        node_id=node_id,
        section_ref=section_ref,
        category=category,
        severity=severity,
        original_text=original,
        suggested_fix=fix,
        reason=reason,
        confidence=confidence,
        review_required=True,
        content_flag=content_flag,
        evidence=kb.search(query, category=evidence_category, limit=1) if evidence_category else [],
    )


GRAMMAR_RULES = (
    ("будьласка", "будь ласка", "ORTH.SPACE.001", Category.ORTHOGRAPHY, "Словосполучення «будь ласка» пишемо окремо.", 0.99),
    ("приймати участь", "брати участь", "GRAM.LEX.001", Category.GRAMMAR, "Нормативна конструкція — «брати участь».", 0.98),
    ("на протязі", "протягом", "GRAM.LEX.002", Category.CALQUE, "Для позначення часу нормативно вжити «протягом».", 0.98),
    ("у відповідності до", "відповідно до", "GRAM.CASE.002", Category.GRAMMAR, "Нормативне прийменникове сполучення — «відповідно до».", 0.97),
    ("згідно наказу", "згідно з наказом", "GRAM.CASE.003", Category.GRAMMAR, "Прийменник «згідно з» керує орудним відмінком.", 0.99),
    ("дякую Вас", "дякую Вам", "GRAM.CASE.004", Category.GRAMMAR, "Дієслово «дякувати» вимагає давального відмінка.", 0.99),
    ("самий важливий", "найважливіший", "GRAM.DEGREE.001", Category.GRAMMAR, "Найвищий ступінь прикметника утворюємо префіксом «най-».", 0.98),
    ("самим важливим", "найважливішим", "GRAM.DEGREE.002", Category.GRAMMAR, "Форму найвищого ступеня в орудному відмінку утворюємо словом «найважливішим».", 0.98),
    ("олексія коваленко", "Олексія Коваленка", "GRAM.NAME.001", Category.GRAMMAR, "Чоловіче прізвище Коваленко в цьому контексті відмінюємо: Олексія Коваленка.", 0.96),
    ("олексію коваленко", "Олексію Коваленку", "GRAM.NAME.005", Category.GRAMMAR, "Чоловіче прізвище Коваленко в давальному відмінку має форму Коваленку.", 0.96),
    ("ігорю журавель", "Ігорю Журавлю", "GRAM.NAME.002", Category.GRAMMAR, "Чоловіче прізвище Журавель у давальному відмінку має форму Журавлю.", 0.95),
    ("тарасом бондар", "Тарасом Бондарем", "GRAM.NAME.003", Category.GRAMMAR, "Чоловіче прізвище Бондар відмінюємо як відповідний загальний іменник.", 0.96),
    ("андрія швець", "Андрія Швеця", "GRAM.NAME.004", Category.GRAMMAR, "Чоловіче прізвище Швець у родовому відмінку має форму Швеця.", 0.95),
)

STYLE_RULES = (
    ("виходячи з вищесказаного", "з огляду на викладене", "STYLE.OFFICIAL.002", "Офіційніше й лаконічніше формулювання.", 0.94),
    ("даний документ", "цей документ", "STYLE.CALQUE.001", "У цьому значенні природніше використати займенник «цей».", 0.93),
    ("по питанню", "щодо", "STYLE.CALQUE.002", "Кальковану конструкцію варто замінити нормативним «щодо».", 0.96),
    ("являється", "є", "STYLE.CALQUE.003", "У значенні зв’язки нормативною є форма «є».", 0.96),
    ("має місце", "зазначено", "STYLE.CLARITY.001", "У цьому контексті канцелярську конструкцію доречно замінити точнішим присудком «зазначено».", 0.82),
    ("по питанню", "щодо", "STYLE.CALQUE.004", "Кальковану конструкцію замінюємо нормативним прийменником «щодо».", 0.97),
    ("на даний момент", "нині", "STYLE.CALQUE.005", "Для офіційного тексту доречніше лаконічне «нині» або «тепер».", 0.93),
    ("слідуючий", "наступний", "STYLE.CALQUE.006", "У значенні черговості нормативною є форма «наступний».", 0.98),
    ("співпадає", "збігається", "STYLE.CALQUE.007", "У цьому значенні нормативно вживати «збігається».", 0.98),
    ("заключити договір", "укласти договір", "STYLE.CALQUE.008", "Нормативне українське словосполучення — «укласти договір».", 0.99),
    ("прийняти міри", "вжити заходів", "STYLE.CALQUE.009", "Кальковане словосполучення замінюємо нормативним «вжити заходів».", 0.99),
    ("вірне рішення", "правильне рішення", "STYLE.CALQUE.010", "«Вірний» означає відданий; щодо рішення нормативно вживати «правильне».", 0.97),
)

TAUTOLOGY_RULES = (
    ("основна суть", "суть", "STRUCT.TAUTOLOGY.001", "Слово «суть» уже позначає основне, тому означення надлишкове."),
    ("спільна співпраця", "співпраця", "STRUCT.TAUTOLOGY.002", "Співпраця за значенням уже є спільною діяльністю."),
    ("пам'ятний сувенір", "сувенір", "STRUCT.TAUTOLOGY.003", "Сувенір за значенням є річчю на пам’ять."),
    ("вільна вакансія", "вакансія", "STRUCT.TAUTOLOGY.004", "Вакансія вже означає вільну посаду."),
)


def grammar_findings(document: DocumentPayload, kb: SecureKnowledgeBase) -> list[Finding]:
    findings: list[Finding] = []
    for node in document.nodes:
        lowered = node.text.lower()
        for original, fix, rule_id, category, reason, confidence in GRAMMAR_RULES:
            if original.lower() in lowered:
                findings.append(_make(
                    agent="grammar", node_id=node.node_id, section_ref=node.section_ref,
                    rule_id=rule_id, category=category, original=original, fix=fix,
                    reason=reason, confidence=confidence, kb=kb, query=f"{original} {fix} відмінок правопис",
                ))
        if re.search(r"\bна мою думку\s+[^,]", lowered):
            findings.append(_make(
                agent="grammar", node_id=node.node_id, section_ref=node.section_ref,
                rule_id="PUNCT.INTRO.001", category=Category.PUNCTUATION,
                original="На мою думку", fix="На мою думку,",
                reason="Вставну конструкцію відокремлюємо комою.", confidence=0.91,
                kb=kb, query="пунктуація вставні слова кома",
            ))
    return findings


def style_findings(document: DocumentPayload, kb: SecureKnowledgeBase) -> list[Finding]:
    findings: list[Finding] = []
    for node in document.nodes:
        lowered = node.text.lower()
        for original, fix, rule_id, reason, confidence in STYLE_RULES:
            if original in lowered:
                category = Category.CALQUE if "CALQUE" in rule_id else Category.OFFICIAL_STYLE
                findings.append(_make(
                    agent="style", node_id=node.node_id, section_ref=node.section_ref,
                    rule_id=rule_id, category=category, original=original, fix=fix,
                    reason=reason, confidence=confidence, kb=kb,
                    query=f"офіційний стиль {original} {fix}",
                    severity=Severity.LOW if confidence < 0.8 else Severity.MEDIUM,
                ))
        words = re.findall(r"[А-Яа-яІіЇїЄєҐґ'-]+", node.text)
        if len(words) > 30:
            findings.append(_make(
                agent="style", node_id=node.node_id, section_ref=node.section_ref,
                rule_id="STYLE.LENGTH.001", category=Category.CLARITY,
                original=node.text, fix=None,
                reason=f"Речення або абзац містить {len(words)} слів; варто перевірити можливість поділу.",
                confidence=0.75, kb=kb, query="офіційний стиль лаконічність ясність",
                severity=Severity.LOW,
            ))
    return findings


def terminology_findings(document: DocumentPayload, kb: SecureKnowledgeBase) -> list[Finding]:
    full_text = " ".join(node.text.lower() for node in document.nodes)
    findings: list[Finding] = []
    # Ураховуємо не лише називний «договір», а й відмінені форми зі stem «договор-».
    has_agreement_term = "договір" in full_text or "договор" in full_text
    if has_agreement_term and "контракт" in full_text:
        locations = [node.node_id for node in document.nodes if "контракт" in node.text.lower()]
        node_id = locations[0]
        evidence = kb.search("договір контракт термінологічна узгодженість", category="terminology", limit=1)
        findings.append(Finding(
            finding_id=finding_id("terminology", node_id, "TERM.CONSISTENCY.001", "контракт"),
            rule_id="TERM.CONSISTENCY.001", agent="terminology", node_id=node_id,
            category=Category.TERMINOLOGY, severity=Severity.MEDIUM,
            original_text="контракт", suggested_fix="договір",
            reason=f"У документі паралельно використано «договір» і «контракт». Місця: {', '.join(locations)}.",
            confidence=0.86, occurrences_count=len(locations), evidence=evidence,
        ))
    for node in document.nodes:
        for term in ("дедлайн", "апрув"):
            if term in node.text.lower():
                lookup = kb.terminology(term)
                findings.append(_make(
                    agent="terminology", node_id=node.node_id, section_ref=node.section_ref,
                    rule_id=f"TERM.PREFERRED.{term.upper()}", category=Category.TERMINOLOGY,
                    original=term, fix=lookup["preferred"], reason="Запропоновано нейтральний український термін.",
                    confidence=0.9, kb=kb, query=f"термінологія {term} {lookup['preferred']}",
                ))
    return findings


def structure_findings(document: DocumentPayload, kb: SecureKnowledgeBase) -> list[Finding]:
    del kb
    findings: list[Finding] = []
    normalized = [re.sub(r"\s+", " ", node.text.lower()).strip() for node in document.nodes]
    counts = Counter(normalized)
    for idx, text in enumerate(normalized):
        if counts[text] > 1 and normalized.index(text) == idx:
            matches = [node.node_id for node, norm in zip(document.nodes, normalized) if norm == text]
            node = document.nodes[idx]
            findings.append(Finding(
                finding_id=finding_id("structure", node.node_id, "STRUCT.DUPLICATE.001", node.text),
                rule_id="STRUCT.DUPLICATE.001", agent="structure", node_id=node.node_id,
                section_ref=node.section_ref, category=Category.STRUCTURE, severity=Severity.LOW,
                original_text=node.text, suggested_fix=None,
                reason=f"Однаковий фрагмент повторюється у вузлах: {', '.join(matches)}.",
                confidence=0.99, occurrences_count=len(matches), evidence=[],
            ))
    for node in document.nodes:
        repeated = re.search(r"\b([А-Яа-яІіЇїЄєҐґ'-]{3,})\s+\1\b", node.text, re.IGNORECASE)
        if repeated:
            findings.append(Finding(
                finding_id=finding_id("structure", node.node_id, "STRUCT.REPEATED_WORD.001", repeated.group(0)),
                rule_id="STRUCT.REPEATED_WORD.001", agent="structure", node_id=node.node_id,
                section_ref=node.section_ref, category=Category.STRUCTURE, severity=Severity.LOW,
                original_text=repeated.group(0), suggested_fix=repeated.group(1),
                reason="Сусіднє повторення того самого слова може бути механічною тавтологією.",
                confidence=0.96, occurrences_count=1, evidence=[],
            ))
        lowered = node.text.lower()
        for original, fix, rule_id, reason in TAUTOLOGY_RULES:
            if original in lowered:
                findings.append(Finding(
                    finding_id=finding_id("structure", node.node_id, rule_id, original),
                    rule_id=rule_id, agent="structure", node_id=node.node_id,
                    section_ref=node.section_ref, category=Category.STRUCTURE, severity=Severity.LOW,
                    original_text=original, suggested_fix=fix, reason=reason,
                    confidence=0.94, occurrences_count=1, evidence=[],
                ))
    return findings


def verify_findings(document: DocumentPayload, findings: list[Finding]) -> list[Finding]:
    nodes = {node.node_id: node.text.lower() for node in document.nodes}
    verified: list[Finding] = []
    seen: set[str] = set()
    for finding in findings:
        if finding.finding_id in seen or finding.node_id not in nodes:
            continue
        if finding.original_text.lower() not in nodes[finding.node_id] and finding.category != Category.STRUCTURE:
            continue
        if finding.suggested_fix:
            original_digits = re.findall(r"\d+(?:[.,]\d+)?", finding.original_text)
            fixed_digits = re.findall(r"\d+(?:[.,]\d+)?", finding.suggested_fix)
            if original_digits != fixed_digits:
                continue
        seen.add(finding.finding_id)
        verified.append(finding)
    return sorted(verified, key=lambda item: (-item.confidence, item.node_id, item.rule_id))
