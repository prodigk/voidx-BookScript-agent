"""Heading-aware Markdown chunking with exact source line ranges."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.config import ChunkingSettings
from app.schemas.book import Book
from app.schemas.chunk import Chunk

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class _Piece:
    text: str
    start_line: int
    end_line: int
    heading_path: tuple[str, ...]


def _split_long_line(text: str, line: int, path: tuple[str, ...], maximum: int) -> list[_Piece]:
    return [_Piece(text[index : index + maximum], line, line, path) for index in range(0, len(text), maximum)]


def _paragraph_pieces(content: str, start_line: int, maximum: int) -> list[_Piece]:
    pieces: list[_Piece] = []
    headings: list[str] = []
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        text = "\n".join(value for _, value in paragraph).strip()
        first, last = paragraph[0][0], paragraph[-1][0]
        path = tuple(headings)
        if len(text) <= maximum:
            pieces.append(_Piece(text, first, last, path))
        else:
            current: list[tuple[int, str]] = []
            current_length = 0
            for number, value in paragraph:
                addition = len(value) + (1 if current else 0)
                if current and current_length + addition > maximum:
                    pieces.append(_Piece("\n".join(v for _, v in current), current[0][0], current[-1][0], path))
                    current, current_length = [], 0
                if len(value) > maximum:
                    if current:
                        pieces.append(_Piece("\n".join(v for _, v in current), current[0][0], current[-1][0], path))
                        current, current_length = [], 0
                    pieces.extend(_split_long_line(value, number, path, maximum))
                else:
                    current.append((number, value))
                    current_length += len(value) + (1 if len(current) > 1 else 0)
            if current:
                pieces.append(_Piece("\n".join(v for _, v in current), current[0][0], current[-1][0], path))
        paragraph.clear()

    for offset, line in enumerate(content.splitlines(), start=start_line):
        if match := HEADING_RE.match(line):
            flush()
            level = len(match.group(1))
            headings[level - 1 :] = [match.group(2).strip()]
        elif not line.strip():
            flush()
        else:
            paragraph.append((offset, line))
    flush()
    return pieces


def _make_chunk(book: Book, pieces: list[_Piece], sequence: int) -> Chunk:
    content = "\n\n".join(piece.text for piece in pieces)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return Chunk(
        chunk_id=f"{book.book_id}_chunk_{sequence:04d}",
        book_id=book.book_id,
        title=book.title,
        author=book.author,
        source_file=book.source_file,
        heading_path=list(pieces[-1].heading_path),
        start_line=min(piece.start_line for piece in pieces),
        end_line=max(piece.end_line for piece in pieces),
        content=content,
        content_hash=digest,
    )


def chunk_markdown(book: Book, content: str, content_start_line: int, settings: ChunkingSettings) -> list[Chunk]:
    """Chunk body paragraphs within heading boundaries and retain traceability."""
    pieces = _paragraph_pieces(content, content_start_line, settings.max_chars)
    if not pieces:
        return []
    groups: list[list[_Piece]] = []
    current: list[_Piece] = []
    current_length = 0
    for piece in pieces:
        addition = len(piece.text) + (2 if current else 0)
        heading_changed = bool(current and current[-1].heading_path != piece.heading_path)
        if current and (heading_changed or current_length + addition > settings.max_chars or current_length >= settings.target_chars):
            groups.append(current)
            overlap: list[_Piece] = []
            overlap_size = 0
            if not heading_changed and settings.overlap_chars:
                for prior in reversed(current):
                    if overlap and overlap_size + len(prior.text) > settings.overlap_chars:
                        break
                    overlap.insert(0, prior)
                    overlap_size += len(prior.text)
            current = overlap
            current_length = len("\n\n".join(item.text for item in current))
        if current and current_length + len(piece.text) + 2 > settings.max_chars:
            groups.append(current)
            current, current_length = [], 0
        current.append(piece)
        current_length = len("\n\n".join(item.text for item in current))
    if current:
        groups.append(current)

    # Merge a short final group only when the heading and maximum-size constraints allow it.
    if len(groups) > 1 and len("\n\n".join(p.text for p in groups[-1])) < settings.min_chars:
        previous, final = groups[-2], groups[-1]
        merged = previous + [piece for piece in final if piece not in previous]
        merged_text = "\n\n".join(piece.text for piece in merged)
        if previous[-1].heading_path == final[-1].heading_path and len(merged_text) <= settings.max_chars:
            groups[-2:] = [merged]
    return [_make_chunk(book, group, index) for index, group in enumerate(groups, start=1)]
