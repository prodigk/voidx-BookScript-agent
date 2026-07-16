"""Generate Phase 6 evidence-linked and clean narration scripts."""

import argparse

from app.agents.phase6 import create_script_revision, generate_script
from app.config import load_settings
from app.utils.logging import configure_logging


def main() -> None:
    parser = argparse.ArgumentParser(description="근거 연결 대본과 사용자용 대본 생성")
    parser.add_argument("--run-id", required=True, help="완료된 Phase 5 실행 ID")
    parser.add_argument("--revision", action="store_true", help="기존 실행을 보존하고 새 대본 리비전 생성")
    args = parser.parse_args()
    settings = load_settings()
    configure_logging(settings.logging.level)
    run_id = create_script_revision(settings, args.run_id) if args.revision else args.run_id
    script = generate_script(settings, run_id)
    run_dir = settings.project.output_path / run_id
    print(f"run_id={run_id}")
    print(f"sections={len(script.sections)}")
    print(f"seconds={script.target_duration_seconds}")
    print(run_dir / "script_with_sources.md")
    print(run_dir / "script.md")


if __name__ == "__main__":
    main()
