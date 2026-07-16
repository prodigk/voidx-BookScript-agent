"""Heading analysis and metadata extraction with documented fallbacks."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from app.ingestion.frontmatter_parser import ParsedMarkdown
from app.schemas.book import BookMetadata, HeadingInfo

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
AUTHOR_PATTERNS = (
    re.compile(r"^(?:저자|지은이|글)\s*[:：]\s*(.+)$", re.MULTILINE),
    re.compile(r"^by\s+(.+)$", re.MULTILINE | re.IGNORECASE),
)


def analyze_headings(content: str, line_offset: int = 0) -> list[HeadingInfo]:
    return [
        HeadingInfo(level=len(match.group(1)), text=match.group(2).strip(), line=line_number + line_offset)
        for line_number, line in enumerate(content.splitlines(), start=1)
        if (match := HEADING_RE.match(line))
    ]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _infer_author(metadata: dict[str, Any], content: str) -> str:
    author = metadata.get("author") or metadata.get("저자")
    if author:
        return str(author).strip()
    for pattern in AUTHOR_PATTERNS:
        if match := pattern.search(content):
            return match.group(1).strip()
    return "unknown"


def extract_book_metadata(path: Path, parsed: ParsedMarkdown, source_root: Path) -> BookMetadata:
    """Extract metadata using frontmatter, H1, filename, then body-pattern fallbacks."""
    headings = analyze_headings(parsed.content, parsed.content_start_line - 1)
    title_value = parsed.metadata.get("title") or parsed.metadata.get("제목")
    title = str(title_value).strip() if title_value else ""
    if not title:
        title = next((heading.text for heading in headings if heading.level == 1), path.stem)
    author = _infer_author(parsed.metadata, parsed.content)
    category = _as_list(parsed.metadata.get("category") or parsed.metadata.get("categories") or parsed.metadata.get("카테고리"))
    tags = _as_list(parsed.metadata.get("tags") or parsed.metadata.get("태그"))
    relative = path.relative_to(source_root)
    if not category and len(relative.parts) > 1:
        category = [relative.parts[0]]
    digest = hashlib.sha256(parsed.raw_text.encode("utf-8")).hexdigest()
    warnings: list[str] = []
    if author == "unknown":
        warnings.append("author_unknown")
    if not category:
        warnings.append("category_unknown")
    return BookMetadata(
        book_id=f"book_{hashlib.sha256(relative.as_posix().encode('utf-8')).hexdigest()[:12]}",
        title=title or "unknown",
        author=author,
        category=category,
        tags=tags,
        source_file=relative,
        has_frontmatter=parsed.has_frontmatter,
        headings=headings,
        character_count=len(parsed.content),
        content_hash=digest,
        warnings=warnings,
    )
