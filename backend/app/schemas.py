"""Pydantic response schemas for the local web API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.topic import TopicRequest


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "youtube-book-script-agent"
    api_version: str = "v1"


class LibraryStatusResponse(BaseModel):
    library_available: bool
    database_available: bool
    source_file_count: int = Field(ge=0)
    book_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    embedding_count: int = Field(ge=0)
    current_embedding_count: int = Field(ge=0)
    embedding_model: str
    embedding_dimensions: int
    last_indexed_at: datetime | None = None


RunStatus = Literal[
    "started", "research_complete", "outline_ready", "script_ready", "needs_revision", "approved",
]


class ArtifactSummary(BaseModel):
    name: str
    media_type: str
    size_bytes: int = Field(ge=0)


class RunSummary(BaseModel):
    run_id: str
    topic: str
    status: RunStatus
    created_at: datetime
    artifacts: list[ArtifactSummary]


class RunListResponse(BaseModel):
    items: list[RunSummary]
    total: int = Field(ge=0)


class RunDetailResponse(RunSummary):
    validation_valid_count: int | None = Field(default=None, ge=0)
    validation_review_count: int | None = Field(default=None, ge=0)
    validation_invalid_count: int | None = Field(default=None, ge=0)


JobStatus = Literal["queued", "running", "succeeded", "failed"]


class ResearchJobResponse(BaseModel):
    job_id: str
    kind: Literal["research"] = "research"
    status: JobStatus
    stage: str
    request: TopicRequest
    run_id: str | None = None
    pipeline_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class SelectionRequest(BaseModel):
    selected_book_ids: list[str] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def selected_books_are_unique(self) -> "SelectionRequest":
        if len(set(self.selected_book_ids)) != len(self.selected_book_ids):
            raise ValueError("selected_book_ids must be unique")
        return self


class OutlineJobRequest(SelectionRequest):
    source_run_id: str = Field(min_length=1, max_length=255)


class OutlineJobResponse(BaseModel):
    job_id: str
    kind: Literal["outline"] = "outline"
    status: JobStatus
    stage: str
    request: OutlineJobRequest
    run_id: str | None = None
    pipeline_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class NarrativeSectionRevision(BaseModel):
    section_id: str = Field(pattern=r"^[a-z0-9_-]+$")
    title: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=500)


class ScriptJobRequest(BaseModel):
    source_run_id: str = Field(min_length=1, max_length=255)
    selected_title: str = Field(min_length=1, max_length=120)
    sections: list[NarrativeSectionRevision] = Field(min_length=4, max_length=14)

    @model_validator(mode="after")
    def section_ids_are_unique(self) -> "ScriptJobRequest":
        ids = [section.section_id for section in self.sections]
        if len(set(ids)) != len(ids):
            raise ValueError("section IDs must be unique")
        return self


class ScriptJobResponse(BaseModel):
    job_id: str
    kind: Literal["script"] = "script"
    status: JobStatus
    stage: str
    request: ScriptJobRequest
    run_id: str | None = None
    pipeline_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ValidationJobRequest(BaseModel):
    source_run_id: str = Field(min_length=1, max_length=255)


class ValidationJobResponse(BaseModel):
    job_id: str
    kind: Literal["validation"] = "validation"
    status: JobStatus
    stage: str
    request: ValidationJobRequest
    run_id: str | None = None
    pipeline_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CitationRevisionJobRequest(BaseModel):
    source_run_id: str = Field(min_length=1, max_length=255)
    paragraph_ids: list[str] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def paragraph_ids_are_unique(self) -> "CitationRevisionJobRequest":
        if len(set(self.paragraph_ids)) != len(self.paragraph_ids):
            raise ValueError("paragraph_ids must be unique")
        return self


class CitationRevisionJobResponse(BaseModel):
    job_id: str
    kind: Literal["citation_revision"] = "citation_revision"
    status: JobStatus
    stage: str
    request: CitationRevisionJobRequest
    run_id: str | None = None
    pipeline_status: str | None = None
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


PipelineJobResponse = (
    ResearchJobResponse | OutlineJobResponse | ScriptJobResponse | ValidationJobResponse
    | CitationRevisionJobResponse
)


class ResearchJobListResponse(BaseModel):
    items: list[PipelineJobResponse]
    total: int = Field(ge=0)
