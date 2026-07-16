"""Phase 4 topic analysis, retrieval, evidence curation, and book selection."""

from __future__ import annotations

import json
import math
import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.agents.editorial import build_editorial_strategy
from app.llm.prompt_loader import load_prompt
from app.llm.structured import OpenAIStructuredProvider, StructuredProvider
from app.retrieval.hybrid_search import hybrid_search
from app.schemas.chunk import HybridSearchResult
from app.schemas.evidence import (
    BookAssessment,
    BookSelection,
    CandidateBook,
    CandidateScreening,
    EvidenceCuration,
    EvidenceItem,
    Phase4Result,
)
from app.schemas.topic import TopicAnalysis, TopicRequest
from app.schemas.insight import EditorialStrategy


def _run_id(topic: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "-", topic).strip("-")[:40] or "topic"
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}_{slug}"


def _rank_candidates(
    result_sets: list[list[HybridSearchResult]], candidate_count: int
) -> tuple[list[CandidateBook], dict[str, HybridSearchResult]]:
    chunks: dict[str, HybridSearchResult] = {}
    query_coverage: dict[str, set[int]] = defaultdict(set)
    book_chunks: dict[str, dict[str, HybridSearchResult]] = defaultdict(dict)
    for query_index, results in enumerate(result_sets):
        for result in results:
            prior = chunks.get(result.chunk_id)
            if prior is None or result.score > prior.score:
                chunks[result.chunk_id] = result
                book_chunks[result.book_id][result.chunk_id] = result
            query_coverage[result.book_id].add(query_index)
    candidates: list[CandidateBook] = []
    for book_id, mapping in book_chunks.items():
        ranked = sorted(mapping.values(), key=lambda item: item.score, reverse=True)
        top = ranked[:5]
        average = sum(max(item.score, 0) for item in top) / len(top)
        coverage_bonus = len(query_coverage[book_id]) / max(len(result_sets), 1)
        score = average * 0.8 + coverage_bonus * 0.2
        first = top[0]
        candidates.append(
            CandidateBook(
                book_id=book_id, title=first.title, author=first.author,
                source_file=first.source_file.as_posix(), score=score,
                chunk_count=len(ranked), evidence_chunk_ids=[item.chunk_id for item in top],
                retrieval_score=score,
            )
        )
    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[:candidate_count], chunks


def _screening_context(
    request: TopicRequest,
    analysis: TopicAnalysis,
    candidates: list[CandidateBook],
    chunks: dict[str, HybridSearchResult],
    editorial_strategy: EditorialStrategy | None = None,
) -> str:
    request_context = {
        "topic": request.topic,
        "desired_lenses": request.desired_lenses,
        "desired_emotional_effects": request.desired_emotional_effects,
        "excluded_lenses": request.excluded_lenses,
        "topic_analysis": analysis.model_dump(mode="json"),
        "editorial_strategy": editorial_strategy.model_dump(mode="json") if editorial_strategy else None,
    }
    blocks = ["REQUEST\n" + json.dumps(request_context, ensure_ascii=False)]
    for candidate in candidates:
        excerpts = []
        for chunk_id in candidate.evidence_chunk_ids[:2]:
            chunk = chunks[chunk_id]
            excerpts.append(
                f"CHUNK {chunk_id} | {' > '.join(chunk.heading_path)}\n{chunk.content[:1200]}"
            )
        blocks.append(
            f"BOOK {candidate.book_id} | {candidate.title} | retrieval={candidate.score:.4f}\n"
            + "\n".join(excerpts)
        )
    return "\n\n".join(blocks)


def _apply_screening(
    candidates: list[CandidateBook],
    screening: CandidateScreening,
    final_count: int,
) -> tuple[list[CandidateBook], list[dict]]:
    candidate_by_id = {candidate.book_id: candidate for candidate in candidates}
    fits = {fit.book_id: fit for fit in screening.candidates if fit.book_id in candidate_by_id}
    screened: list[CandidateBook] = []
    records: list[dict] = []
    for candidate in candidates:
        fit = fits.get(candidate.book_id)
        if fit is None:
            records.append({"book_id": candidate.book_id, "include": False, "exclusion_reason": "심사 결과 누락"})
            continue
        retrieval = candidate.retrieval_score or candidate.score
        combined = (
            retrieval * 0.15
            + fit.topic_fit_score * 0.35
            + fit.editorial_fit_score * 0.30
            + fit.emotional_fit_score * 0.20
        )
        updated = candidate.model_copy(update={
            "score": combined,
            "topic_fit_score": fit.topic_fit_score,
            "editorial_fit_score": fit.editorial_fit_score,
            "emotional_fit_score": fit.emotional_fit_score,
            "perspective": fit.perspective,
            "inclusion_reason": fit.reason,
        })
        records.append({**fit.model_dump(mode="json"), "retrieval_score": retrieval, "combined_score": combined})
        if fit.include:
            screened.append(updated)
    screened.sort(key=lambda item: item.score, reverse=True)
    return screened[:final_count], records


def _evidence_context(candidates: list[CandidateBook], chunks: dict[str, HybridSearchResult]) -> str:
    blocks: list[str] = []
    total_chars = 0
    for candidate in candidates:
        header = f"BOOK {candidate.book_id} | {candidate.title} | {candidate.author}"
        parts = [header]
        for chunk_id in candidate.evidence_chunk_ids[:3]:
            chunk = chunks[chunk_id]
            excerpt = chunk.content[:1800]
            part = (
                f"CHUNK {chunk.chunk_id} | source={chunk.source_file}:{chunk.start_line}-{chunk.end_line} "
                f"| heading={' > '.join(chunk.heading_path)}\n{excerpt}"
            )
            if total_chars + len(part) > 45_000:
                break
            parts.append(part)
            total_chars += len(part)
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def _validate_curation(
    curation: EvidenceCuration, candidates: list[CandidateBook]
) -> list[EvidenceItem]:
    allowed_books = {candidate.book_id: set(candidate.evidence_chunk_ids) for candidate in candidates}
    evidence: list[EvidenceItem] = []
    seen_ids: set[str] = set()
    for assessment in curation.assessments:
        if assessment.book_id not in allowed_books:
            continue
        for item in assessment.evidence:
            if item.book_id != assessment.book_id or item.evidence_id in seen_ids:
                continue
            if not set(item.source_chunk_ids) <= allowed_books[assessment.book_id]:
                continue
            seen_ids.add(item.evidence_id)
            evidence.append(item)
    return evidence


def _write_artifacts(
    run_dir: Path, request: TopicRequest, result: Phase4Result,
    curation: EvidenceCuration | None = None,
    search_records: list[dict] | None = None,
    screening_records: list[dict] | None = None,
    editorial_strategy: EditorialStrategy | None = None,
    insight_sources: list[dict[str, object]] | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=False)
    payloads = {
        "input.json": request.model_dump(mode="json"),
        "topic_analysis.json": result.topic_analysis.model_dump(mode="json"),
        "search_results.json": search_records or [],
        "candidate_screening.json": screening_records or [],
        "candidate_books.json": [item.model_dump(mode="json") for item in result.candidate_books],
        "evidence.json": [item.model_dump(mode="json") for item in result.evidence],
        "selected_books.json": result.selection.model_dump(mode="json") if result.selection else {"status": result.status, "message": result.message},
        "editorial_strategy.json": editorial_strategy.model_dump(mode="json") if editorial_strategy else {"status": "not_applied"},
        "insight_sources.json": insight_sources or [],
    }
    for filename, payload in payloads.items():
        (run_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# 영상 리서치", "", "## 입력 주제", request.topic, "", "## 핵심 질문", result.topic_analysis.core_question, "", "## 후보 도서"]
    assessments = {item.book_id: item for item in (curation.assessments if curation else [])}
    for candidate in result.candidate_books:
        assessment = assessments.get(candidate.book_id)
        lines += [f"### {candidate.title}", f"- 저자: {candidate.author}", f"- 점수: {candidate.score:.4f}", f"- 출처: `{candidate.source_file}`"]
        if candidate.editorial_fit_score is not None:
            lines += [
                f"- 주제 적합성: {candidate.topic_fit_score:.2f}",
                f"- 편집 관점 적합성: {candidate.editorial_fit_score:.2f}",
                f"- 정서 적합성: {candidate.emotional_fit_score:.2f}",
                f"- 관점: {candidate.perspective}",
                f"- 포함 이유: {candidate.inclusion_reason}",
            ]
        if assessment:
            lines += [f"- 관련성: {assessment.relevance_reason}", f"- 제안 역할: {assessment.suggested_role}"]
    lines += ["", "## 최종 선택"]
    if result.selection:
        selected_by_id = {item.book_id: item for item in result.candidate_books}
        for selected in result.selection.selected_books:
            book = selected_by_id[selected.book_id]
            lines += [f"- {book.title}: {selected.role} — {selected.selection_reason}"]
        lines += ["", "## 도서 연결", result.selection.cross_book_connection]
    else:
        lines.append(result.message or "근거 부족")
    (run_dir / "research.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_phase4(
    settings: Settings,
    request: TopicRequest,
    *,
    structured: StructuredProvider | None = None,
    search: Callable[[str], list[HybridSearchResult]] | None = None,
    editorial_strategy: EditorialStrategy | None = None,
) -> Phase4Result:
    """Run the evidence-first Phase 4 pipeline and persist inspectable artifacts."""
    structured = structured or OpenAIStructuredProvider(settings.llm)
    search = search or (lambda query: hybrid_search(settings, query, limit=30))
    insight_sources: list[dict[str, object]] = []
    if editorial_strategy is None:
        editorial_strategy, insight_sources = build_editorial_strategy(
            settings, request, structured=structured,
        )
    analysis = structured.parse(
        stage="topic_analysis", instructions=load_prompt("topic_planner"),
        input_text=json.dumps({
            "request": request.model_dump(mode="json"),
            "editorial_strategy": editorial_strategy.model_dump(mode="json") if editorial_strategy else None,
        }, ensure_ascii=False), output_type=TopicAnalysis,
    )
    queries = list(dict.fromkeys([request.topic, *analysis.search_queries]))
    result_sets = [search(query) for query in queries]
    search_records = [
        {
            "query": query,
            "results": [item.model_dump(mode="json") for item in results],
        }
        for query, results in zip(queries, result_sets, strict=True)
    ]
    raw_candidates, chunks = _rank_candidates(result_sets, settings.book_selection.screening_count)
    screening_records: list[dict] = []
    has_editorial_options = bool(
        request.desired_lenses or request.desired_emotional_effects or request.excluded_lenses
        or editorial_strategy is not None
    )
    if has_editorial_options:
        screening = structured.parse(
            stage="candidate_screening", instructions=load_prompt("candidate_screener"),
            input_text=_screening_context(request, analysis, raw_candidates, chunks, editorial_strategy),
            output_type=CandidateScreening,
        )
        candidates, screening_records = _apply_screening(
            raw_candidates, screening, settings.book_selection.candidate_count
        )
    else:
        candidates = raw_candidates[: settings.book_selection.candidate_count]
    run_id = _run_id(request.topic)
    run_dir = settings.project.output_path / run_id
    empty_selection = Phase4Result(
        status="insufficient_evidence", run_id=run_id,
        message="검색된 후보 도서가 요청 권수보다 적습니다.", topic_analysis=analysis,
        candidate_books=candidates, evidence=[], selection=None,
    )
    if len(candidates) < request.target_book_count:
        _write_artifacts(
            run_dir, request, empty_selection, search_records=search_records,
            screening_records=screening_records,
            editorial_strategy=editorial_strategy, insight_sources=insight_sources,
        )
        return empty_selection
    curation = structured.parse(
        stage="evidence_curation", instructions=load_prompt("evidence_curator"),
        input_text=f"TOPIC\n{analysis.model_dump_json()}\n\nRETRIEVED EVIDENCE\n{_evidence_context(candidates, chunks)}",
        output_type=EvidenceCuration,
    )
    evidence = _validate_curation(curation, candidates)
    supported_books = {item.book_id for item in evidence if item.confidence >= 0.5}
    if len(supported_books) < request.target_book_count:
        insufficient = empty_selection.model_copy(update={
            "message": "요청한 도서 수를 뒷받침할 근거가 부족합니다.", "evidence": evidence,
        })
        _write_artifacts(
            run_dir, request, insufficient, curation, search_records, screening_records,
            editorial_strategy, insight_sources,
        )
        return insufficient
    selection_input = {
        "target_book_count": request.target_book_count,
        "topic_analysis": analysis.model_dump(mode="json"),
        "candidates": [item.model_dump(mode="json") for item in candidates if item.book_id in supported_books],
        "assessments": [item.model_dump(mode="json") for item in curation.assessments if item.book_id in supported_books],
        "editorial_strategy": editorial_strategy.model_dump(mode="json") if editorial_strategy else None,
    }
    selection = structured.parse(
        stage="book_selection", instructions=load_prompt("book_selector"),
        input_text=json.dumps(selection_input, ensure_ascii=False), output_type=BookSelection,
    )
    allowed = supported_books
    selected_ids = [item.book_id for item in selection.selected_books]
    if len(selected_ids) != request.target_book_count or len(set(selected_ids)) != len(selected_ids) or not set(selected_ids) <= allowed:
        raise ValueError("Book selector returned invalid book IDs or count")
    result = Phase4Result(
        status="complete", run_id=run_id, topic_analysis=analysis,
        candidate_books=candidates, evidence=evidence, selection=selection,
    )
    _write_artifacts(
        run_dir, request, result, curation, search_records, screening_records,
        editorial_strategy, insight_sources,
    )
    return result
