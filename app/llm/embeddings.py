"""Bounded OpenAI embeddings client with usage-only logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Protocol

from openai import OpenAI

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingBatch:
    vectors: list[list[float]]
    tokens: int


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> EmbeddingBatch: ...


class OpenAIEmbeddingProvider:
    def __init__(self, model: str, dimensions: int, max_retries: int = 3) -> None:
        self.model = model
        self.dimensions = dimensions
        self.max_retries = max_retries
        self.client = OpenAI()

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        """Embed selected texts only; never log their content."""
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("Embedding input must contain non-empty text")
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.embeddings.create(
                    model=self.model, input=texts, dimensions=self.dimensions, encoding_format="float"
                )
                vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
                if len(vectors) != len(texts):
                    raise RuntimeError("Embedding response count did not match input count")
                tokens = response.usage.total_tokens
                LOGGER.info("Embedding call complete: model=%s inputs=%d tokens=%d attempt=%d", self.model, len(texts), tokens, attempt + 1)
                return EmbeddingBatch(vectors=vectors, tokens=tokens)
            except Exception:
                if attempt >= self.max_retries:
                    LOGGER.exception("Embedding call failed after %d attempts", attempt + 1)
                    raise
                delay = min(2**attempt, 8)
                LOGGER.warning("Embedding call failed; retrying in %ds (%d/%d)", delay, attempt + 1, self.max_retries)
                time.sleep(delay)
        raise RuntimeError("Unreachable embedding retry state")
