"""Full and incremental Markdown indexing."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.ingestion.chunker import chunk_markdown
from app.ingestion.frontmatter_parser import parse_frontmatter
from app.ingestion.markdown_loader import discover_markdown_files, read_markdown
from app.ingestion.metadata_parser import extract_book_metadata
from app.schemas.book import ParseFailure
from app.schemas.chunk import Chunk
from app.storage.database import connect_database, initialize_database

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class IndexSummary:
    discovered: int
    indexed: int
    unchanged: int
    deleted: int
    chunks: int
    failures: tuple[ParseFailure, ...]


def _delete_book(connection, book_id: str) -> None:
    connection.execute("DELETE FROM chunks_fts WHERE book_id = ?", (book_id,))
    connection.execute("DELETE FROM books WHERE id = ?", (book_id,))


def _insert_chunk(connection, chunk: Chunk) -> None:
    heading_json = json.dumps(chunk.heading_path, ensure_ascii=False)
    connection.execute(
        "INSERT INTO chunks(id, book_id, heading_path, start_line, end_line, content, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (chunk.chunk_id, chunk.book_id, heading_json, chunk.start_line, chunk.end_line, chunk.content, chunk.content_hash),
    )
    connection.execute(
        "INSERT INTO chunks_fts(chunk_id, book_id, title, author, heading_path, content) VALUES (?, ?, ?, ?, ?, ?)",
        (chunk.chunk_id, chunk.book_id, chunk.title, chunk.author, " > ".join(chunk.heading_path), chunk.content),
    )


def build_index(settings: Settings, full: bool = False) -> IndexSummary:
    """Index changed documents and remove records for source files that disappeared."""
    initialize_database(settings.project.database_path)
    root = settings.project.library_path
    files = discover_markdown_files(root, settings.ingestion.ignored_directories)
    indexed = unchanged = deleted = chunk_count = 0
    failures: list[ParseFailure] = []
    seen_sources: set[str] = set()
    with connect_database(settings.project.database_path) as connection:
        if full:
            connection.execute("DELETE FROM chunks_fts")
            connection.execute("DELETE FROM books")
        existing = {
            row["source_file"]: (row["id"], row["content_hash"])
            for row in connection.execute("SELECT id, source_file, content_hash FROM books")
        }
        for path in files:
            relative = path.relative_to(root).as_posix()
            seen_sources.add(relative)
            try:
                parsed = parse_frontmatter(read_markdown(path))
                book = extract_book_metadata(path, parsed, root)
                prior = existing.get(relative)
                if prior and prior[1] == book.content_hash:
                    unchanged += 1
                    continue
                if prior:
                    _delete_book(connection, prior[0])
                connection.execute(
                    """INSERT INTO books(id, title, author, category, tags, source_file, content_hash)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        book.book_id,
                        book.title,
                        book.author,
                        json.dumps(book.category, ensure_ascii=False),
                        json.dumps(book.tags, ensure_ascii=False),
                        relative,
                        book.content_hash,
                    ),
                )
                chunks = chunk_markdown(book, parsed.content, parsed.content_start_line, settings.chunking)
                for chunk in chunks:
                    _insert_chunk(connection, chunk)
                indexed += 1
                chunk_count += len(chunks)
            except Exception as exc:
                LOGGER.warning("Failed to index %s: %s", path, exc)
                failures.append(ParseFailure(source_file=Path(relative), error=str(exc)))
        for source_file, (book_id, _) in existing.items():
            if source_file not in seen_sources:
                _delete_book(connection, book_id)
                deleted += 1
    LOGGER.info(
        "Index complete: %d discovered, %d indexed, %d unchanged, %d deleted, %d chunks, %d failed",
        len(files), indexed, unchanged, deleted, chunk_count, len(failures),
    )
    return IndexSummary(len(files), indexed, unchanged, deleted, chunk_count, tuple(failures))
