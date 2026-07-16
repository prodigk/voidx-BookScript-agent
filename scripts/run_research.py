"""Run the Phase 4 evidence-first research pipeline."""

import argparse

from app.agents.phase4 import run_phase4
from app.config import load_settings
from app.schemas.topic import TopicRequest
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="주제 분석, 도서 랭킹, 근거 큐레이션, 최종 도서 선택")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--duration", type=int, default=12)
    parser.add_argument("--books", type=int, default=3)
    parser.add_argument("--tone", default="사색적")
    parser.add_argument("--audience", default="일반 성인")
    parser.add_argument("--lens", action="append", default=[], help="원하는 관점(반복 가능)")
    parser.add_argument("--emotional-effect", action="append", default=[], help="원하는 정서 효과")
    parser.add_argument("--exclude-lens", action="append", default=[], help="제외할 관점")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    result = run_phase4(settings, TopicRequest(
        topic=args.topic, duration_minutes=args.duration, target_book_count=args.books,
        tone=args.tone, audience=args.audience,
        desired_lenses=args.lens, desired_emotional_effects=args.emotional_effect,
        excluded_lenses=args.exclude_lens,
    ))
    print(f"status={result.status}")
    print(f"run_id={result.run_id}")
    print(settings.project.output_path / result.run_id)


if __name__ == "__main__":
    main()
