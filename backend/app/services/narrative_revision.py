"""Validated immutable narrative revisions before Phase 6 script generation."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime

from app.agents.phase5 import _read_json, render_outline_markdown, resolve_run_dir
from app.agents.phase6 import create_script_revision
from app.config import Settings
from app.schemas.evidence import BookSelection, CandidateBook
from app.schemas.narrative import NarrativePlan
from app.schemas.topic import TopicAnalysis, TopicRequest
from backend.app.schemas import ScriptJobRequest


def _revised_plan(settings: Settings, request: ScriptJobRequest) -> NarrativePlan:
    source = resolve_run_dir(settings.project.output_path, request.source_run_id)
    plan = NarrativePlan.model_validate(_read_json(source / "narrative.json"))
    source_by_id = {section.section_id: section for section in plan.sections}
    requested_ids = [section.section_id for section in request.sections]
    if set(requested_ids) != set(source_by_id):
        raise ValueError("구성안 리비전은 기존 섹션을 빠뜨리거나 새로 추가할 수 없습니다.")
    if not request.selected_title.strip():
        raise ValueError("확정 제목은 공백일 수 없습니다.")
    if any(not item.title.strip() or not item.purpose.strip() for item in request.sections):
        raise ValueError("섹션 제목과 목적은 공백일 수 없습니다.")
    revised_sections = [
        source_by_id[item.section_id].model_copy(update={
            "title": item.title.strip(), "purpose": item.purpose.strip(),
        })
        for item in request.sections
    ]
    if revised_sections[0].narrative_function != "hook":
        raise ValueError("도입 섹션은 항상 첫 번째여야 합니다.")
    if revised_sections[-1].narrative_function != "conclusion":
        raise ValueError("결론 섹션은 항상 마지막이어야 합니다.")
    return plan.model_copy(update={
        "selected_title": request.selected_title.strip(),
        "sections": revised_sections,
    })


def validate_script_job_request(settings: Settings, request: ScriptJobRequest) -> None:
    """Validate editable fields while keeping evidence-bearing fields immutable."""
    _revised_plan(settings, request)


def prepare_narrative_revision(settings: Settings, request: ScriptJobRequest) -> str:
    """Create a new run containing only a validated narrative revision."""
    plan = _revised_plan(settings, request)
    run_id = create_script_revision(settings, request.source_run_id)
    destination = resolve_run_dir(settings.project.output_path, run_id)
    try:
        topic_request = TopicRequest.model_validate(_read_json(destination / "input.json"))
        analysis = TopicAnalysis.model_validate(_read_json(destination / "topic_analysis.json"))
        candidates = [
            CandidateBook.model_validate(item)
            for item in _read_json(destination / "candidate_books.json")
        ]
        selection = BookSelection.model_validate(_read_json(destination / "selected_books.json"))
        (destination / "narrative.json").write_text(
            plan.model_dump_json(indent=2), encoding="utf-8"
        )
        (destination / "outline.md").write_text(
            render_outline_markdown(topic_request, analysis, plan, selection, candidates),
            encoding="utf-8",
        )
        manifest = {
            "source_run_id": request.source_run_id,
            "selected_title": plan.selected_title,
            "section_ids": [section.section_id for section in plan.sections],
            "created_at": datetime.now(UTC).isoformat(),
        }
        (destination / "narrative_revision.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        shutil.rmtree(destination)
        raise
    return run_id
