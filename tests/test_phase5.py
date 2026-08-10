import json
from pathlib import Path

import pytest

from app.agents.phase5 import generate_narrative, resolve_run_dir
from app.config import ProjectSettings, Settings
from app.schemas.narrative import NarrativePlan


class FakeNarrativeProvider:
    def parse(self, *, stage, instructions, input_text, output_type):
        assert stage == "narrative_architecture"
        assert output_type is NarrativePlan
        context = json.loads(input_text)
        assert len(context["selected_books"]) == 2
        return NarrativePlan.model_validate({
            "title_candidates": ["평가에서 자유로워지는 법", "인정 욕구의 뿌리", "나답게 사는 연습"],
            "core_message": "타인의 평가는 관계의 신호이지만 내 가치의 판결문은 아니다.",
            "emotional_arc": ["불안의 공감", "원인의 이해", "관점의 전환", "안도"],
            "sections": [
                {"section_id": "hook", "title": "평가가 두려운 순간", "narrative_function": "hook",
                 "purpose": "시청자의 경험에 접속한다.", "key_points": ["평가 불안을 질문으로 연다."],
                 "book_ids": [], "evidence_ids": [], "estimated_seconds": 50},
                {"section_id": "cause", "title": "인정 욕구의 원인", "narrative_function": "book_perspective",
                 "purpose": "심리적 원인을 이해한다.", "key_points": ["관계 욕구를 설명한다."],
                 "book_ids": ["book_1"], "evidence_ids": ["e_1"], "estimated_seconds": 100},
                {"section_id": "turn", "title": "철학적 전환", "narrative_function": "transition",
                 "purpose": "평가의 의미를 다시 본다.", "key_points": ["판단과 가치를 분리한다."],
                 "book_ids": ["book_2"], "evidence_ids": ["e_2"], "estimated_seconds": 100},
                {"section_id": "apply", "title": "나로 사는 연습", "narrative_function": "application",
                 "purpose": "일상에 적용한다.", "key_points": ["작은 선택을 제안한다."],
                 "book_ids": ["book_1", "book_2"], "evidence_ids": ["e_1", "e_2"],
                 "estimated_seconds": 100},
                {"section_id": "end", "title": "평가는 판결문이 아니다", "narrative_function": "conclusion",
                 "purpose": "안도와 여운을 남긴다.", "key_points": ["중심 메시지를 회수한다."],
                 "book_ids": [], "evidence_ids": [], "estimated_seconds": 50},
            ],
            "total_seconds": 400,
        })


class InvalidEvidenceProvider(FakeNarrativeProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        plan = super().parse(
            stage=stage, instructions=instructions, input_text=input_text, output_type=output_type,
        )
        sections = list(plan.sections)
        sections[1] = sections[1].model_copy(update={"evidence_ids": ["e_unknown"]})
        return plan.model_copy(update={"sections": sections})


class ShortsNarrativeProvider:
    def parse(self, *, stage, instructions, input_text, output_type):
        context = json.loads(input_text)
        assert context["request"]["content_format"] == "shorts"
        assert len(context["selected_books"]) == 1
        return NarrativePlan.model_validate({
            "title_candidates": ["불안할 때 펼칠 한 권", "타인의 시선에서 벗어나는 60초", "나를 지키는 책"],
            "core_message": "타인의 평가는 내 가치의 판결문이 아니다.",
            "emotional_arc": ["공감", "발견", "이해", "여운"],
            "sections": [
                {"section_id": "hook", "title": "혹시 평가가 두렵나요", "narrative_function": "hook",
                 "purpose": "생활 장면으로 질문을 연다.", "key_points": ["평가 불안을 묻는다."],
                 "book_ids": [], "evidence_ids": [], "estimated_seconds": 12},
                {"section_id": "intro", "title": "오늘의 한 권", "narrative_function": "book_intro",
                 "purpose": "책과 저자를 공개한다.", "key_points": ["책의 문제의식을 소개한다."],
                 "book_ids": ["book_1"], "evidence_ids": ["e_1"], "estimated_seconds": 18},
                {"section_id": "insight", "title": "핵심 통찰", "narrative_function": "book_perspective",
                 "purpose": "한 가지 관점을 설명한다.", "key_points": ["관계 욕구를 이해한다."],
                 "book_ids": ["book_1"], "evidence_ids": ["e_1"], "estimated_seconds": 35},
                {"section_id": "end", "title": "오늘의 한 문장", "narrative_function": "conclusion",
                 "purpose": "적용과 여운을 남긴다.", "key_points": ["내 기준을 선택한다."],
                 "book_ids": [], "evidence_ids": [], "estimated_seconds": 15},
            ],
            "total_seconds": 80,
        })


def _write_run(tmp_path: Path) -> tuple[Settings, str]:
    output_path = tmp_path / "outputs"
    run_id = "run_001"
    run_dir = output_path / run_id
    run_dir.mkdir(parents=True)
    artifacts = {
        "input.json": {"topic": "타인의 평가", "duration_minutes": 12, "target_book_count": 2,
                       "tone": "사색적", "audience": "일반 성인"},
        "topic_analysis.json": {"core_question": "평가에서 어떻게 자유로워지는가", "intent": "원인과 대안",
                                "subtopics": ["평가", "자존감"], "keywords": ["평가", "인정", "자존감"],
                                "search_queries": ["타인의 평가", "인정 욕구"]},
        "candidate_books.json": [
            {"book_id": "book_1", "title": "책 하나", "author": "저자 하나", "source_file": "책1.md",
             "score": 0.9, "chunk_count": 1, "evidence_chunk_ids": ["chunk_1"]},
            {"book_id": "book_2", "title": "책 둘", "author": "저자 둘", "source_file": "책2.md",
             "score": 0.8, "chunk_count": 1, "evidence_chunk_ids": ["chunk_2"]},
        ],
        "evidence.json": [
            {"evidence_id": "e_1", "book_id": "book_1", "type": "paraphrase", "claim": "관계 욕구가 있다.",
             "source_chunk_ids": ["chunk_1"], "confidence": 0.9},
            {"evidence_id": "e_2", "book_id": "book_2", "type": "interpretation", "claim": "가치는 분리된다.",
             "source_chunk_ids": ["chunk_2"], "confidence": 0.8},
        ],
        "selected_books.json": {"selected_books": [
            {"book_id": "book_1", "role": "원인", "selection_reason": "근거 충분"},
            {"book_id": "book_2", "role": "전환", "selection_reason": "근거 충분"},
        ], "excluded_books": [], "cross_book_connection": "원인에서 전환으로"},
    }
    for name, payload in artifacts.items():
        (run_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return Settings(project=ProjectSettings(output_path=output_path)), run_id


def _write_shorts_run(tmp_path: Path) -> tuple[Settings, str]:
    settings, run_id = _write_run(tmp_path)
    run_dir = settings.project.output_path / run_id
    payload = json.loads((run_dir / "input.json").read_text(encoding="utf-8"))
    payload.update({"content_format": "shorts", "duration_minutes": 1, "target_book_count": 1})
    (run_dir / "input.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    selection = {
        "selected_books": [{"book_id": "book_1", "role": "핵심 통찰", "selection_reason": "근거 충분"}],
        "excluded_books": [{"book_id": "book_2", "reason": "한 권 쇼츠 범위 밖"}],
        "cross_book_connection": "책 하나의 핵심 관점을 주제와 연결한다.",
    }
    (run_dir / "selected_books.json").write_text(json.dumps(selection, ensure_ascii=False), encoding="utf-8")
    return settings, run_id


def test_generate_narrative_preserves_evidence_and_normalizes_duration(tmp_path: Path) -> None:
    settings, run_id = _write_run(tmp_path)
    plan = generate_narrative(settings, run_id, structured=FakeNarrativeProvider())
    run_dir = settings.project.output_path / run_id
    assert plan.total_seconds == 720
    assert sum(item.estimated_seconds for item in plan.sections) == 720
    assert {evidence_id for item in plan.sections for evidence_id in item.evidence_ids} == {"e_1", "e_2"}
    assert (run_dir / "narrative.json").is_file()
    outline = (run_dir / "outline.md").read_text(encoding="utf-8")
    assert "책 하나" in outline
    assert "e_2" in outline
    assert "12분 0초" in outline


def test_generate_narrative_refuses_to_overwrite(tmp_path: Path) -> None:
    settings, run_id = _write_run(tmp_path)
    generate_narrative(settings, run_id, structured=FakeNarrativeProvider())
    with pytest.raises(FileExistsError):
        generate_narrative(settings, run_id, structured=FakeNarrativeProvider())


def test_generate_narrative_rejects_unknown_evidence_before_writing(tmp_path: Path) -> None:
    settings, run_id = _write_run(tmp_path)
    with pytest.raises(ValueError, match="Unknown evidence ID"):
        generate_narrative(settings, run_id, structured=InvalidEvidenceProvider())
    run_dir = settings.project.output_path / run_id
    assert not (run_dir / "narrative.json").exists()
    assert not (run_dir / "outline.md").exists()


def test_resolve_run_dir_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        resolve_run_dir(tmp_path / "outputs", "../outside")


def test_generate_shorts_narrative_uses_one_book_and_four_sections(tmp_path: Path) -> None:
    settings, run_id = _write_shorts_run(tmp_path)
    plan = generate_narrative(settings, run_id, structured=ShortsNarrativeProvider())

    assert plan.total_seconds == 60
    assert len(plan.sections) == 4
    assert plan.sections[1].narrative_function == "book_intro"
    assert sum(section.estimated_seconds for section in plan.sections) == 60
    outline = (settings.project.output_path / run_id / "outline.md").read_text(encoding="utf-8")
    assert "- 형식: 쇼츠" in outline
    assert "- 예상 길이: 1분 0초" in outline
