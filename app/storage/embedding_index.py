"""Incremental embedding generation and SQLite vector cache."""

from __future__ import annotations

import logging
from array import array
from dataclasses import dataclass

from app.config import Settings
from app.llm.embeddings import EmbeddingProvider, OpenAIEmbeddingProvider
from app.storage.database import connect_database, initialize_database

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingSummary:
    discovered: int
    embedded: int
    cached: int
    deleted_stale: int
    tokens: int
    model: str
    dimensions: int


def vector_to_blob(vector: list[float]) -> bytes:
    return array("f", vector).tobytes()


def blob_to_vector(blob: bytes) -> list[float]:
    values = array("f")
    values.frombytes(blob)
    return values.tolist()


def build_embeddings(settings: Settings, provider: EmbeddingProvider | None = None, *, full: bool = False) -> EmbeddingSummary:
    """Embed only uncached or content-changed chunks for the configured model."""
    initialize_database(settings.project.database_path)
    model, dimensions = settings.embedding.model, settings.embedding.dimensions
    provider = provider or OpenAIEmbeddingProvider(model, dimensions, settings.embedding.max_retries)
    embedded = tokens = 0
    with connect_database(settings.project.database_path) as connection:
        if full:
            connection.execute("DELETE FROM embeddings WHERE model = ? AND dimensions = ?", (model, dimensions))
        stale = connection.execute(
            """DELETE FROM embeddings WHERE model = ? AND dimensions = ?
               AND (chunk_id NOT IN (SELECT id FROM chunks)
                    OR content_hash != (SELECT content_hash FROM chunks WHERE chunks.id = embeddings.chunk_id))""",
            (model, dimensions),
        ).rowcount
        rows = connection.execute(
            """SELECT c.id, c.content, c.content_hash, CASE WHEN e.chunk_id IS NULL THEN 0 ELSE 1 END AS cached
               FROM chunks c LEFT JOIN embeddings e
               ON e.chunk_id = c.id AND e.model = ? AND e.dimensions = ? ORDER BY c.id""",
            (model, dimensions),
        ).fetchall()
        pending = [row for row in rows if not row["cached"]]
        cached = len(rows) - len(pending)
        for start in range(0, len(pending), settings.embedding.batch_size):
            batch = pending[start : start + settings.embedding.batch_size]
            result = provider.embed([row["content"] for row in batch])
            if any(len(vector) != dimensions for vector in result.vectors):
                raise ValueError(f"Unexpected embedding dimensions; expected {dimensions}")
            connection.executemany(
                "INSERT OR REPLACE INTO embeddings(chunk_id, model, dimensions, content_hash, vector) VALUES (?, ?, ?, ?, ?)",
                [(row["id"], model, dimensions, row["content_hash"], vector_to_blob(vector)) for row, vector in zip(batch, result.vectors, strict=True)],
            )
            embedded += len(batch)
            tokens += result.tokens
            connection.commit()
            LOGGER.info("Embedding cache progress: %d/%d new chunks", embedded, len(pending))
    return EmbeddingSummary(len(rows), embedded, cached, max(stale, 0), tokens, model, dimensions)
