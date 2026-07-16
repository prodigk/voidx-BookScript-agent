"""Local cosine similarity search over cached OpenAI embeddings."""

from __future__ import annotations

import json
import math
from pathlib import Path

from app.config import Settings
from app.llm.embeddings import EmbeddingProvider, OpenAIEmbeddingProvider
from app.schemas.chunk import SearchResult
from app.storage.database import connect_database
from app.storage.embedding_index import blob_to_vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Vector dimensions do not match")
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def semantic_search(
    settings: Settings,
    query: str,
    limit: int = 10,
    provider: EmbeddingProvider | None = None,
) -> list[SearchResult]:
    """Embed a query and rank locally cached chunk vectors by cosine similarity."""
    if not query.strip():
        raise ValueError("검색어는 비어 있을 수 없습니다.")
    if limit < 1 or limit > 1000:
        raise ValueError("limit은 1에서 1000 사이여야 합니다.")
    provider = provider or OpenAIEmbeddingProvider(
        settings.embedding.model, settings.embedding.dimensions, settings.embedding.max_retries
    )
    query_vector = provider.embed([query]).vectors[0]
    with connect_database(settings.project.database_path) as connection:
        rows = connection.execute(
            """SELECT c.id AS chunk_id, c.book_id, b.title, b.author, b.source_file,
                      c.heading_path, c.start_line, c.end_line, c.content, c.content_hash, e.vector
               FROM embeddings e JOIN chunks c ON c.id = e.chunk_id JOIN books b ON b.id = c.book_id
               WHERE e.model = ? AND e.dimensions = ?""",
            (settings.embedding.model, settings.embedding.dimensions),
        ).fetchall()
    scored = sorted(
        ((cosine_similarity(query_vector, blob_to_vector(row["vector"])), row) for row in rows),
        key=lambda item: item[0], reverse=True,
    )[:limit]
    return [
        SearchResult(
            chunk_id=row["chunk_id"], book_id=row["book_id"], title=row["title"], author=row["author"],
            source_file=Path(row["source_file"]), heading_path=json.loads(row["heading_path"]),
            start_line=row["start_line"], end_line=row["end_line"], content=row["content"],
            content_hash=row["content_hash"], score=score,
        )
        for score, row in scored
    ]
