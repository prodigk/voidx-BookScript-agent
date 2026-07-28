"""Phase 4 topic planning schemas."""

from typing import Annotated

from pydantic import BaseModel, Field, model_validator

ShortText = Annotated[str, Field(min_length=1, max_length=200)]
Keyword = Annotated[str, Field(min_length=1, max_length=50)]

EDITORIAL_FOCUS = ("인문학", "철학", "심리학")
DEFAULT_EXCLUDED_LENSES = ("커리어", "생산성", "조직관리", "성과 중심")


class TopicRequest(BaseModel):
    topic: str = Field(min_length=2, max_length=500)
    duration_minutes: int = Field(default=12, ge=3, le=60)
    target_book_count: int = Field(default=3, ge=2, le=4)
    tone: str = Field(default="사색적")
    audience: str = Field(default="일반 성인")
    desired_lenses: list[str] = Field(default_factory=list, max_length=8)
    desired_emotional_effects: list[str] = Field(default_factory=list, max_length=8)
    excluded_lenses: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def apply_editorial_focus(self) -> "TopicRequest":
        """Keep new research runs centered on humanities, philosophy, and psychology."""
        blocked = set(DEFAULT_EXCLUDED_LENSES)
        desired = list(dict.fromkeys(
            lens for lens in self.desired_lenses if lens not in blocked
        ))
        excluded = list(dict.fromkeys([
            *self.excluded_lenses,
            *DEFAULT_EXCLUDED_LENSES,
        ]))
        self.desired_lenses = desired[:8]
        self.excluded_lenses = excluded[:8]
        return self


class TopicAnalysis(BaseModel):
    core_question: ShortText
    intent: ShortText
    subtopics: list[Keyword] = Field(min_length=2, max_length=8)
    keywords: list[Keyword] = Field(min_length=3, max_length=12)
    search_queries: list[ShortText] = Field(min_length=2, max_length=6)
