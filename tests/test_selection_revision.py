import json
from pathlib import Path

import pytest

from app.config import ProjectSettings, Settings
from backend.app.schemas import OutlineJobRequest
from backend.app.services.selection import prepare_selection_revision, validate_outline_request


def _write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def _settings(tmp_path: Path) -> tuple[Settings, Path]:
    output = tmp_path / "outputs"
    source = output / "source_run"
    source.mkdir(parents=True)
    _write(source / "input.json", {"topic": "일과 자아의 거리", "target_book_count": 3})
    _write(source / "topic_analysis.json", {"core_question": "일은 왜 자아가 되는가", "intent": "거리 찾기", "subtopics": ["일", "자아"], "keywords": ["일", "자아", "거리"], "search_queries": ["일 자아", "직업 정체성"]})
    _write(source / "candidate_books.json", [
        {"book_id": "a", "title": "일의 철학", "author": "저자 A", "source_file": "일의 철학.md", "score": 0.9, "chunk_count": 2, "evidence_chunk_ids": ["ca"], "perspective": "일과 정체성", "inclusion_reason": "일과 자아를 분리한다."},
        {"book_id": "b", "title": "회복의 기술", "author": "저자 B", "source_file": "회복의 기술.md", "score": 0.8, "chunk_count": 2, "evidence_chunk_ids": ["cb"], "perspective": "회복", "inclusion_reason": "회복의 단계를 설명한다."},
        {"book_id": "c", "title": "성과의 함정", "author": "저자 C", "source_file": "성과의 함정.md", "score": 0.7, "chunk_count": 1, "evidence_chunk_ids": ["cc"], "perspective": "성과", "inclusion_reason": "성과 압박을 설명한다."},
    ])
    _write(source / "evidence.json", [
        {"evidence_id": "ea", "book_id": "a", "type": "paraphrase", "claim": "일과 자아는 다르다.", "source_chunk_ids": ["ca"], "confidence": 0.9},
        {"evidence_id": "eb", "book_id": "b", "type": "quotation", "claim": "회복에는 거리가 필요하다.", "source_chunk_ids": ["cb"], "confidence": 0.8},
        {"evidence_id": "ec", "book_id": "c", "type": "interpretation", "claim": "성과는 압박이 된다.", "source_chunk_ids": ["cc"], "confidence": 0.3},
    ])
    _write(source / "selected_books.json", {
        "selected_books": [
            {"book_id": "a", "role": "문제 정의", "selection_reason": "정체성 근거"},
            {"book_id": "b", "role": "회복 제안", "selection_reason": "회복 근거"},
        ],
        "excluded_books": [{"book_id": "c", "reason": "근거 부족"}],
        "cross_book_connection": "문제에서 회복으로",
    })
    settings = Settings(project=ProjectSettings(
        library_path=tmp_path / "library", output_path=output, database_path=tmp_path / "db.sqlite",
    ))
    return settings, source


def test_creates_ordered_immutable_selection_revision(tmp_path: Path) -> None:
    settings, source = _settings(tmp_path)
    original = (source / "selected_books.json").read_text(encoding="utf-8")
    request = OutlineJobRequest(source_run_id="source_run", selected_book_ids=["b", "a"])

    run_id = prepare_selection_revision(settings, request)
    revised = settings.project.output_path / run_id
    selection = json.loads((revised / "selected_books.json").read_text(encoding="utf-8"))
    revised_input = json.loads((revised / "input.json").read_text(encoding="utf-8"))
    manifest = json.loads((revised / "selection_revision.json").read_text(encoding="utf-8"))

    assert [item["book_id"] for item in selection["selected_books"]] == ["b", "a"]
    assert revised_input["target_book_count"] == 2
    assert manifest["source_run_id"] == "source_run"
    assert (source / "selected_books.json").read_text(encoding="utf-8") == original
    assert revised != source


def test_rejects_selection_without_reliable_evidence(tmp_path: Path) -> None:
    settings, _ = _settings(tmp_path)
    request = OutlineJobRequest(source_run_id="source_run", selected_book_ids=["a", "c"])
    with pytest.raises(ValueError, match="신뢰도 0.5"):
        validate_outline_request(settings, request)


def test_shorts_selection_revision_accepts_exactly_one_book(tmp_path: Path) -> None:
    settings, source = _settings(tmp_path)
    input_payload = json.loads((source / "input.json").read_text(encoding="utf-8"))
    input_payload["content_format"] = "shorts"
    _write(source / "input.json", input_payload)

    run_id = prepare_selection_revision(
        settings, OutlineJobRequest(source_run_id="source_run", selected_book_ids=["a"]),
    )
    revised = settings.project.output_path / run_id
    selection = json.loads((revised / "selected_books.json").read_text(encoding="utf-8"))

    assert [item["book_id"] for item in selection["selected_books"]] == ["a"]
    assert "한 권의 책을 소개한다" in selection["cross_book_connection"]


def test_shorts_selection_revision_rejects_multiple_books(tmp_path: Path) -> None:
    settings, source = _settings(tmp_path)
    input_payload = json.loads((source / "input.json").read_text(encoding="utf-8"))
    input_payload["content_format"] = "shorts"
    _write(source / "input.json", input_payload)

    with pytest.raises(ValueError, match="1권만"):
        validate_outline_request(
            settings, OutlineJobRequest(source_run_id="source_run", selected_book_ids=["a", "b"]),
        )
