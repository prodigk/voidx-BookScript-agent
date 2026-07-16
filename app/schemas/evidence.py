"""Candidate ranking, evidence, and selection schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.topic import TopicAnalysis

ConciseText = Annotated[str, Field(min_length=1, max_length=400)]


class CandidateBook(BaseModel):
    book_id: str
    title: str
    author: str
    source_file: str
    score: float
    chunk_count: int
    evidence_chunk_ids: list[str]
    retrieval_score: float | None = None
    topic_fit_score: float | None = None
    editorial_fit_score: float | None = None
    emotional_fit_score: float | None = None
    perspective: str | None = None
    inclusion_reason: str | None = None


class CandidateFit(BaseModel):
    book_id: str
    include: bool
    topic_fit_score: float = Field(ge=0, le=1)
    editorial_fit_score: float = Field(ge=0, le=1)
    emotional_fit_score: float = Field(ge=0, le=1)
    perspective: Annotated[str, Field(min_length=1, max_length=100)]
    reason: ConciseText
    exclusion_reason: str | None = Field(default=None, max_length=400)


class CandidateScreening(BaseModel):
    candidates: list[CandidateFit]


class EvidenceItem(BaseModel):
    evidence_id: str
    book_id: str
    type: Literal["quotation", "paraphrase", "interpretation"]
    claim: ConciseText
    source_chunk_ids: list[str] = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class BookAssessment(BaseModel):
    book_id: str
    relevance_reason: ConciseText
    suggested_role: Annotated[str, Field(min_length=1, max_length=100)]
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=5)


class EvidenceCuration(BaseModel):
    assessments: list[BookAssessment]


class SelectedBook(BaseModel):
    book_id: str
    role: Annotated[str, Field(min_length=1, max_length=100)]
    selection_reason: ConciseText


class ExcludedBook(BaseModel):
    book_id: str
    reason: ConciseText


class BookSelection(BaseModel):
    selected_books: list[SelectedBook] = Field(min_length=2, max_length=4)
    excluded_books: list[ExcludedBook] = Field(default_factory=list)
    cross_book_connection: ConciseText


class Phase4Result(BaseModel):
    status: Literal["complete", "insufficient_evidence"]
    run_id: str
    message: str | None = None
    topic_analysis: TopicAnalysis
    candidate_books: list[CandidateBook]
    evidence: list[EvidenceItem]
    selection: BookSelection | None = None
