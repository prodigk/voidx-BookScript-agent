from app.schemas.topic import DEFAULT_EXCLUDED_LENSES, EDITORIAL_FOCUS, TopicRequest


def test_topic_request_applies_humanities_focus() -> None:
    request = TopicRequest(
        topic="타인의 평가를 의식하는 이유",
        desired_lenses=[*EDITORIAL_FOCUS, "커리어", "생산성"],
        excluded_lenses=["투자"],
    )

    assert request.desired_lenses == ["인문학", "철학", "심리학"]
    assert request.excluded_lenses == ["투자", *DEFAULT_EXCLUDED_LENSES]


def test_topic_request_applies_focus_exclusions_by_default() -> None:
    request = TopicRequest(topic="삶의 의미를 찾는 방법")

    assert request.excluded_lenses == list(DEFAULT_EXCLUDED_LENSES)
