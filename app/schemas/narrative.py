"""Phase 5 narrative architecture schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

NarrativeText = Annotated[str, Field(min_length=1, max_length=500)]


class NarrativeSection(BaseModel):
    section_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    title: Annotated[str, Field(min_length=1, max_length=120)]
    narrative_function: Literal[
        "hook", "problem", "book_perspective", "transition", "tension",
        "integration", "application", "conclusion",
    ]
    purpose: NarrativeText
    key_points: list[NarrativeText] = Field(min_length=1, max_length=5)
    book_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    estimated_seconds: int = Field(ge=15, le=600)


class NarrativePlan(BaseModel):
    title_candidates: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=3, max_length=7)
    selected_title: Annotated[str, Field(min_length=1, max_length=120)] | None = None
    core_message: NarrativeText
    emotional_arc: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(min_length=3, max_length=8)
    sections: list[NarrativeSection] = Field(min_length=5, max_length=14)
    total_seconds: int = Field(ge=180, le=3600)
