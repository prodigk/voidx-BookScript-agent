"""Insight-backed editorial strategy and topic ideation."""

from __future__ import annotations

import json
import re

from app.config import Settings
from app.insights.registry import select_insight_context, sync_insights
from app.llm.prompt_loader import load_prompt
from app.llm.structured import OpenAIStructuredProvider, StructuredProvider
from app.schemas.insight import EditorialStrategy, InsightDocument, TopicIdeas
from app.schemas.topic import TopicRequest


def _source_snapshot(documents: list[InsightDocument]) -> list[dict[str, object]]:
    return [
        {
            "insight_id": item.insight_id, "source_file": item.source_file, "title": item.title,
            "insight_type": item.insight_type, "source": item.source, "created_at": item.created_at,
            "tags": item.tags, "content_hash": item.content_hash,
        }
        for item in documents
    ]


def build_editorial_strategy(
    settings: Settings,
    request: TopicRequest,
    *,
    structured: StructuredProvider | None = None,
) -> tuple[EditorialStrategy | None, list[dict[str, object]]]:
    """Create a reproducible topic-specific strategy from selected insight excerpts."""
    if not settings.insights.enabled:
        return None, []
    manifest, _ = sync_insights(settings.insights)
    if not manifest.documents:
        return None, []
    query = " ".join([
        settings.insights.default_profile, request.topic, request.audience, request.tone,
        *request.desired_lenses, *request.desired_emotional_effects, *request.excluded_lenses,
    ])
    context = select_insight_context(
        manifest, query, settings.insights.max_context_chars, settings.insights.max_documents,
    )
    if not context:
        return None, _source_snapshot(manifest.documents)
    structured = structured or OpenAIStructuredProvider(settings.llm)
    strategy = structured.parse(
        stage="editorial_strategy", instructions=load_prompt("editorial_strategist"),
        input_text=json.dumps({
            "profile": settings.insights.default_profile,
            "request": request.model_dump(mode="json"), "insight_context": context,
        }, ensure_ascii=False),
        output_type=EditorialStrategy,
    )
    allowed_ids = {item.insight_id for item in manifest.documents}
    if not set(strategy.source_insight_ids) <= allowed_ids:
        raise ValueError("Editorial strategy returned unknown insight IDs")
    strategy = strategy.model_copy(update={"profile": settings.insights.default_profile})
    used = [item for item in manifest.documents if item.insight_id in set(strategy.source_insight_ids)]
    return strategy, _source_snapshot(used)


def suggest_topics(
    settings: Settings,
    count: int = 10,
    *,
    structured: StructuredProvider | None = None,
) -> TopicIdeas:
    """Generate insight-backed topic candidates and save inspectable artifacts."""
    if not settings.insights.enabled:
        raise ValueError("Insight integration is disabled")
    manifest, _ = sync_insights(settings.insights)
    if not manifest.documents:
        raise ValueError("No insight Markdown files were found")
    context = select_insight_context(
        manifest, settings.insights.default_profile,
        settings.insights.max_context_chars, settings.insights.max_documents,
    )
    structured = structured or OpenAIStructuredProvider(settings.llm)
    result = structured.parse(
        stage="topic_ideation", instructions=load_prompt("topic_ideator"),
        input_text=json.dumps({
            "profile": settings.insights.default_profile, "requested_count": count,
            "insight_context": context,
        }, ensure_ascii=False), output_type=TopicIdeas,
    )
    allowed_ids = {item.insight_id for item in manifest.documents}
    if not set(result.source_insight_ids) <= allowed_ids:
        raise ValueError("Topic ideator returned unknown insight IDs")
    ideas = [
        item.model_copy(update={
            "title": re.sub(r"^\[(?:standard|sleep_longform|shortform)\]\s*", "", item.title),
            "audience_state": re.sub(
                r"^format=(?:standard|sleep_longform|shortform)\s*\|\s*", "", item.audience_state,
            ),
        })
        for item in result.ideas[:count]
    ]
    if len(ideas) < min(count, 3):
        raise ValueError("Topic ideator returned too few ideas")
    result = result.model_copy(update={"profile": settings.insights.default_profile, "ideas": ideas})
    data_path = settings.insights.manifest_path.parent / "topic_ideas.json"
    report_path = settings.project.output_path.parent / "reports" / "topic_ideas.md"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    lines = [f"# {result.profile} 주제 후보", ""]
    for index, idea in enumerate(result.ideas, 1):
        lines += [
            f"## {index}. {idea.title}", "", f"- 핵심 질문: {idea.core_question}",
            f"- 시청자 상태: {idea.audience_state}", f"- 정서적 약속: {idea.emotional_promise}",
            f"- 관점: {', '.join(idea.suggested_lenses)}", f"- 포맷: {idea.format}",
            f"- 선정 이유: {idea.reason}", "",
        ]
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return result
