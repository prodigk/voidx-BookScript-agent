"""Phase 7 citation validation schemas."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

IssueCategory = Literal[
    "missing_source", "invalid_line_range", "modified_quotation", "unsupported_paraphrase",
    "mixed_book_attribution", "incorrect_title", "incorrect_author", "unsupported_causal_claim",
]


class ParsedScriptParagraph(BaseModel):
    paragraph_id: str
    section_id: str
    section_title: str
    text_type: Literal["quotation", "paraphrase", "interpretation", "transition", "example", "commentary"]
    text: str
    book_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)


class SourceReference(BaseModel):
    chunk_id: str
    book_id: str
    title: str
    author: str
    source_file: str
    heading_path: list[str]
    start_line: int
    end_line: int
    content_hash: str


class CitationAssessment(BaseModel):
    paragraph_id: str
    supported: bool
    confidence: float = Field(ge=0, le=1)
    issue_categories: list[IssueCategory] = Field(default_factory=list, max_length=3)
    explanation: Annotated[str, Field(min_length=1, max_length=500)]
    suggested_rewrite: str | None = Field(default=None, max_length=1000)


class CitationReview(BaseModel):
    assessments: list[CitationAssessment]


class ValidationIssue(BaseModel):
    issue_id: str
    severity: Literal["low", "medium", "high"]
    category: IssueCategory
    section_id: str
    paragraph_id: str
    description: str
    recommended_action: str
    source_chunk_ids: list[str] = Field(default_factory=list)


class CitationRecord(BaseModel):
    citation_id: str
    paragraph_id: str
    section_id: str
    text_type: str
    text: str
    book_ids: list[str]
    evidence_ids: list[str]
    sources: list[SourceReference]
    status: Literal["valid", "needs_review", "invalid"]
    confidence: float = Field(ge=0, le=1)
    review_summary: str


class CitationValidationResult(BaseModel):
    status: Literal["approved", "needs_revision"]
    citations: list[CitationRecord]
    issues: list[ValidationIssue]
    valid_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    invalid_count: int = Field(ge=0)
