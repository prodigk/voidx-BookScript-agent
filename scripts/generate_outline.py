"""Generate a Phase 5 narrative plan from a completed Phase 4 run."""

import argparse

from app.agents.phase5 import generate_narrative
from app.config import load_settings
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="근거 기반 내러티브와 영상 구성안 생성")
    parser.add_argument("--run-id", required=True, help="완료된 Phase 4 실행 ID")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    plan = generate_narrative(settings, args.run_id)
    run_dir = settings.project.output_path / args.run_id
    print(f"sections={len(plan.sections)}")
    print(f"seconds={plan.total_seconds}")
    print(run_dir / "narrative.json")
    print(run_dir / "outline.md")


if __name__ == "__main__":
    main()
