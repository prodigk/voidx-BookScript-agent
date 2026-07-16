"""Validate a Phase 6 script against its local evidence chunks."""

import argparse

from app.agents.phase7 import validate_script_run
from app.config import load_settings
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="대본의 인용, 요약, 책 귀속과 출처 검증")
    parser.add_argument("--run-id", required=True, help="완료된 Phase 6 실행 ID")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    result = validate_script_run(settings, args.run_id)
    run_dir = settings.project.output_path / args.run_id
    print(f"status={result.status}")
    print(f"valid={result.valid_count} review={result.needs_review_count} invalid={result.invalid_count}")
    print(run_dir / "citations.json")
    print(run_dir / "validation_report.md")


if __name__ == "__main__":
    main()
