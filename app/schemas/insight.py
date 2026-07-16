"""Editorial insight registry and strategy schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

StrategyText = Annotated[str, Field(min_length=1, max_length=500)]


class InsightSection(BaseModel):
    heading: str
    level: int = Field(ge=1, le=6)
    content: str


class InsightDocument(BaseModel):
    insight_id: str
    source_file: str
    title: str
    insight_type: str
    source: str
    created_at: str | None = None
    tags: list[str] = Field(default_factory=list)
    content_hash: str
    sections: list[InsightSection]


class InsightManifest(BaseModel):
    profile: str
    documents: list[InsightDocument]


class InsightSyncSummary(BaseModel):
    discovered: int
    added: int
    updated: int
    unchanged: int
    deleted: int
    manifest_path: str


class EditorialStrategy(BaseModel):
    profile: str
    source_insight_ids: list[str] = Field(min_length=1)
    topic_opportunity: StrategyText
    audience_state: StrategyText
    positioning: StrategyText
    title_directions: list[StrategyText] = Field(min_length=3, max_length=6)
    hook_strategy: StrategyText
    narrative_strategy: list[StrategyText] = Field(min_length=3, max_length=7)
    tone_rules: list[StrategyText] = Field(min_length=2, max_length=6)
    closing_strategy: StrategyText
    duration_guidance: StrategyText
    avoid_patterns: list[StrategyText] = Field(min_length=1, max_length=6)


class TopicIdea(BaseModel):
    title: Annotated[str, Field(min_length=2, max_length=120)]
    core_question: Annotated[str, Field(min_length=2, max_length=200)]
    audience_state: Annotated[str, Field(min_length=1, max_length=100)]
    emotional_promise: Annotated[str, Field(min_length=1, max_length=200)]
    suggested_lenses: list[str] = Field(min_length=1, max_length=5)
    format: Literal["standard", "sleep_longform", "shortform"]
    reason: StrategyText


class TopicIdeas(BaseModel):
    profile: str
    source_insight_ids: list[str] = Field(min_length=1)
    ideas: list[TopicIdea] = Field(min_length=3, max_length=20)
