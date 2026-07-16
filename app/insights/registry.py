"""Discover, parse, snapshot, and select editorial insight Markdown files."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

from app.config import InsightSettings
from app.schemas.insight import (
    InsightDocument, InsightManifest, InsightSection, InsightSyncSummary,
)

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
METADATA = re.compile(r"^-\s*(유형|출처|생성일|태그):\s*(.*?)\s*$")
PRIORITY_HEADINGS = ("잠들기전 교양이 적용", "추천 전략", "요약", "주제", "제목", "포맷", "다음 액션")


def _normalized_relative(path: Path, root: Path) -> str:
    return unicodedata.normalize("NFC", path.relative_to(root).as_posix())


def _parse_sections(text: str) -> tuple[str, list[InsightSection]]:
    title = ""
    sections: list[InsightSection] = []
    heading = "문서 정보"
    level = 1
    buffer: list[str] = []
    for line in text.splitlines():
        match = HEADING.match(line)
        if match:
            if buffer and any(item.strip() for item in buffer):
                sections.append(InsightSection(heading=heading, level=level, content="\n".join(buffer).strip()))
            level = len(match.group(1))
            heading = match.group(2).strip()
            if not title:
                title = heading
            buffer = []
        else:
            buffer.append(line)
    if buffer and any(item.strip() for item in buffer):
        sections.append(InsightSection(heading=heading, level=level, content="\n".join(buffer).strip()))
    return title, sections


def parse_insight_file(path: Path, root: Path) -> InsightDocument:
    raw = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    relative = _normalized_relative(path, root)
    title, sections = _parse_sections(raw)
    metadata: dict[str, str] = {}
    for line in raw.splitlines()[:15]:
        if match := METADATA.match(line):
            metadata[match.group(1)] = match.group(2).strip()
    tags = [item.strip() for item in metadata.get("태그", "").split(",") if item.strip()]
    stable_path = unicodedata.normalize("NFC", relative).encode("utf-8")
    return InsightDocument(
        insight_id="insight_" + hashlib.sha256(stable_path).hexdigest()[:12],
        source_file=relative, title=title or path.stem,
        insight_type=metadata.get("유형", "unknown"), source=metadata.get("출처", "unknown"),
        created_at=metadata.get("생성일"), tags=tags, content_hash=content_hash, sections=sections,
    )


def discover_insights(root: Path) -> list[InsightDocument]:
    if not root.is_dir():
        return []
    files = sorted(
        (path for path in root.rglob("*.md") if not any(part.startswith(".") for part in path.relative_to(root).parts)),
        key=lambda path: unicodedata.normalize("NFC", path.as_posix()),
    )
    return [parse_insight_file(path, root) for path in files]


def sync_insights(settings: InsightSettings) -> tuple[InsightManifest, InsightSyncSummary]:
    documents = discover_insights(settings.path)
    manifest = InsightManifest(profile=settings.default_profile, documents=documents)
    previous: dict[str, str] = {}
    if settings.manifest_path.is_file():
        old = InsightManifest.model_validate_json(settings.manifest_path.read_text(encoding="utf-8"))
        previous = {item.insight_id: item.content_hash for item in old.documents}
    current = {item.insight_id: item.content_hash for item in documents}
    added = sum(item not in previous for item in current)
    updated = sum(item in previous and previous[item] != digest for item, digest in current.items())
    unchanged = sum(item in previous and previous[item] == digest for item, digest in current.items())
    deleted = sum(item not in current for item in previous)
    settings.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    settings.manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest, InsightSyncSummary(
        discovered=len(documents), added=added, updated=updated, unchanged=unchanged, deleted=deleted,
        manifest_path=settings.manifest_path.as_posix(),
    )


def select_insight_context(manifest: InsightManifest, query: str, max_chars: int, max_documents: int) -> str:
    tokens = {item for item in re.findall(r"[0-9A-Za-z가-힣]{2,}", query.lower())}
    ranked: list[tuple[int, str, InsightDocument, InsightSection]] = []
    allowed_ids = {item.insight_id for item in manifest.documents[:max_documents]}
    for document in manifest.documents:
        if document.insight_id not in allowed_ids:
            continue
        for section in document.sections:
            haystack = f"{document.title} {document.source} {section.heading} {section.content}".lower()
            score = sum(3 for token in tokens if token in haystack)
            score += sum(8 for priority in PRIORITY_HEADINGS if priority in section.heading)
            if manifest.profile in haystack:
                score += 4
            ranked.append((score, document.source_file, document, section))
    ranked.sort(key=lambda item: (-item[0], item[1], item[3].heading))
    blocks: list[str] = []
    used = 0
    for score, _, document, section in ranked:
        if score <= 0 and blocks:
            continue
        block = (
            f"INSIGHT {document.insight_id} | type={document.insight_type} | source={document.source} "
            f"| file={document.source_file} | hash={document.content_hash}\n"
            f"SECTION {section.heading}\n{section.content}"
        )
        if used + len(block) > max_chars:
            continue
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)
