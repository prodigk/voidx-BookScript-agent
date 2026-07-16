"""Transparent keyword, semantic, metadata, and diversity score fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import RetrievalSettings, Settings, load_retrieval_settings
from app.llm.embeddings import EmbeddingProvider
from app.retrieval.keyword_search import keyword_search
from app.retrieval.semantic_search import semantic_search
from app.schemas.chunk import HybridSearchResult, SearchResult


def _normalize(results: list[SearchResult]) -> dict[str, float]:
    if not results:
        return {}
    values = [result.score for result in results]
    minimum, maximum = min(values), max(values)
    if maximum == minimum:
        return {result.chunk_id: 1.0 for result in results}
    return {result.chunk_id: (result.score - minimum) / (maximum - minimum) for result in results}


def _metadata_score(query: str, result: SearchResult) -> float:
    terms = {term.casefold() for term in re.findall(r"[\w가-힣]+", query)}
    if not terms:
        return 0.0
    metadata = f"{result.title} {result.author} {' '.join(result.heading_path)}".casefold()
    return sum(term in metadata for term in terms) / len(terms)


def hybrid_search(
    settings: Settings,
    query: str,
    limit: int = 10,
    *,
    retrieval: RetrievalSettings | None = None,
    provider: EmbeddingProvider | None = None,
) -> list[HybridSearchResult]:
    retrieval = retrieval or load_retrieval_settings()
    pool = retrieval.limits.candidate_pool
    keyword = keyword_search(settings.project.database_path, query, min(pool, 100))
    semantic = semantic_search(settings, query, pool, provider)
    keyword_scores, semantic_scores = _normalize(keyword), _normalize(semantic)
    candidates: dict[str, SearchResult] = {result.chunk_id: result for result in semantic}
    candidates.update({result.chunk_id: result for result in keyword})
    weighted: list[HybridSearchResult] = []
    for chunk_id, candidate in candidates.items():
        keyword_score = keyword_scores.get(chunk_id, 0.0)
        semantic_score = semantic_scores.get(chunk_id, 0.0)
        metadata_score = _metadata_score(query, candidate)
        base = (
            retrieval.weights.keyword * keyword_score
            + retrieval.weights.semantic * semantic_score
            + retrieval.weights.metadata * metadata_score
        )
        weighted.append(
            HybridSearchResult(**candidate.model_dump(exclude={"score"}), score=base,
                keyword_score=keyword_score, semantic_score=semantic_score,
                metadata_score=metadata_score, diversity_score=0.0)
        )
    weighted.sort(key=lambda result: result.score, reverse=True)
    selected: list[HybridSearchResult] = []
    book_counts: dict[str, int] = {}
    for candidate in weighted:
        count = book_counts.get(candidate.book_id, 0)
        if count >= retrieval.limits.max_chunks_per_book:
            continue
        diversity_score = 1.0 / (count + 1) if retrieval.diversity.enabled else 0.0
        penalty = retrieval.diversity.same_book_penalty * count if retrieval.diversity.enabled else 0.0
        candidate.diversity_score = diversity_score
        candidate.score = candidate.score + retrieval.weights.diversity * diversity_score - penalty
        selected.append(candidate)
        book_counts[candidate.book_id] = count + 1
    selected.sort(key=lambda result: result.score, reverse=True)
    return selected[:limit]
