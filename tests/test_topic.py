from app.schemas.topic import DEFAULT_EXCLUDED_LENSES, EDITORIAL_FOCUS, TopicRequest
from pydantic import ValidationError
import pytest


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


def test_shorts_request_normalizes_to_one_minute_and_one_book() -> None:
    request = TopicRequest(
        topic="불안할 때 읽을 책",
        content_format="shorts",
        duration_minutes=20,
        target_book_count=4,
    )

    assert request.duration_minutes == 1
    assert request.target_book_count == 1


def test_longform_rejects_single_book_configuration() -> None:
    with pytest.raises(ValidationError, match="longform requires"):
        TopicRequest(topic="한 권 소개", target_book_count=1)
