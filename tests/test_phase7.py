import hashlib
import json
from pathlib import Path

from app.agents.phase7 import create_validated_revision, parse_sourced_script, validate_script_run
from app.config import ProjectSettings, Settings
from app.schemas.validation import CitationReview


class FakeCitationReviewer:
    def __init__(self, supported: bool = True) -> None:
        self.supported = supported

    def parse(self, *, stage, instructions, input_text, output_type):
        assert stage == "citation_reviewer"
        assert output_type is CitationReview
        items = json.loads(input_text)
        return CitationReview.model_validate({"assessments": [
            {"paragraph_id": item["paragraph"]["paragraph_id"], "supported": self.supported,
             "confidence": 0.95, "issue_categories": [] if self.supported else ["unsupported_paraphrase"],
             "explanation": "원문이 문단을 뒷받침합니다." if self.supported else "원문보다 의미가 확대됐습니다.",
             "suggested_rewrite": None if self.supported else "원문 범위로 문장을 완화합니다."}
            for item in items
        ]})


def _write_run(tmp_path: Path, *, quotation: bool = False) -> tuple[Settings, str, list[dict[str, object]]]:
    library = tmp_path / "library"
    library.mkdir()
    source_text = "사회적 뇌는 타인의 반응에 주의를 기울인다."
    (library / "책.md").write_text(source_text + "\n", encoding="utf-8")
    output = tmp_path / "outputs"
    run_id = "run_001"
    run = output / run_id
    run.mkdir(parents=True)
    paragraph_text = "변형된 직접 인용" if quotation else source_text
    text_type = "quotation" if quotation else "paraphrase"
    script = f"""# 제목

## 본론

<!-- REMOTION: section_id=sec_01 start=0s end=60s fps=30 -->

{paragraph_text}

[TYPE:{text_type}] [BOOK:book_1] [SOURCE:e_1] [CHUNK:chunk_1]

## 결론

<!-- REMOTION: section_id=sec_02 start=60s end=120s fps=30 -->

이 영상은 『책 하나』와 『책 둘』의 내용을 바탕으로 구성되었습니다.

[TYPE:commentary]
"""
    (run / "script_with_sources.md").write_text(script, encoding="utf-8")
    clean_script = f"""# 제목

## 본론

{paragraph_text}

## 결론

이 영상은 『책 하나』와 『책 둘』의 내용을 바탕으로 구성되었습니다.
"""
    (run / "script.md").write_text(clean_script, encoding="utf-8")
    artifacts = {
        "input.json": {"topic": "사회적 반응", "content_format": "longform", "duration_minutes": 3, "target_book_count": 2},
        "evidence.json": [{"evidence_id": "e_1", "book_id": "book_1",
                           "type": "quotation" if quotation else "paraphrase", "claim": source_text,
                           "source_chunk_ids": ["chunk_1"], "confidence": 0.9}],
        "candidate_books.json": [
            {"book_id": "book_1", "title": "책 하나", "author": "저자 하나", "source_file": "책.md",
             "score": 0.9, "chunk_count": 1, "evidence_chunk_ids": ["chunk_1"]},
            {"book_id": "book_2", "title": "책 둘", "author": "저자 둘", "source_file": "책2.md",
             "score": 0.8, "chunk_count": 1, "evidence_chunk_ids": []},
        ],
        "selected_books.json": {"selected_books": [
            {"book_id": "book_1", "role": "원인", "selection_reason": "근거"},
            {"book_id": "book_2", "role": "전환", "selection_reason": "근거"},
        ], "excluded_books": [], "cross_book_connection": "연결"},
    }
    for name, payload in artifacts.items():
        (run / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    chunk = {"chunk_id": "chunk_1", "book_id": "book_1", "title": "책 하나", "author": "저자 하나",
             "source_file": "책.md", "heading_path": ["장"], "start_line": 1, "end_line": 1,
             "content": source_text, "content_hash": hashlib.sha256(source_text.encode()).hexdigest()}
    settings = Settings(project=ProjectSettings(library_path=library, output_path=output))
    return settings, run_id, [chunk]


def test_parse_sourced_script_preserves_markers() -> None:
    text = """## 장\n<!-- REMOTION: section_id=sec_01 start=0s -->\n문장\n\n[TYPE:paraphrase] [BOOK:b1] [SOURCE:e1] [CHUNK:c1]\n"""
    parsed = parse_sourced_script(text)
    assert parsed[0].paragraph_id == "sec_01_p01"
    assert parsed[0].evidence_ids == ["e1"]
    assert parsed[0].chunk_ids == ["c1"]


def test_validate_script_writes_approved_citations(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    result = validate_script_run(settings, run_id, structured=FakeCitationReviewer(), source_chunks=chunks)
    assert result.status == "approved"
    assert result.valid_count == 1
    run = settings.project.output_path / run_id
    assert (run / "citations.json").is_file()
    assert "상태: **승인**" in (run / "validation_report.md").read_text(encoding="utf-8")


def test_unsupported_paraphrase_blocks_approval(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    result = validate_script_run(
        settings, run_id, structured=FakeCitationReviewer(supported=False), source_chunks=chunks,
    )
    assert result.status == "needs_revision"
    assert result.invalid_count == 1
    assert result.issues[0].category == "unsupported_paraphrase"


def test_modified_quotation_blocks_approval(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path, quotation=True)
    result = validate_script_run(settings, run_id, structured=FakeCitationReviewer(), source_chunks=chunks)
    assert result.status == "needs_revision"
    assert any(item.category == "modified_quotation" for item in result.issues)


def test_create_validated_revision_replaces_only_invalid_paragraph(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    validate_script_run(settings, run_id, structured=FakeCitationReviewer(supported=False), source_chunks=chunks)
    revision_id = create_validated_revision(settings, run_id)
    revision = settings.project.output_path / revision_id
    sourced = (revision / "script_with_sources.md").read_text(encoding="utf-8")
    clean = (revision / "script.md").read_text(encoding="utf-8")
    assert "원문 범위로 문장을 완화합니다." in sourced
    assert "원문 범위로 문장을 완화합니다." in clean
    assert not (revision / "citations.json").exists()
    manifest = json.loads((revision / "citation_revision.json").read_text(encoding="utf-8"))
    assert manifest["source_run_id"] == run_id
    assert manifest["revised_paragraph_ids"] == ["sec_01_p01"]


def test_create_validated_revision_rejects_unavailable_selected_paragraph(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    validate_script_run(
        settings, run_id, structured=FakeCitationReviewer(supported=False), source_chunks=chunks,
    )
    try:
        create_validated_revision(settings, run_id, ["missing_paragraph"])
    except ValueError as exc:
        assert "do not have high-severity revisions" in str(exc)
    else:
        raise AssertionError("Unavailable paragraph selection must be rejected")


def test_shorts_validation_accepts_title_and_author_in_book_intro(tmp_path: Path) -> None:
    settings, run_id, chunks = _write_run(tmp_path)
    run = settings.project.output_path / run_id
    input_payload = json.loads((run / "input.json").read_text(encoding="utf-8"))
    input_payload.update({"content_format": "shorts", "duration_minutes": 1, "target_book_count": 1})
    (run / "input.json").write_text(json.dumps(input_payload, ensure_ascii=False), encoding="utf-8")
    selection = {
        "selected_books": [{"book_id": "book_1", "role": "핵심 통찰", "selection_reason": "근거"}],
        "excluded_books": [{"book_id": "book_2", "reason": "한 권 쇼츠"}],
        "cross_book_connection": "책 하나를 주제와 연결한다.",
    }
    (run / "selected_books.json").write_text(json.dumps(selection, ensure_ascii=False), encoding="utf-8")
    for name in ("script_with_sources.md", "script.md"):
        text = (run / name).read_text(encoding="utf-8")
        text = text.replace(
            "이 영상은 『책 하나』와 『책 둘』의 내용을 바탕으로 구성되었습니다.",
            "『책 하나』의 저자 저자 하나는 타인의 반응을 관계의 신호로 바라봅니다.",
        )
        (run / name).write_text(text, encoding="utf-8")

    result = validate_script_run(settings, run_id, structured=FakeCitationReviewer(), source_chunks=chunks)

    assert result.status == "approved"
    assert not any(issue.category in {"incorrect_title", "incorrect_author"} for issue in result.issues)
