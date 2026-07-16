"""Phase 6 evidence-linked narration script schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

ScriptText = Annotated[str, Field(min_length=1, max_length=2500)]


class RemotionCue(BaseModel):
    """Renderer-neutral scene intent designed for a future Remotion Sequence."""

    visual_intent: Annotated[str, Field(min_length=1, max_length=300)]
    scene_type: Literal["standard", "quote_card"] = "standard"
    quote_text: Annotated[str, Field(min_length=1, max_length=300)] | None = None
    quote_evidence_id: str | None = None
    quote_duration_seconds: int | None = Field(default=None, ge=4, le=15)
    on_screen_text: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(
        default_factory=list, max_length=3,
    )
    suggested_assets: list[Annotated[str, Field(min_length=1, max_length=100)]] = Field(
        default_factory=list, max_length=4,
    )


class ScriptParagraph(BaseModel):
    paragraph_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    text_type: Literal[
        "quotation", "paraphrase", "interpretation", "transition", "example", "commentary",
    ]
    text: ScriptText
    book_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class ScriptSection(BaseModel):
    section_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    title: Annotated[str, Field(min_length=1, max_length=120)]
    estimated_seconds: int = Field(ge=15, le=600)
    remotion_cue: RemotionCue
    paragraphs: list[ScriptParagraph] = Field(min_length=1, max_length=12)


class ScriptDocument(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=120)]
    target_duration_seconds: int = Field(ge=180, le=3600)
    sections: list[ScriptSection] = Field(min_length=5, max_length=14)
