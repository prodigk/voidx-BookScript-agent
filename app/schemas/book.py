"""Book metadata and audit models."""

from pathlib import Path

from pydantic import BaseModel, Field


class HeadingInfo(BaseModel):
    level: int = Field(ge=1, le=6)
    text: str
    line: int = Field(ge=1)


class Book(BaseModel):
    book_id: str
    title: str = "unknown"
    author: str = "unknown"
    category: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_file: Path
    has_frontmatter: bool = False
    headings: list[HeadingInfo] = Field(default_factory=list)
    character_count: int = 0
    content_hash: str
    warnings: list[str] = Field(default_factory=list)


class ParseFailure(BaseModel):
    source_file: Path
    error: str


# Phase 1 compatibility name; serialized data remains unchanged.
BookMetadata = Book
