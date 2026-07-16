"""Schemas shared by the approved-script to Remotion export boundary."""

from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class VideoQuote(BaseModel):
    """Exact quotation card rendered inside a scene."""

    text: Annotated[str, Field(min_length=1, max_length=300)]
    source: Annotated[str, Field(min_length=1, max_length=1000)]
    display_source: Annotated[str, Field(min_length=1, max_length=200)]
    duration_seconds: int = Field(ge=4, le=15)


class VideoAudio(BaseModel):
    """Public-directory audio asset consumed by Remotion."""

    src: Annotated[str, Field(min_length=1, max_length=500)]
    volume: float = Field(default=1.0, ge=0, le=1)


class VideoScene(BaseModel):
    """One contiguous Remotion Sequence derived from a script section."""

    section_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    title: Annotated[str, Field(min_length=1, max_length=120)]
    start_seconds: int = Field(ge=0)
    end_seconds: int = Field(gt=0)
    start_frame: int = Field(ge=0)
    duration_frames: int = Field(gt=0)
    narration: Annotated[str, Field(min_length=1)]
    visual_intent: Annotated[str, Field(min_length=1, max_length=500)]
    on_screen_text: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(
        default_factory=list, max_length=3,
    )
    suggested_assets: list[Annotated[str, Field(min_length=1, max_length=150)]] = Field(
        default_factory=list, max_length=4,
    )
    quote: VideoQuote | None = None


class VideoManifest(BaseModel):
    """Renderer-neutral, validated input for the local Remotion project."""

    schema_version: str = "1.0"
    run_id: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1, max_length=120)]
    renderer: str = "remotion"
    validation_status: str = "approved"
    fps: int = Field(ge=1, le=120)
    width: int = Field(ge=640, le=7680)
    height: int = Field(ge=360, le=4320)
    duration_seconds: int = Field(gt=0)
    duration_frames: int = Field(gt=0)
    source_script: Annotated[str, Field(min_length=1)]
    audio: VideoAudio | None = None
    reference_books: list[Annotated[str, Field(min_length=1, max_length=120)]] = Field(min_length=1)
    scenes: list[VideoScene] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline(self) -> "VideoManifest":
        if self.renderer != "remotion" or self.validation_status != "approved":
            raise ValueError("Video manifest requires an approved Remotion run")
        expected_second = 0
        for scene in self.scenes:
            if scene.start_seconds != expected_second:
                raise ValueError(f"Non-contiguous scene timeline at {scene.section_id}")
            if scene.end_seconds <= scene.start_seconds:
                raise ValueError(f"Invalid scene duration at {scene.section_id}")
            if scene.start_frame != scene.start_seconds * self.fps:
                raise ValueError(f"Invalid start frame at {scene.section_id}")
            if scene.duration_frames != (scene.end_seconds - scene.start_seconds) * self.fps:
                raise ValueError(f"Invalid frame duration at {scene.section_id}")
            expected_second = scene.end_seconds
        if expected_second != self.duration_seconds:
            raise ValueError("Scene timeline does not match manifest duration")
        if self.duration_frames != self.duration_seconds * self.fps:
            raise ValueError("Manifest duration_frames does not match fps")
        return self
