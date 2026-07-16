"""Preflight checks for Phase 7 validation jobs."""

from app.agents.phase5 import resolve_run_dir
from app.config import Settings
from backend.app.schemas import ValidationJobRequest


def validate_validation_job_request(settings: Settings, request: ValidationJobRequest) -> None:
    """Require a complete, not-yet-validated Phase 6 run."""
    run = resolve_run_dir(settings.project.output_path, request.source_run_id)
    missing = [
        name for name in ("script.md", "script_with_sources.md")
        if not (run / name).is_file()
    ]
    if missing:
        raise ValueError("Phase 7 검증에 필요한 대본 산출물이 없습니다: " + ", ".join(missing))
    if (run / "citations.json").exists() or (run / "validation_report.md").exists():
        raise ValueError("이미 검증된 실행입니다. 기존 검증 결과를 사용하세요.")
