"""Library audit orchestration and artifact generation."""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from app.config import Settings
from app.ingestion.frontmatter_parser import parse_frontmatter
from app.ingestion.markdown_loader import discover_markdown_files, read_markdown
from app.ingestion.metadata_parser import extract_book_metadata
from app.schemas.book import BookMetadata, ParseFailure

LOGGER = logging.getLogger(__name__)
QUOTE_RE = re.compile(r"(^|\n)\s*(>|[\"“])", re.MULTILINE)
MEMO_RE = re.compile(r"(?:메모|생각|노트|TODO)\s*[:：]", re.IGNORECASE)


def audit_library(settings: Settings) -> tuple[list[BookMetadata], list[ParseFailure]]:
    """Audit every discoverable file; record individual failures and continue."""
    root = settings.project.library_path
    books: list[BookMetadata] = []
    failures: list[ParseFailure] = []
    files = discover_markdown_files(root, settings.ingestion.ignored_directories)
    for path in files:
        try:
            text = read_markdown(path)
            parsed = parse_frontmatter(text)
            books.append(extract_book_metadata(path, parsed, root))
        except Exception as exc:  # batch operation must continue on a malformed document
            LOGGER.warning("Failed to parse %s: %s", path, exc)
            failures.append(ParseFailure(source_file=path.relative_to(root), error=str(exc)))
    write_books_metadata(books, settings.project.metadata_path)
    write_audit_report(books, failures, settings.project.audit_report_path, root)
    LOGGER.info("Library audit complete: %d parsed, %d failed", len(books), len(failures))
    return books, failures


def write_books_metadata(books: list[BookMetadata], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"books": [book.model_dump(mode="json") for book in books]}
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _duplicate_groups(books: list[BookMetadata]) -> list[list[str]]:
    groups: dict[str, list[str]] = {}
    for book in books:
        groups.setdefault(book.content_hash, []).append(book.source_file.as_posix())
    return [paths for paths in groups.values() if len(paths) > 1]


def _source_texts(books: list[BookMetadata], root: Path) -> list[str]:
    texts = []
    for book in books:
        try:
            texts.append((root / book.source_file).read_text(encoding="utf-8"))
        except OSError:
            pass
    return texts


def write_audit_report(
    books: list[BookMetadata], failures: list[ParseFailure], path: Path, source_root: Path
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    total = len(books) + len(failures)
    percentage = lambda count: f"{(count / total * 100):.1f}%" if total else "0.0%"
    lengths = [book.character_count for book in books]
    categories = Counter(category for book in books for category in book.category)
    texts = _source_texts(books, source_root)
    longest = max(books, key=lambda book: book.character_count, default=None)
    shortest = min(books, key=lambda book: book.character_count, default=None)
    duplicates = _duplicate_groups(books)
    unknown_titles = sum(book.title == "unknown" for book in books)
    unknown_authors = sum(book.author == "unknown" for book in books)
    lines = [
        "# 라이브러리 진단 리포트",
        "",
        "## 요약",
        f"- 전체 파일 수: {total}",
        f"- 정상 파싱 파일 수: {len(books)}",
        f"- 파싱 실패 파일 수: {len(failures)}",
        f"- YAML frontmatter 포함 비율: {percentage(sum(book.has_frontmatter for book in books))}",
        f"- 제목 추출 성공률: {percentage(len(books) - unknown_titles)}",
        f"- 저자 추출 성공률: {percentage(len(books) - unknown_authors)}",
        f"- heading 사용 비율: {percentage(sum(bool(book.headings) for book in books))}",
        f"- 평균 문서 길이: {(sum(lengths) / len(lengths)):.1f}자" if lengths else "- 평균 문서 길이: 0자",
        f"- 가장 긴 문서: {longest.source_file.as_posix()} ({longest.character_count}자)" if longest else "- 가장 긴 문서: 없음",
        f"- 가장 짧은 문서: {shortest.source_file.as_posix()} ({shortest.character_count}자)" if shortest else "- 가장 짧은 문서: 없음",
        "",
        "## 카테고리 분포",
    ]
    lines.extend(f"- {name}: {count}" for name, count in sorted(categories.items()))
    if not categories:
        lines.append("- 없음")
    lines += [
        "",
        "## 문서 패턴",
        f"- 공백 포함 파일명: {sum(' ' in book.source_file.name for book in books)}개",
        f"- 한글 포함 파일명: {sum(bool(re.search('[가-힣]', book.source_file.name)) for book in books)}개",
        f"- 인용문 표기 문서: {sum(bool(QUOTE_RE.search(text)) for text in texts)}개",
        f"- 개인 메모 표기 문서: {sum(bool(MEMO_RE.search(text)) for text in texts)}개",
        "",
        "## 중복 가능성이 있는 문서",
    ]
    lines.extend(f"- {', '.join(group)}" for group in duplicates)
    if not duplicates:
        lines.append("- 없음")
    lines += ["", "## 파싱 오류 목록"]
    lines.extend(f"- `{failure.source_file}`: {failure.error}" for failure in failures)
    if not failures:
        lines.append("- 없음")
    lines += ["", "## 메타데이터 경고"]
    warning_rows = [
        f"- `{book.source_file}`: {', '.join(book.warnings)}" for book in books if book.warnings
    ]
    lines.extend(warning_rows or ["- 없음"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
