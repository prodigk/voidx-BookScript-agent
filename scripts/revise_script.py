"""Create a targeted script revision from a Phase 7 validation report."""

import argparse

from app.agents.phase7 import create_validated_revision
from app.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="고위험 출처 검증 문제만 수정한 새 대본 리비전 생성")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    settings = load_settings()
    run_id = create_validated_revision(settings, args.run_id)
    print(f"run_id={run_id}")
    print(settings.project.output_path / run_id)


if __name__ == "__main__":
    main()
