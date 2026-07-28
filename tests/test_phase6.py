import json
from pathlib import Path

import pytest

from app.agents.phase6 import _verified_quote_text, create_script_revision, generate_script
from app.config import ProjectSettings, ScriptSettings, Settings
from app.schemas.evidence import EvidenceItem
from app.schemas.script import ScriptDocument


class FakeScriptProvider:
    def parse(self, *, stage, instructions, input_text, output_type):
        assert stage == "script_writer"
        assert output_type is ScriptDocument
        context = json.loads(input_text)
        repeated = "타인의 평가를 의식하는 마음을 이해하고 자기 기준을 천천히 찾아갑니다. " * 6
        paragraphs = [
            ("commentary", [], []),
            ("quotation", ["book_1"], ["e_1"]),
            ("quotation", ["book_2"], ["e_2"]),
            ("interpretation", ["book_1", "book_2"], ["e_1", "e_2"]),
            ("commentary", [], []),
        ]
        sections = []
        for index, (section, paragraph_data) in enumerate(zip(context["narrative"]["sections"], paragraphs, strict=True), 1):
            text_type, book_ids, evidence_ids = paragraph_data
            quote_text = {2: "사회적 반응에 관한 원문", 3: "자기 기준에 관한 원문"}.get(index)
            sections.append({
                "section_id": section["section_id"], "title": section["title"],
                "estimated_seconds": section["estimated_seconds"],
                "remotion_cue": {"visual_intent": f"장면 {index}",
                                  "scene_type": "quote_card" if quote_text else "standard",
                                  "quote_text": quote_text,
                                  "quote_evidence_id": evidence_ids[0] if quote_text else None,
                                  "quote_duration_seconds": 8 if quote_text else None,
                                  "on_screen_text": [section["title"]], "suggested_assets": ["차분한 추상 배경"]},
                "paragraphs": [{"paragraph_id": f"p_{index}", "text_type": text_type, "text": repeated,
                                "book_ids": book_ids, "evidence_ids": evidence_ids}],
            })
            if quote_text:
                sections[-1]["paragraphs"][0]["text"] = quote_text
        return ScriptDocument(title="평가에서 나를 되찾는 법", target_duration_seconds=720, sections=sections)


class InvalidAttributionProvider(FakeScriptProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        script = super().parse(stage=stage, instructions=instructions, input_text=input_text, output_type=output_type)
        sections = list(script.sections)
        paragraphs = list(sections[1].paragraphs)
        paragraphs[0] = paragraphs[0].model_copy(update={"evidence_ids": ["e_2"]})
        sections[1] = sections[1].model_copy(update={"paragraphs": paragraphs})
        return script.model_copy(update={"sections": sections})


class RepairingAttributionProvider(InvalidAttributionProvider):
    def __init__(self) -> None:
        self.calls = 0

    def parse(self, *, stage, instructions, input_text, output_type):
        self.calls += 1
        context = json.loads(input_text)
        assert context["section_evidence_contract"][1] == {
            "section_id": "s2",
            "allowed_book_ids": ["book_1"],
            "required_evidence_ids": ["e_1"],
        }
        if self.calls == 1:
            assert context["validation_feedback"] is None
            return super().parse(
                stage=stage, instructions=instructions,
                input_text=input_text, output_type=output_type,
            )
        feedback = context["validation_feedback"]
        assert feedback["error"] == "Invalid evidence attribution: p_2"
        assert feedback["invalid_section"]["section_id"] == "s2"
        assert [item["evidence_id"] for item in feedback["allowed_section_evidence"]] == ["e_1"]
        return FakeScriptProvider.parse(
            self, stage=stage, instructions=instructions,
            input_text=input_text, output_type=output_type,
        )


class InexactQuotationProvider(FakeScriptProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        script = super().parse(stage=stage, instructions=instructions, input_text=input_text, output_type=output_type)
        sections = list(script.sections)
        paragraphs = list(sections[1].paragraphs)
        paragraphs[0] = paragraphs[0].model_copy(update={"text": "모델이 바꾼 부정확한 인용"})
        cue = sections[1].remotion_cue.model_copy(update={"quote_text": "모델이 바꾼 부정확한 인용"})
        sections[1] = sections[1].model_copy(update={"paragraphs": paragraphs, "remotion_cue": cue})
        return script.model_copy(update={"sections": sections})


class ExposedTitleProvider(FakeScriptProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        script = super().parse(stage=stage, instructions=instructions, input_text=input_text, output_type=output_type)
        sections = list(script.sections)
        paragraphs = list(sections[0].paragraphs)
        paragraphs[0] = paragraphs[0].model_copy(update={"text": paragraphs[0].text + " 책 하나를 소개합니다."})
        sections[0] = sections[0].model_copy(update={"paragraphs": paragraphs})
        return script.model_copy(update={"sections": sections})


class MissingQuoteCardProvider(FakeScriptProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        script = super().parse(stage=stage, instructions=instructions, input_text=input_text, output_type=output_type)
        sections = []
        for section in script.sections:
            paragraphs = [
                paragraph.model_copy(update={"text_type": "paraphrase"})
                if paragraph.text_type == "quotation" else paragraph
                for paragraph in section.paragraphs
            ]
            cue = section.remotion_cue.model_copy(update={
                "scene_type": "standard", "quote_text": None,
                "quote_evidence_id": None, "quote_duration_seconds": None,
            })
            sections.append(section.model_copy(update={"paragraphs": paragraphs, "remotion_cue": cue}))
        return script.model_copy(update={"sections": sections})


def _write_run(tmp_path: Path) -> tuple[Settings, str, list[dict[str, object]]]:
    output_path, run_id = tmp_path / "outputs", "run_001"
    run_dir = output_path / run_id
    run_dir.mkdir(parents=True)
    sections = [
        {"section_id": "s1", "title": "도입", "narrative_function": "hook", "purpose": "공감",
         "key_points": ["질문"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 100},
        {"section_id": "s2", "title": "원인", "narrative_function": "problem", "purpose": "원인",
         "key_points": ["심리"], "book_ids": ["book_1"], "evidence_ids": ["e_1"], "estimated_seconds": 160},
        {"section_id": "s3", "title": "전환", "narrative_function": "transition", "purpose": "관점",
         "key_points": ["철학"], "book_ids": ["book_2"], "evidence_ids": ["e_2"], "estimated_seconds": 160},
        {"section_id": "s4", "title": "통합", "narrative_function": "integration", "purpose": "통합",
         "key_points": ["연결"], "book_ids": ["book_1", "book_2"], "evidence_ids": ["e_1", "e_2"],
         "estimated_seconds": 200},
        {"section_id": "s5", "title": "결론", "narrative_function": "conclusion", "purpose": "위로",
         "key_points": ["여운"], "book_ids": [], "evidence_ids": [], "estimated_seconds": 100},
    ]
    artifacts = {
        "input.json": {"topic": "타인의 평가", "duration_minutes": 12, "target_book_count": 2},
        "narrative.json": {"title_candidates": ["제목1", "제목2", "제목3"], "core_message": "자기 기준",
                           "emotional_arc": ["불안", "이해", "위로"], "sections": sections,
                           "total_seconds": 720},
        "candidate_books.json": [
            {"book_id": "book_1", "title": "책 하나", "author": "저자 하나", "source_file": "책1.md",
             "score": 0.9, "chunk_count": 1, "evidence_chunk_ids": ["chunk_1"]},
            {"book_id": "book_2", "title": "책 둘", "author": "저자 둘", "source_file": "책2.md",
             "score": 0.8, "chunk_count": 1, "evidence_chunk_ids": ["chunk_2"]},
        ],
        "selected_books.json": {"selected_books": [
            {"book_id": "book_1", "role": "원인", "selection_reason": "근거"},
            {"book_id": "book_2", "role": "전환", "selection_reason": "근거"},
        ], "excluded_books": [], "cross_book_connection": "원인과 전환"},
        "evidence.json": [
            {"evidence_id": "e_1", "book_id": "book_1", "type": "quotation", "claim": "사회적 반응",
             "source_chunk_ids": ["chunk_1"], "confidence": 0.9},
            {"evidence_id": "e_2", "book_id": "book_2", "type": "quotation", "claim": "자기 기준",
             "source_chunk_ids": ["chunk_2"], "confidence": 0.9},
        ],
    }
    for name, payload in artifacts.items():
        (run_dir / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(output_path=output_path),
        script=ScriptSettings(characters_per_minute=100, length_tolerance=0.75),
    )
    chunks = [
        {"chunk_id": "chunk_1", "book_id": "book_1", "content": "사회적 반응에 관한 원문",
         "source_file": "책1.md", "start_line": 10, "end_line": 12},
        {"chunk_id": "chunk_2", "book_id": "book_2", "content": "자기 기준에 관한 원문",
         "source_file": "책2.md", "start_line": 20, "end_line": 22},
    ]
    return settings, run_id, chunks


def test_generate_script_writes_internal_and_clean_outputs(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    script = generate_script(settings, run_id, structured=FakeScriptProvider(), source_chunks=chunks)
    run_dir = settings.project.output_path / run_id
    assert len(script.sections) == 5
    sourced = (run_dir / "script_with_sources.md").read_text(encoding="utf-8")
    clean = (run_dir / "script.md").read_text(encoding="utf-8")
    assert "[SOURCE:e_1]" in sourced
    assert "[CHUNK:chunk_2]" in sourced
    assert "<!-- REMOTION:" in sourced
    assert sourced.count("<!-- QUOTE_SCENE:") == 2
    assert "영상 렌더러: remotion" in sourced
    assert "[SOURCE:" not in clean
    assert "REMOTION" not in clean
    assert clean.rstrip().endswith("이 영상은 『책 하나』와 『책 둘』의 내용을 바탕으로 구성되었습니다.")


def test_generate_script_rejects_invalid_section_attribution(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    with pytest.raises(ValueError, match="Invalid evidence attribution"):
        generate_script(settings, run_id, structured=InvalidAttributionProvider(), source_chunks=chunks)
    assert not (settings.project.output_path / run_id / "script.md").exists()


def test_generate_script_retries_with_bounded_attribution_feedback(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    provider = RepairingAttributionProvider()
    script = generate_script(settings, run_id, structured=provider, source_chunks=chunks)
    assert provider.calls == 2
    assert script.sections[1].paragraphs[0].evidence_ids == ["e_1"]
    assert (settings.project.output_path / run_id / "script.md").is_file()


def test_generate_script_repairs_quotation_from_exact_evidence(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    generate_script(settings, run_id, structured=InexactQuotationProvider(), source_chunks=chunks)
    sourced = (settings.project.output_path / run_id / "script_with_sources.md").read_text(encoding="utf-8")
    assert "<!-- QUOTE_TEXT: 사회적 반응 -->" in sourced
    assert "모델이 바꾼 부정확한 인용" not in sourced


def test_generate_script_inserts_verified_quote_card_when_model_omits_it(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    generate_script(settings, run_id, structured=MissingQuoteCardProvider(), source_chunks=chunks)
    sourced = (settings.project.output_path / run_id / "script_with_sources.md").read_text(encoding="utf-8")
    assert sourced.count("<!-- QUOTE_SCENE:") == 1
    assert "<!-- QUOTE_TEXT: 사회적 반응 -->" in sourced


def test_verified_quote_uses_exact_source_wording_for_near_match() -> None:
    evidence = EvidenceItem(
        evidence_id="e_1", book_id="book_1", type="quotation",
        claim="번아웃은 정체성 상실을 수반하는 신체적·정서적 피로 상태다.",
        source_chunk_ids=["chunk_1"], confidence=0.9,
    )
    exact = "'번아웃은 정체성 상실을 수반하는 신체적, 정서적 피로 상태다.'"
    source = {"chunk_1": {"content": f"도입 문장\n{exact}\n다음 문장"}}
    assert _verified_quote_text(evidence, source) == exact


def test_generate_script_rejects_book_title_in_narration(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    with pytest.raises(ValueError, match="Book title/author exposed"):
        generate_script(settings, run_id, structured=ExposedTitleProvider(), source_chunks=chunks)


def test_generate_script_refuses_to_overwrite(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    generate_script(settings, run_id, structured=FakeScriptProvider(), source_chunks=chunks)
    with pytest.raises(FileExistsError):
        generate_script(settings, run_id, structured=FakeScriptProvider(), source_chunks=chunks)


def test_generate_script_uses_user_selected_narrative_title(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    narrative_path = settings.project.output_path / run_id / "narrative.json"
    narrative = json.loads(narrative_path.read_text(encoding="utf-8"))
    narrative["selected_title"] = "사용자가 확정한 제목"
    narrative_path.write_text(json.dumps(narrative, ensure_ascii=False), encoding="utf-8")
    script = generate_script(settings, run_id, structured=FakeScriptProvider(), source_chunks=chunks)
    assert script.title == "사용자가 확정한 제목"
    assert (settings.project.output_path / run_id / "script.md").read_text(encoding="utf-8").startswith("# 사용자가 확정한 제목")


def test_script_revision_does_not_copy_downstream_validation_artifacts(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    generate_script(settings, run_id, structured=FakeScriptProvider(), source_chunks=chunks)
    source = settings.project.output_path / run_id
    (source / "citations.json").write_text("{}", encoding="utf-8")
    (source / "validation_report.md").write_text("검증", encoding="utf-8")
    revision = settings.project.output_path / create_script_revision(settings, run_id)
    assert (revision / "input.json").is_file()
    for name in ("script.md", "script_with_sources.md", "citations.json", "validation_report.md"):
        assert not (revision / name).exists()
