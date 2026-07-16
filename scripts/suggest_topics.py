"""Generate topic ideas from the synchronized insight profile."""

import argparse

from app.agents.editorial import suggest_topics
from app.config import load_settings
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="Insight 기반 영상 주제 후보 생성")
    parser.add_argument("--count", type=int, default=10, choices=range(3, 21), metavar="3-20")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    result = suggest_topics(settings, count=args.count)
    print(f"profile={result.profile} count={len(result.ideas)}")
    print(settings.insights.manifest_path.parent / "topic_ideas.json")
    print(settings.project.output_path.parent / "reports" / "topic_ideas.md")


if __name__ == "__main__":
    main()
