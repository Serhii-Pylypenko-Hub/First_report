"""Захищене перетворення TXT, DOCX, PDF та зображень у спільний JSON-контракт."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path
from time import perf_counter
from typing import Callable

from PIL import Image

from .audit import JsonlTracer
from .models import AnalysisRequest
from .security import SecurityError, ToolGuardrail


ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_ROOT = (ROOT / "fixtures" / "documents").resolve()
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_EXTRACTED_CHARS = 60_000
MAX_DOCX_ENTRIES = 500
MAX_DOCX_UNCOMPRESSED_SIZE = 20 * 1024 * 1024
MAX_PDF_PAGES = 50
MAX_IMAGE_PIXELS = 25_000_000
SUPPORTED_SUFFIXES = {".txt", ".docx", ".pdf", ".png", ".jpg", ".jpeg"}


def _resolve_scoped_path(file_name: str) -> Path:
    """Не дозволяє читати довільні файли поза серверним intake-каталогом."""

    if Path(file_name).is_absolute():
        raise SecurityError("Абсолютні шляхи заборонені")
    target = (DOCUMENT_ROOT / file_name).resolve()
    if target != DOCUMENT_ROOT and DOCUMENT_ROOT not in target.parents:
        raise SecurityError("Файл знаходиться поза дозволеним intake-каталогом")
    if not target.is_file():
        raise FileNotFoundError(f"Файл не знайдено: {file_name}")
    if target.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise SecurityError("Непідтримуваний тип файла")
    if target.stat().st_size > MAX_FILE_SIZE:
        raise SecurityError("Файл перевищує ліміт 5 MiB")
    return target


ExtractedChunk = tuple[str, str]


def _txt(path: Path) -> tuple[list[ExtractedChunk], str, list[str]]:
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise SecurityError("TXT містить бінарні дані")
    text = raw.decode("utf-8-sig")
    chunks = [
        (part.strip(), f"Рядок {line_number}")
        for line_number, part in enumerate(text.splitlines(), start=1)
        if part.strip()
    ]
    return chunks, "utf8_text", []


def _docx(path: Path) -> tuple[list[ExtractedChunk], str, list[str]]:
    if path.read_bytes()[:2] != b"PK":
        raise SecurityError("Некоректна сигнатура DOCX")
    try:
        with zipfile.ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_DOCX_ENTRIES:
                raise SecurityError("DOCX містить забагато архівних елементів")
            if sum(item.file_size for item in entries) > MAX_DOCX_UNCOMPRESSED_SIZE:
                raise SecurityError("Розпакований DOCX перевищує ліміт 20 MiB")
    except zipfile.BadZipFile as exc:
        raise SecurityError("Некоректний ZIP-контейнер DOCX") from exc

    from docx import Document

    document = Document(path)
    chunks = [
        (paragraph.text.strip(), f"Абзац {paragraph_number}")
        for paragraph_number, paragraph in enumerate(document.paragraphs, start=1)
        if paragraph.text.strip()
    ]
    return chunks, "python_docx", []


def _pdf(path: Path) -> tuple[list[ExtractedChunk], str, list[str]]:
    if not path.read_bytes().startswith(b"%PDF"):
        raise SecurityError("Некоректна сигнатура PDF")
    from pypdf import PdfReader

    reader = PdfReader(path)
    if len(reader.pages) > MAX_PDF_PAGES:
        raise SecurityError(f"PDF перевищує ліміт {MAX_PDF_PAGES} сторінок")
    pages = [str(page.extract_text() or "").strip() for page in reader.pages]
    chunks = [
        (line.strip(), f"Сторінка {page_number}, рядок {line_number}")
        for page_number, page in enumerate(pages, start=1)
        for line_number, line in enumerate(page.splitlines(), start=1)
        if line.strip()
    ]
    return chunks, "pypdf_text_layer", []


def _image(path: Path) -> tuple[list[ExtractedChunk], str, list[str]]:
    with Image.open(path) as image:
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise SecurityError("Зображення перевищує безпечний піксельний ліміт")
        image.verify()
    with Image.open(path) as image:
        # Production-шлях: локальний Tesseract. Жодне зображення не передається у зовнішній API.
        if shutil.which("tesseract"):
            import pytesseract

            text = pytesseract.image_to_string(image, lang="ukr").strip()
            chunks = [
                (line.strip(), f"Зображення, OCR-рядок {line_number}")
                for line_number, line in enumerate(text.splitlines(), start=1)
                if line.strip()
            ]
            return chunks, "local_tesseract_ocr", []

        # Офлайн fixture має підписаний текст у PNG metadata лише для відтворюваного навчального тесту.
        fixture_text = image.info.get("language_mas_fixture_text", "").strip()
        if fixture_text and path.parent == DOCUMENT_ROOT:
            chunks = [
                (line.strip(), f"Зображення, рядок {line_number}")
                for line_number, line in enumerate(fixture_text.splitlines(), start=1)
                if line.strip()
            ]
            return chunks, "fixture_metadata_test_double", [
                "Tesseract не встановлено: для fixture використано контрольовану metadata-мітку; production потребує OCR backend."
            ]
    raise RuntimeError("OCR backend недоступний; установіть локальний Tesseract з українською мовною моделлю")


PARSERS: dict[str, Callable[[Path], tuple[list[ExtractedChunk], str, list[str]]]] = {
    ".txt": _txt,
    ".docx": _docx,
    ".pdf": _pdf,
    ".png": _image,
    ".jpg": _image,
    ".jpeg": _image,
}


def parse_document_payload(file_name: str, request_id: str = "document-intake") -> dict:
    """Єдиний tool-контракт status + data/error для всіх підтримуваних форматів."""

    try:
        path = _resolve_scoped_path(file_name)
        chunks, method, warnings = PARSERS[path.suffix.lower()](path)
        if not chunks:
            raise ValueError("У документі не знайдено тексту")
        extracted_chars = sum(len(text) for text, _ in chunks)
        if extracted_chars > MAX_EXTRACTED_CHARS:
            raise SecurityError(f"Витягнутий текст перевищує ліміт {MAX_EXTRACTED_CHARS} символів")
        nodes = [
            {
                "node_id": f"n-{index:03d}",
                "node_type": "paragraph",
                "section_ref": location,
                "text": text,
            }
            for index, (text, location) in enumerate(chunks, start=1)
        ]
        request = AnalysisRequest.model_validate({
            "request_id": request_id,
            "document": {
                "document_id": path.stem,
                "language": "uk",
                "register": "official",
                "nodes": nodes,
            },
        })
        return {
            "status": "ok",
            "data": {
                "request": request.model_dump(mode="json", by_alias=True),
                "source": {
                    "file_name": path.name,
                    "format": path.suffix.lower().lstrip("."),
                    "size_bytes": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "extraction_method": method,
                    "warnings": warnings,
                },
            },
        }
    except Exception as exc:
        return {"status": "error", "error": {"code": type(exc).__name__.upper(), "message": str(exc)}}


class DocumentIntakeAgent:
    """Вузький агент: може лише перетворити дозволений файл у JSON, але не аналізувати чи редагувати його."""

    def __init__(self, trace_path: Path | None = None) -> None:
        self.guardrail = ToolGuardrail(max_calls=10)
        self.tracer = JsonlTracer(trace_path)

    def parse(self, file_name: str, *, request_id: str) -> dict:
        started = perf_counter()
        try:
            self.guardrail.authorize("document_intake", "parse_document", {"file_name": file_name})
            result = parse_document_payload(file_name, request_id)
            source = result.get("data", {}).get("source", {})
            self.tracer.emit(
                "document_intake_completed",
                request_id=request_id,
                status=result.get("status"),
                format=source.get("format"),
                source_sha256=source.get("sha256"),
                size_bytes=source.get("size_bytes"),
                node_count=len(result.get("data", {}).get("request", {}).get("document", {}).get("nodes", [])),
                error_code=(result.get("error") or {}).get("code"),
                elapsed_ms=round((perf_counter() - started) * 1000, 2),
            )
            return result
        except Exception as exc:
            self.tracer.emit(
                "document_intake_blocked", request_id=request_id, status="blocked",
                error_code=type(exc).__name__.upper(),
                elapsed_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise
