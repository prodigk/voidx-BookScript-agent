"""Immutable user book selection revisions for Phase 5 generation."""

from __future__ import annotations

import json
import re
import shutil
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.schemas.evidence import (
    BookSelection,
    CandidateBook,
    EvidenceItem,
    ExcludedBook,
    SelectedBook,
)
from app.schemas.topic import TopicRequest
from backend.app.schemas import OutlineJobRequest
from backend.app.services.runs import resolve_artifact

PHASE4_INPUT_ARTIFACTS = (
    "input.json",
    "topic_analysis.json",
    "search_results.json",
    "candidate_screening.json",
    "candidate_books.json",
    "evidence.json",
    "editorial_strategy.json",
    "insight_sources.json",
)


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed generated artifact: {path.name}") from exc


def _source_artifact(settings: Settings, run_id: str, name: str) -> Path:
    path, _ = resolve_artifact(settings.project.output_path, run_id, name)
    return path


def validate_outline_request(settings: Settings, request: OutlineJobRequest) -> None:
    """Validate candidate membership and minimum supporting evidence before queueing."""
    candidate_path = _source_artifact(settings, request.source_run_id, "candidate_books.json")
    evidence_path = _source_artifact(settings, request.source_run_id, "evidence.json")
    candidates = [CandidateBook.model_validate(item) for item in _read_json(candidate_path)]
    evidence = [EvidenceItem.model_validate(item) for item in _read_json(evidence_path)]
    candidate_ids = {candidate.book_id for candidate in candidates}
    unknown = [book_id for book_id in request.selected_book_ids if book_id not in candidate_ids]
    if unknown:
        raise ValueError("후보 도서에 없는 ID가 포함되어 있습니다: " + ", ".join(unknown))
    supported = {item.book_id for item in evidence if item.confidence >= 0.5}
    unsupported = [book_id for book_id in request.selected_book_ids if book_id not in supported]
    if unsupported:
        raise ValueError("신뢰도 0.5 이상의 근거가 없는 도서는 선택할 수 없습니다: " + ", ".join(unsupported))


def _slug(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z가-힣]+", "-", value).strip("-")
    return normalized[:60] or "selection"


def _new_run_dir(output_root: Path, topic: str) -> Path:
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    base = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{_slug(topic)}-selection-revision"
    run_dir = root / base
    suffix = 1
    while run_dir.exists():
        run_dir = root / f"{base}-{suffix}"
        suffix += 1
    run_dir.mkdir()
    return run_dir


def prepare_selection_revision(settings: Settings, request: OutlineJobRequest) -> str:
    """Create a new immutable Phase 4 run with the user's ordered final selection."""
    validate_outline_request(settings, request)
    input_path = _source_artifact(settings, request.source_run_id, "input.json")
    candidate_path = _source_artifact(settings, request.source_run_id, "candidate_books.json")
    input_data = TopicRequest.model_validate(_read_json(input_path))
    candidates = [CandidateBook.model_validate(item) for item in _read_json(candidate_path)]
    candidate_by_id = {item.book_id: item for item in candidates}

    original_selection: BookSelection | None = None
    try:
        selection_path = _source_artifact(settings, request.source_run_id, "selected_books.json")
        original_selection = BookSelection.model_validate(_read_json(selection_path))
    except (FileNotFoundError, ValueError):
        pass
    original_selected = {
        item.book_id: item for item in original_selection.selected_books
    } if original_selection else {}
    original_excluded = {
        item.book_id: item for item in original_selection.excluded_books
    } if original_selection else {}

    selected: list[SelectedBook] = []
    for book_id in request.selected_book_ids:
        candidate = candidate_by_id[book_id]
        prior = original_selected.get(book_id)
        selected.append(SelectedBook(
            book_id=book_id,
            role=prior.role if prior else candidate.perspective or "주제의 핵심 관점",
            selection_reason=(
                prior.selection_reason if prior
                else candidate.inclusion_reason or "사용자가 최종 도서로 선택함"
            ),
        ))
    excluded = [
        ExcludedBook(
            book_id=candidate.book_id,
            reason=(
                original_excluded[candidate.book_id].reason
                if candidate.book_id in original_excluded
                else "사용자가 최종 선택에서 제외함"
            ),
        )
        for candidate in candidates
        if candidate.book_id not in request.selected_book_ids
    ]
    titles = [candidate_by_id[book_id].title for book_id in request.selected_book_ids]
    selection = BookSelection(
        selected_books=selected,
        excluded_books=excluded,
        cross_book_connection=(
            "사용자가 지정한 순서에 따라 " + " → ".join(titles) + "의 관점을 연결한다."
        ),
    )

    run_dir = _new_run_dir(settings.project.output_path, input_data.topic)
    try:
        for name in PHASE4_INPUT_ARTIFACTS:
            try:
                source = _source_artifact(settings, request.source_run_id, name)
            except FileNotFoundError:
                continue
            shutil.copy2(source, run_dir / name)
        revised_input = input_data.model_copy(
            update={"target_book_count": len(request.selected_book_ids)}
        )
        (run_dir / "input.json").write_text(
            revised_input.model_dump_json(indent=2), encoding="utf-8"
        )
        (run_dir / "selected_books.json").write_text(
            selection.model_dump_json(indent=2), encoding="utf-8"
        )
        manifest = {
            "source_run_id": request.source_run_id,
            "selected_book_ids": request.selected_book_ids,
            "created_at": datetime.now(UTC).isoformat(),
        }
        (run_dir / "selection_revision.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(run_dir)
        raise
    return run_dir.name
