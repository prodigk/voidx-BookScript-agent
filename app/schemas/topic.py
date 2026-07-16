"""Phase 4 topic planning schemas."""

from typing import Annotated

from pydantic import BaseModel, Field

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
Keyword = Annotated[str, Field(min_length=1, max_length=50)]


class TopicRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=500)
    duration_minutes: int = Field(default=12, ge=3, le=60)
    target_book_count: int = Field(default=3, ge=2, le=4)
    tone: str = Field(default="사색적")
    audience: str = Field(default="일반 성인")
    desired_lenses: list[str] = Field(default_factory=list, max_length=8)
    desired_emotional_effects: list[str] = Field(default_factory=list, max_length=8)
    excluded_lenses: list[str] = Field(default_factory=list, max_length=8)


class TopicAnalysis(BaseModel):
    core_question: ShortText
    intent: ShortText
    subtopics: list[Keyword] = Field(min_length=2, max_length=8)
    keywords: list[Keyword] = Field(min_length=3, max_length=12)
    search_queries: list[ShortText] = Field(min_length=2, max_length=6)
