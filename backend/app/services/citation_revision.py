"""Preflight validation for targeted citation revision jobs."""

from app.agents.phase5 import _read_json, resolve_run_dir
from app.agents.phase7 import TARGETED_REWRITE_CATEGORIES
from app.config import Settings
from app.schemas.validation import CitationValidationResult
from backend.app.schemas import CitationRevisionJobRequest


def validate_citation_revision_request(
    settings: Settings,
    request: CitationRevisionJobRequest,
) -> None:
    """Allow only selected paragraphs with high-severity validation issues."""
    run = resolve_run_dir(settings.project.output_path, request.source_run_id)
    citations_path = run / "citations.json"
    if not citations_path.is_file():
        raise ValueError("부분 재작성에 필요한 검증 결과가 없습니다.")
    raw_result = _read_json(citations_path)
    if raw_result.get("status") != "needs_revision":
        raise ValueError("수정이 필요한 검증 실행만 부분 재작성할 수 있습니다.")
    result = CitationValidationResult.model_validate(raw_result)
    eligible = {
        issue.paragraph_id
        for issue in result.issues
        if issue.severity == "high" and issue.category in TARGETED_REWRITE_CATEGORIES
    }
    unavailable = set(request.paragraph_ids) - eligible
    if unavailable:
        raise ValueError(
            "선택한 문단에 재작성 가능한 고위험 이슈가 없습니다: "
            + ", ".join(sorted(unavailable))
        )
