"""Repeatable FTS retrieval baseline evaluation."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable
from pathlib import Path

import yaml

from app.retrieval.keyword_search import keyword_search
from app.schemas.evaluation import CaseResult, EvaluationDataset, EvaluationResult
from app.schemas.chunk import SearchResult


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EvaluationDataset.model_validate(raw)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFC", value).casefold()


def evaluate_keyword_search(database_path: Path, dataset: EvaluationDataset) -> EvaluationResult:
    return evaluate_search(dataset, lambda query: keyword_search(database_path, query, limit=100))


def evaluate_search(
    dataset: EvaluationDataset,
    search: Callable[[str], list[SearchResult]],
) -> EvaluationResult:
    """Evaluate any chunk retriever after deduplicating results to book rank."""
    cases: list[CaseResult] = []
    for case in dataset.cases:
        chunk_results = search(case.query)
        results = []
        seen_books: set[str] = set()
        for result in chunk_results:
            if result.book_id in seen_books:
                continue
            seen_books.add(result.book_id)
            results.append(result)
            if len(results) == 10:
                break
        sources = [_normalize(result.source_file.as_posix()) for result in results]

        def matched(limit: int) -> list[str]:
            top_sources = sources[:limit]
            return [
                expected.label
                for expected in case.expected_books
                if any(_normalize(expected.source_contains) in source for source in top_sources)
            ]

        matched_5 = matched(5)
        matched_10 = matched(10)
        expected_labels = [expected.label for expected in case.expected_books]
        total = len(expected_labels)
        cases.append(
            CaseResult(
                topic=case.topic,
                query=case.query,
                recall_at_5=len(matched_5) / total,
                recall_at_10=len(matched_10) / total,
                matched_at_5=matched_5,
                matched_at_10=matched_10,
                missing_at_10=[label for label in expected_labels if label not in matched_10],
                returned_titles=[result.title for result in results],
                needs_review=case.needs_review,
            )
        )
    count = len(cases)
    return EvaluationResult(
        case_count=count,
        mean_recall_at_5=sum(case.recall_at_5 for case in cases) / count,
        mean_recall_at_10=sum(case.recall_at_10 for case in cases) / count,
        cases_with_no_results=sum(not case.returned_titles for case in cases),
        cases=cases,
    )


def write_evaluation_report(result: EvaluationResult, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 검색 기준선 평가",
        "",
        f"- 평가 주제 수: {result.case_count}",
        f"- 평균 Recall@5: {result.mean_recall_at_5:.3f}",
        f"- 평균 Recall@10: {result.mean_recall_at_10:.3f}",
        f"- 검색 결과가 없는 주제: {result.cases_with_no_results}",
        f"- 기준 데이터 상태: {'확정' if all(not case.needs_review for case in result.cases) else '사용자 검토 전 초안'}",
        "",
        "## 주제별 결과",
    ]
    for case in result.cases:
        lines += [
            "",
            f"### {case.topic}",
            f"- 검색어: `{case.query}`",
            f"- Recall@5 / @10: {case.recall_at_5:.3f} / {case.recall_at_10:.3f}",
            f"- Top 5 일치: {', '.join(case.matched_at_5) or '없음'}",
            f"- Top 10 누락: {', '.join(case.missing_at_10) or '없음'}",
            f"- 상위 결과: {', '.join(case.returned_titles[:5]) or '없음'}",
            f"- 사람 검토 필요: {'예' if case.needs_review else '아니오'}",
        ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
