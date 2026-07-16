"""Search evaluation dataset and result models."""

from pydantic import BaseModel, Field


class ExpectedBook(BaseModel):
    label: str
    source_contains: str


class EvaluationCase(BaseModel):
    topic: str
    query: str
    expected_books: list[ExpectedBook] = Field(min_length=1)
    needs_review: bool = True


class EvaluationDataset(BaseModel):
    cases: list[EvaluationCase] = Field(min_length=1)


class CaseResult(BaseModel):
    topic: str
    query: str
    recall_at_5: float
    recall_at_10: float
    matched_at_5: list[str]
    matched_at_10: list[str]
    missing_at_10: list[str]
    returned_titles: list[str]
    needs_review: bool


class EvaluationResult(BaseModel):
    case_count: int
    mean_recall_at_5: float
    mean_recall_at_10: float
    cases_with_no_results: int
    cases: list[CaseResult]
