"""Traceable Markdown chunk models."""

from pathlib import Path

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    chunk_id: str
    book_id: str
    title: str
    author: str
    source_file: Path
    heading_path: list[str] = Field(default_factory=list)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    content: str
    content_hash: str


class SearchResult(Chunk):
    score: float


class HybridSearchResult(SearchResult):
    keyword_score: float = 0.0
    semantic_score: float = 0.0
    metadata_score: float = 0.0
    diversity_score: float = 0.0
