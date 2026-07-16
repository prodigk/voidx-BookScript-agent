import json
from pathlib import Path

import pytest

from app.config import ProjectSettings, Settings
from backend.app.schemas import NarrativeSectionRevision, ScriptJobRequest
from backend.app.services.narrative_revision import (
    prepare_narrative_revision,
    validate_script_job_request,
)


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _fixture(tmp_path: Path) -> tuple[Settings, list[dict[str, object]]]:
    run = tmp_path / "outputs" / "outline_run"
    run.mkdir(parents=True)
    sections = [
        {"section_id": "hook", "title": "도입", "narrative_function": "hook", "purpose": "공감", "key_points": ["질문"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 60},
        {"section_id": "problem", "title": "문제", "narrative_function": "problem", "purpose": "원인", "key_points": ["원인"], "book_ids": ["a"], "evidence_ids": ["ea"], "estimated_seconds": 120},
        {"section_id": "perspective", "title": "관점", "narrative_function": "book_perspective", "purpose": "대안", "key_points": ["대안"], "book_ids": ["b"], "evidence_ids": ["eb"], "estimated_seconds": 120},
        {"section_id": "integration", "title": "통합", "narrative_function": "integration", "purpose": "통합", "key_points": ["연결"], "book_ids": ["a", "b"], "evidence_ids": ["ea", "eb"], "estimated_seconds": 120},
        {"section_id": "conclusion", "title": "결론", "narrative_function": "conclusion", "purpose": "여운", "key_points": ["질문"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 60},
    ]
    _write(run / "input.json", {"topic": "일과 자아", "duration_minutes": 8, "target_book_count": 2})
    _write(run / "topic_analysis.json", {"core_question": "일은 나인가", "intent": "거리 찾기", "subtopics": ["일", "자아"], "keywords": ["일", "자아", "거리"], "search_queries": ["일 자아", "직업 정체성"]})
    _write(run / "candidate_books.json", [
        {"book_id": "a", "title": "일의 철학", "author": "저자 A", "source_file": "a.md", "score": .9, "chunk_count": 1, "evidence_chunk_ids": ["ca"]},
        {"book_id": "b", "title": "회복의 기술", "author": "저자 B", "source_file": "b.md", "score": .8, "chunk_count": 1, "evidence_chunk_ids": ["cb"]},
    ])
    _write(run / "selected_books.json", {"selected_books": [{"book_id": "a", "role": "문제", "selection_reason": "근거"}, {"book_id": "b", "role": "대안", "selection_reason": "근거"}], "excluded_books": [], "cross_book_connection": "문제에서 대안으로"})
    _write(run / "evidence.json", [{"evidence_id": "ea", "book_id": "a", "type": "paraphrase", "claim": "일과 자아", "source_chunk_ids": ["ca"], "confidence": .9}, {"evidence_id": "eb", "book_id": "b", "type": "quotation", "claim": "회복", "source_chunk_ids": ["cb"], "confidence": .9}])
    _write(run / "narrative.json", {"title_candidates": ["제목 1", "제목 2", "제목 3"], "core_message": "일은 전부가 아니다", "emotional_arc": ["압박", "이해", "안도"], "sections": sections, "total_seconds": 480})
    (run / "outline.md").write_text("# 기존 구성안", encoding="utf-8")
    return Settings(project=ProjectSettings(output_path=tmp_path / "outputs")), sections


def _request(sections: list[dict[str, object]]) -> ScriptJobRequest:
    return ScriptJobRequest(
        source_run_id="outline_run", selected_title="일에서 나를 되찾는 법",
        sections=[NarrativeSectionRevision(
            section_id=str(item["section_id"]), title=str(item["title"]), purpose=str(item["purpose"]),
        ) for item in sections],
    )


def test_creates_narrative_revision_without_changing_evidence_links(tmp_path: Path) -> None:
    settings, sections = _fixture(tmp_path)
    sections[1]["title"] = "일이 자아가 될 때"
    sections[1]["purpose"] = "성과와 정체성의 결합을 설명한다"
    request = _request(sections)
    run_id = prepare_narrative_revision(settings, request)
    revised = settings.project.output_path / run_id
    narrative = json.loads((revised / "narrative.json").read_text(encoding="utf-8"))
    manifest = json.loads((revised / "narrative_revision.json").read_text(encoding="utf-8"))
    assert narrative["selected_title"] == "일에서 나를 되찾는 법"
    assert narrative["sections"][1]["title"] == "일이 자아가 될 때"
    assert narrative["sections"][1]["evidence_ids"] == ["ea"]
    assert manifest["source_run_id"] == "outline_run"
    assert "## 확정 제목\n일에서 나를 되찾는 법" in (revised / "outline.md").read_text(encoding="utf-8")
    assert json.loads((settings.project.output_path / "outline_run" / "narrative.json").read_text(encoding="utf-8")).get("selected_title") is None


def test_rejects_missing_section_and_conclusion_reorder(tmp_path: Path) -> None:
    settings, sections = _fixture(tmp_path)
    missing = [dict(item) for item in sections]
    missing[2]["section_id"] = "unknown"
    with pytest.raises(ValueError, match="빠뜨리거나"):
        validate_script_job_request(settings, _request(missing))
    sections[-1], sections[-2] = sections[-2], sections[-1]
    with pytest.raises(ValueError, match="결론 섹션"):
        validate_script_job_request(settings, _request(sections))
