from pathlib import Path

from app.agents.phase4 import run_phase4
from app.config import InsightSettings, ProjectSettings, Settings
from app.schemas.chunk import HybridSearchResult
from app.schemas.evidence import BookSelection, CandidateScreening, EvidenceCuration
from app.schemas.topic import TopicAnalysis, TopicRequest
from app.schemas.insight import EditorialStrategy


class FakeStructuredProvider:
    def parse(self, *, stage, instructions, input_text, output_type):
        if output_type is TopicAnalysis:
            return TopicAnalysis(
                core_question="타인의 평가는 정체성에 어떤 영향을 주는가", intent="원인과 대안 탐색",
                subtopics=["평가", "자존감"], keywords=["평가", "인정", "자존감"],
                search_queries=["타인의 평가", "인정 욕구"],
            )
        if output_type is CandidateScreening:
            context = input_text.split("BOOK ")[1:]
            return CandidateScreening.model_validate({"candidates": [
                {
                    "book_id": block.split(" | ", 1)[0],
                    "include": True,
                    "topic_fit_score": 0.9,
                    "editorial_fit_score": 0.9,
                    "emotional_fit_score": 0.9,
                    "perspective": "철학·심리",
                    "reason": "편집 방향 적합",
                    "exclusion_reason": None,
                }
                for block in context
            ]})
        if output_type is EvidenceCuration:
            return EvidenceCuration.model_validate({"assessments": [
                {"book_id": f"book_{i}", "relevance_reason": "직접 관련", "suggested_role": f"역할 {i}",
                 "evidence": [{"evidence_id": f"e_{i}", "book_id": f"book_{i}", "type": "paraphrase",
                    "claim": f"주장 {i}", "source_chunk_ids": [f"chunk_{i}"], "confidence": 0.9}]}
                for i in range(1, 4)
            ]})
        if output_type is BookSelection:
            return BookSelection.model_validate({
                "selected_books": [
                    {"book_id": f"book_{i}", "role": f"역할 {i}", "selection_reason": "근거 충분"}
                    for i in range(1, 4)
                ],
                "excluded_books": [], "cross_book_connection": "원인에서 대안으로 연결",
            })
        raise AssertionError(stage)


class EditorialFakeProvider(FakeStructuredProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        if output_type is CandidateScreening:
            return CandidateScreening.model_validate({"candidates": [
                {"book_id": "book_1", "include": False, "topic_fit_score": 0.7,
                 "editorial_fit_score": 0.1, "emotional_fit_score": 0.1,
                 "perspective": "생산성", "reason": "성과 중심", "exclusion_reason": "제외 관점"},
                *[
                    {"book_id": f"book_{i}", "include": True, "topic_fit_score": 0.9,
                     "editorial_fit_score": 0.9, "emotional_fit_score": 0.9,
                     "perspective": "심리", "reason": "위로 방향", "exclusion_reason": None}
                    for i in range(2, 5)
                ],
            ]})
        if output_type is EvidenceCuration:
            return EvidenceCuration.model_validate({"assessments": [
                {"book_id": f"book_{i}", "relevance_reason": "직접 관련", "suggested_role": f"역할 {i}",
                 "evidence": [{"evidence_id": f"e_{i}", "book_id": f"book_{i}", "type": "paraphrase",
                    "claim": f"주장 {i}", "source_chunk_ids": [f"chunk_{i}"], "confidence": 0.9}]}
                for i in range(2, 5)
            ]})
        if output_type is BookSelection:
            return BookSelection.model_validate({
                "selected_books": [
                    {"book_id": f"book_{i}", "role": f"역할 {i}", "selection_reason": "방향 적합"}
                    for i in range(2, 5)
                ], "excluded_books": [], "cross_book_connection": "위로와 회복",
            })
        return super().parse(stage=stage, instructions=instructions, input_text=input_text, output_type=output_type)


class ShortsStructuredProvider(FakeStructuredProvider):
    def parse(self, *, stage, instructions, input_text, output_type):
        if output_type is BookSelection:
            context = __import__("json").loads(input_text)
            assert context["target_book_count"] == 1
            return BookSelection.model_validate({
                "selected_books": [
                    {"book_id": "book_1", "role": "핵심 통찰 소개", "selection_reason": "주제와 직접 연결"},
                ],
                "excluded_books": [],
                "cross_book_connection": "책 1의 관점을 주제와 연결한다.",
            })
        return super().parse(
            stage=stage, instructions=instructions, input_text=input_text, output_type=output_type,
        )


def _result(index: int) -> HybridSearchResult:
    return HybridSearchResult(
        chunk_id=f"chunk_{index}", book_id=f"book_{index}", title=f"책 {index}", author=f"저자 {index}",
        source_file=Path(f"책{index}.md"), heading_path=["장"], start_line=2, end_line=3,
        content=f"평가와 인정에 대한 근거 {index}", content_hash=f"hash{index}", score=1 - index * 0.1,
        keyword_score=0.5, semantic_score=0.8, metadata_score=0.2, diversity_score=1.0,
    )


def _strategy() -> EditorialStrategy:
    return EditorialStrategy(
        profile="잠들기전 교양이", source_insight_ids=["insight_test"], topic_opportunity="평가 불안",
        audience_state="생각이 많은 밤", positioning="밤에 듣는 교양 위로",
        title_directions=["상황 공감형", "질문형", "차분한 선언형"], hook_strategy="감정에서 시작",
        narrative_strategy=["공감", "원인", "위로"], tone_rules=["차분함", "비단정적"],
        closing_strategy="여운을 남긴다", duration_guidance="15~25분", avoid_patterns=["과장"],
    )


def test_phase4_preserves_evidence_ids_and_writes_artifacts(tmp_path: Path) -> None:
    settings = Settings(project=ProjectSettings(output_path=tmp_path / "outputs"), insights=InsightSettings(enabled=False))
    result = run_phase4(
        settings, TopicRequest(topic="타인의 평가", target_book_count=3),
        structured=FakeStructuredProvider(), search=lambda query: [_result(1), _result(2), _result(3)],
    )
    assert result.status == "complete"
    assert len(result.selection.selected_books) == 3
    assert {item.source_chunk_ids[0] for item in result.evidence} == {"chunk_1", "chunk_2", "chunk_3"}
    run_dir = settings.project.output_path / result.run_id
    assert (run_dir / "topic_analysis.json").is_file()
    assert (run_dir / "candidate_books.json").is_file()
    assert (run_dir / "search_results.json").is_file()
    assert (run_dir / "evidence.json").is_file()
    assert (run_dir / "selected_books.json").is_file()
    assert (run_dir / "research.md").is_file()


def test_phase4_returns_insufficient_evidence_before_curation(tmp_path: Path) -> None:
    settings = Settings(project=ProjectSettings(output_path=tmp_path / "outputs"), insights=InsightSettings(enabled=False))
    result = run_phase4(
        settings, TopicRequest(topic="희귀 주제", target_book_count=3),
        structured=FakeStructuredProvider(), search=lambda query: [_result(1)],
    )
    assert result.status == "insufficient_evidence"
    assert result.selection is None


def test_editorial_options_exclude_mismatched_high_retrieval_book(tmp_path: Path) -> None:
    settings = Settings(project=ProjectSettings(output_path=tmp_path / "outputs"), insights=InsightSettings(enabled=False))
    result = run_phase4(
        settings,
        TopicRequest(
            topic="평가 불안", target_book_count=3, desired_lenses=["철학", "심리"],
            desired_emotional_effects=["위로"], excluded_lenses=["생산성"],
        ),
        structured=EditorialFakeProvider(),
        search=lambda query: [_result(1), _result(2), _result(3), _result(4)],
    )
    assert result.status == "complete"
    assert "book_1" not in {item.book_id for item in result.candidate_books}
    assert all(item.editorial_fit_score == 0.9 for item in result.candidate_books)
    screening = settings.project.output_path / result.run_id / "candidate_screening.json"
    assert screening.is_file()


def test_phase4_persists_injected_editorial_strategy(tmp_path: Path) -> None:
    settings = Settings(project=ProjectSettings(output_path=tmp_path / "outputs"), insights=InsightSettings(enabled=False))
    result = run_phase4(
        settings, TopicRequest(topic="평가 불안", target_book_count=3), editorial_strategy=_strategy(),
        structured=EditorialFakeProvider(),
        search=lambda query: [_result(1), _result(2), _result(3), _result(4)],
    )
    run_dir = settings.project.output_path / result.run_id
    strategy = (run_dir / "editorial_strategy.json").read_text(encoding="utf-8")
    assert "잠들기전 교양이" in strategy
    assert (run_dir / "insight_sources.json").is_file()


def test_phase4_shorts_selects_exactly_one_supported_book(tmp_path: Path) -> None:
    settings = Settings(project=ProjectSettings(output_path=tmp_path / "outputs"), insights=InsightSettings(enabled=False))
    result = run_phase4(
        settings,
        TopicRequest(topic="타인의 평가를 다룬 한 권", content_format="shorts"),
        structured=ShortsStructuredProvider(),
        search=lambda query: [_result(1), _result(2), _result(3)],
    )

    assert result.status == "complete"
    assert [item.book_id for item in result.selection.selected_books] == ["book_1"]
    input_payload = (settings.project.output_path / result.run_id / "input.json").read_text(encoding="utf-8")
    assert '"content_format": "shorts"' in input_payload
    assert '"target_book_count": 1' in input_payload
