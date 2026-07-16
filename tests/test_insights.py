from pathlib import Path

from app.config import InsightSettings, ProjectSettings, Settings
from app.insights.registry import discover_insights, select_insight_context, sync_insights
from app.schemas.insight import EditorialStrategy, TopicIdeas
from app.schemas.topic import TopicRequest
from app.agents.editorial import build_editorial_strategy, suggest_topics


INSIGHT = """# 테스트 채널 분석 보드

- 유형: 채널 분석
- 출처: 테스트 채널
- 생성일: 2026. 7. 13.
- 태그: 도서, 심리

## 요약
불안한 밤에 차분한 심리 콘텐츠가 적합합니다.

## 추천 전략
상황 공감형 제목과 낮은 자극의 결말을 사용합니다.

## 잠들기전 교양이 적용
공감에서 시작해 원인을 설명하고 여운으로 마무리합니다.
"""


class FakeEditorialProvider:
    def parse(self, *, stage, instructions, input_text, output_type):
        if output_type is EditorialStrategy:
            import json
            context = json.loads(input_text)
            insight_id = context["insight_context"].split("INSIGHT ", 1)[1].split(" ", 1)[0]
            return EditorialStrategy(
                profile="임시", source_insight_ids=[insight_id], topic_opportunity="불안한 밤",
                audience_state="생각이 많아 잠들기 어려운 사람", positioning="밤에 듣는 교양 위로",
                title_directions=["상황 공감형", "감정 질문형", "차분한 선언형"],
                hook_strategy="첫 30초에 감정과 효용을 제시", narrative_strategy=["공감", "원인", "전환"],
                tone_rules=["차분함", "비단정적"], closing_strategy="질문과 여운",
                duration_guidance="15~25분", avoid_patterns=["공포와 과장"],
            )
        if output_type is TopicIdeas:
            import json
            context = json.loads(input_text)
            insight_id = context["insight_context"].split("INSIGHT ", 1)[1].split(" ", 1)[0]
            return TopicIdeas.model_validate({
                "profile": "임시", "source_insight_ids": [insight_id],
                "ideas": [
                    {"title": f"생각이 많은 밤 {i}", "core_question": "왜 생각을 멈추기 어려운가",
                     "audience_state": "불안한 밤", "emotional_promise": "생각을 정리한다",
                     "suggested_lenses": ["심리"], "format": "standard", "reason": "운영 전략 적합"}
                    for i in range(1, 4)
                ],
            })
        raise AssertionError(stage)


def _settings(tmp_path: Path) -> Settings:
    insight_path = tmp_path / "insights"
    insight_path.mkdir()
    (insight_path / "분석.md").write_text(INSIGHT, encoding="utf-8")
    return Settings(
        project=ProjectSettings(output_path=tmp_path / "outputs"),
        insights=InsightSettings(
            path=insight_path, manifest_path=tmp_path / "data" / "manifest.json",
            default_profile="잠들기전 교양이",
        ),
    )


def test_discover_and_sync_insights_incrementally(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    documents = discover_insights(settings.insights.path)
    assert len(documents) == 1
    assert documents[0].source == "테스트 채널"
    assert documents[0].tags == ["도서", "심리"]
    _, first = sync_insights(settings.insights)
    _, second = sync_insights(settings.insights)
    assert first.added == 1
    assert second.unchanged == 1
    insight_file = settings.insights.path / "분석.md"
    insight_file.write_text(INSIGHT + "\n추가 전략", encoding="utf-8")
    _, third = sync_insights(settings.insights)
    assert third.updated == 1
    insight_file.unlink()
    _, fourth = sync_insights(settings.insights)
    assert fourth.deleted == 1
    assert settings.insights.manifest_path.is_file()


def test_select_context_prioritizes_profile_application(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manifest, _ = sync_insights(settings.insights)
    context = select_insight_context(manifest, "불안한 밤", 5000, 5)
    assert "잠들기전 교양이 적용" in context
    assert "추천 전략" in context


def test_build_strategy_and_topic_ideas_save_source_ids(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    provider = FakeEditorialProvider()
    strategy, sources = build_editorial_strategy(
        settings, TopicRequest(topic="타인의 평가"), structured=provider,
    )
    assert strategy is not None
    assert strategy.profile == "잠들기전 교양이"
    assert strategy.source_insight_ids[0] == sources[0]["insight_id"]
    ideas = suggest_topics(settings, count=3, structured=provider)
    assert len(ideas.ideas) == 3
    assert (settings.insights.manifest_path.parent / "topic_ideas.json").is_file()
