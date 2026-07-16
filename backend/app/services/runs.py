"""Safe discovery and reading of immutable generated run artifacts."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from app.agents.phase5 import resolve_run_dir
from backend.app.schemas import ArtifactSummary, RunDetailResponse, RunListResponse, RunStatus, RunSummary

ARTIFACT_MEDIA_TYPES: dict[str, str] = {
    "input.json": "application/json",
    "topic_analysis.json": "application/json",
    "search_results.json": "application/json",
    "candidate_screening.json": "application/json",
    "candidate_books.json": "application/json",
    "selected_books.json": "application/json",
    "selection_revision.json": "application/json",
    "narrative_revision.json": "application/json",
    "evidence.json": "application/json",
    "editorial_strategy.json": "application/json",
    "insight_sources.json": "application/json",
    "narrative.json": "application/json",
    "citations.json": "application/json",
    "video_manifest.json": "application/json",
    "research.md": "text/markdown",
    "outline.md": "text/markdown",
    "script.md": "text/markdown",
    "script_with_sources.md": "text/markdown",
    "validation_report.md": "text/markdown",
}


def resolve_artifact(output_root: Path, run_id: str, artifact_name: str) -> tuple[Path, str]:
    """Resolve only a known generated artifact inside one immutable run."""
    if artifact_name not in ARTIFACT_MEDIA_TYPES:
        raise ValueError("Artifact is not available through the API")
    run_dir = resolve_run_dir(output_root, run_id)
    path = run_dir / artifact_name
    if not path.is_file():
        raise FileNotFoundError(f"Artifact not found: {artifact_name}")
    return path, ARTIFACT_MEDIA_TYPES[artifact_name]


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _artifacts(run_dir: Path) -> list[ArtifactSummary]:
    return [
        ArtifactSummary(name=name, media_type=media_type, size_bytes=path.stat().st_size)
        for name, media_type in ARTIFACT_MEDIA_TYPES.items()
        if (path := run_dir / name).is_file()
    ]


def _status(run_dir: Path) -> RunStatus:
    validation = _read_json(run_dir / "citations.json")
    if validation.get("status") == "approved":
        return "approved"
    if validation.get("status") == "needs_revision":
        return "needs_revision"
    if (run_dir / "script.md").is_file():
        return "script_ready"
    if (run_dir / "outline.md").is_file():
        return "outline_ready"
    if (run_dir / "research.md").is_file() or (run_dir / "selection_revision.json").is_file():
        return "research_complete"
    return "started"


def _summary(run_dir: Path) -> RunSummary:
    request = _read_json(run_dir / "input.json")
    topic = request.get("topic")
    return RunSummary(
        run_id=run_dir.name,
        topic=str(topic) if topic else "제목 없음",
        status=_status(run_dir),
        created_at=datetime.fromtimestamp(run_dir.stat().st_mtime, tz=UTC),
        artifacts=_artifacts(run_dir),
    )


def list_runs(output_root: Path, *, limit: int = 50) -> RunListResponse:
    """List recent valid run directories without following paths outside outputs."""
    root = output_root.resolve()
    if not root.is_dir():
        return RunListResponse(items=[], total=0)
    directories = [
        path for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".") and path.resolve().parent == root
    ]
    directories.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    items = [_summary(path) for path in directories]
    return RunListResponse(items=items[:limit], total=len(items))


def get_run(output_root: Path, run_id: str) -> RunDetailResponse:
    """Return one run summary and validation counts."""
    run_dir = resolve_run_dir(output_root, run_id)
    summary = _summary(run_dir)
    validation = _read_json(run_dir / "citations.json")
    return RunDetailResponse(
        **summary.model_dump(),
        validation_valid_count=validation.get("valid_count") if isinstance(validation.get("valid_count"), int) else None,
        validation_review_count=validation.get("needs_review_count") if isinstance(validation.get("needs_review_count"), int) else None,
        validation_invalid_count=validation.get("invalid_count") if isinstance(validation.get("invalid_count"), int) else None,
    )
