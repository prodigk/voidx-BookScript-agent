"""Phase 5 narrative architecture and outline generation."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.llm.prompt_loader import load_prompt
from app.llm.structured import OpenAIStructuredProvider, StructuredProvider
from app.schemas.evidence import BookSelection, CandidateBook, EvidenceItem
from app.schemas.insight import EditorialStrategy
from app.schemas.narrative import NarrativePlan
from app.schemas.topic import TopicAnalysis, TopicRequest


def _read_json(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required Phase 4 artifact not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_run_dir(output_root: Path, run_id: str) -> Path:
    root = output_root.resolve()
    run_dir = (root / run_id).resolve()
    if run_dir.parent != root:
        raise ValueError("Invalid run ID path")
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run not found: {run_id}")
    return run_dir


def _normalize_duration(plan: NarrativePlan, target_seconds: int) -> NarrativePlan:
    current = sum(section.estimated_seconds for section in plan.sections)
    if current <= 0:
        raise ValueError("Narrative duration must be positive")
    scaled = [max(15, round(section.estimated_seconds * target_seconds / current)) for section in plan.sections]
    difference = target_seconds - sum(scaled)
    order = sorted(range(len(scaled)), key=lambda index: scaled[index], reverse=True)
    while difference != 0:
        changed = False
        for index in order:
            step = 1 if difference > 0 else -1
            if scaled[index] + step < 15:
                continue
            scaled[index] += step
            difference -= step
            changed = True
            if difference == 0:
                break
        if not changed:
            raise ValueError("Could not normalize narrative duration")
    sections = [section.model_copy(update={"estimated_seconds": seconds}) for section, seconds in zip(plan.sections, scaled, strict=True)]
    return plan.model_copy(update={"sections": sections, "total_seconds": target_seconds})


def _validate_plan(
    plan: NarrativePlan,
    selected: BookSelection,
    evidence: list[EvidenceItem],
) -> None:
    selected_ids = {item.book_id for item in selected.selected_books}
    evidence_by_id = {item.evidence_id: item for item in evidence}
    seen_books: set[str] = set()
    functions = {section.narrative_function for section in plan.sections}
    if not {"hook", "conclusion"} <= functions:
        raise ValueError("Narrative must contain hook and conclusion sections")
    if len({section.section_id for section in plan.sections}) != len(plan.sections):
        raise ValueError("Narrative section IDs must be unique")
    for section in plan.sections:
        if not set(section.book_ids) <= selected_ids:
            raise ValueError(f"Unknown book ID in section: {section.section_id}")
        if not set(section.evidence_ids) <= evidence_by_id.keys():
            raise ValueError(f"Unknown evidence ID in section: {section.section_id}")
        evidence_books = {evidence_by_id[item].book_id for item in section.evidence_ids}
        if not evidence_books <= set(section.book_ids):
            raise ValueError(f"Evidence/book attribution mismatch: {section.section_id}")
        if section.book_ids and not section.evidence_ids:
            raise ValueError(f"Book section has no evidence: {section.section_id}")
        seen_books.update(section.book_ids)
    if seen_books != selected_ids:
        raise ValueError("Every selected book must appear in the narrative")


def render_outline_markdown(
    request: TopicRequest,
    analysis: TopicAnalysis,
    plan: NarrativePlan,
    selected: BookSelection,
    candidates: list[CandidateBook],
) -> str:
    books = {item.book_id: item for item in candidates}
    selected_roles = {item.book_id: item for item in selected.selected_books}
    lines = [
        "# 영상 구성안", "", "## 기본 정보",
        f"- 주제: {request.topic}", f"- 예상 길이: {plan.total_seconds // 60}분 {plan.total_seconds % 60}초",
        f"- 대상: {request.audience}", f"- 톤: {request.tone}", "", "## 핵심 질문", analysis.core_question,
        "", "## 중심 메시지", plan.core_message,
        "", "## 확정 제목", plan.selected_title or "미확정",
        "", "## 제목 후보",
    ]
    lines.extend(f"- {title}" for title in plan.title_candidates)
    lines += ["", "## 감정 흐름", " → ".join(plan.emotional_arc), "", "## 선정 도서"]
    for book_id, selected_book in selected_roles.items():
        book = books[book_id]
        lines.append(f"- {book.title}: {selected_book.role}")
    lines += ["", "## 섹션"]
    elapsed = 0
    for index, section in enumerate(plan.sections, start=1):
        start, end = elapsed, elapsed + section.estimated_seconds
        elapsed = end
        lines += [
            "", f"### {index}. {section.title}",
            f"- 시간: {start // 60:02d}:{start % 60:02d}–{end // 60:02d}:{end % 60:02d}",
            f"- 기능: {section.narrative_function}", f"- 목적: {section.purpose}",
        ]
        if section.book_ids:
            lines.append("- 도서: " + ", ".join(books[item].title for item in section.book_ids))
        if section.evidence_ids:
            lines.append("- 근거: " + ", ".join(section.evidence_ids))
        lines.append("- 핵심 포인트:")
        lines.extend(f"  - {point}" for point in section.key_points)
    return "\n".join(lines) + "\n"


def generate_narrative(
    settings: Settings,
    run_id: str,
    *,
    structured: StructuredProvider | None = None,
) -> NarrativePlan:
    """Generate and validate narrative artifacts for a completed Phase 4 run."""
    run_dir = resolve_run_dir(settings.project.output_path, run_id)
    narrative_path, outline_path = run_dir / "narrative.json", run_dir / "outline.md"
    if narrative_path.exists() or outline_path.exists():
        raise FileExistsError("Narrative artifacts already exist; refusing to overwrite the run")
    request = TopicRequest.model_validate(_read_json(run_dir / "input.json"))
    analysis = TopicAnalysis.model_validate(_read_json(run_dir / "topic_analysis.json"))
    candidates = [CandidateBook.model_validate(item) for item in _read_json(run_dir / "candidate_books.json")]
    evidence = [EvidenceItem.model_validate(item) for item in _read_json(run_dir / "evidence.json")]
    selected = BookSelection.model_validate(_read_json(run_dir / "selected_books.json"))
    strategy_data = _read_json(run_dir / "editorial_strategy.json") if (run_dir / "editorial_strategy.json").is_file() else None
    editorial_strategy = EditorialStrategy.model_validate(strategy_data) if strategy_data and "profile" in strategy_data else None
    candidate_by_id = {item.book_id: item for item in candidates}
    selected_ids = {item.book_id for item in selected.selected_books}
    if not selected_ids <= candidate_by_id.keys():
        raise ValueError("Selected book is missing from candidate artifacts")
    relevant_evidence = [item for item in evidence if item.book_id in selected_ids]
    context = {
        "request": request.model_dump(mode="json"),
        "topic_analysis": analysis.model_dump(mode="json"),
        "selected_books": [
            {**item.model_dump(mode="json"), "title": candidate_by_id[item.book_id].title}
            for item in selected.selected_books
        ],
        "cross_book_connection": selected.cross_book_connection,
        "evidence": [item.model_dump(mode="json") for item in relevant_evidence],
        "editorial_strategy": editorial_strategy.model_dump(mode="json") if editorial_strategy else None,
    }
    structured = structured or OpenAIStructuredProvider(settings.llm)
    plan = structured.parse(
        stage="narrative_architecture", instructions=load_prompt("narrative_architect"),
        input_text=json.dumps(context, ensure_ascii=False), output_type=NarrativePlan,
    )
    plan = _normalize_duration(plan, request.duration_minutes * 60)
    _validate_plan(plan, selected, relevant_evidence)
    narrative_path.write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    outline_path.write_text(render_outline_markdown(request, analysis, plan, selected, candidates), encoding="utf-8")
    return plan
