"""Persistent, single-worker local research job orchestration."""

from __future__ import annotations

import logging
import os
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from app.agents.phase4 import run_phase4
from app.agents.phase5 import generate_narrative
from app.agents.phase6 import generate_script
from app.agents.phase7 import create_validated_revision, validate_script_run
from app.config import Settings
from app.schemas.topic import TopicRequest
from app.storage.database import connect_database
from backend.app.schemas import (
    OutlineJobRequest,
    OutlineJobResponse,
    CitationRevisionJobRequest,
    CitationRevisionJobResponse,
    PipelineJobResponse,
    ResearchJobListResponse,
    ResearchJobResponse,
    ScriptJobRequest,
    ScriptJobResponse,
    ValidationJobRequest,
    ValidationJobResponse,
)
from backend.app.services.narrative_revision import (
    prepare_narrative_revision,
    validate_script_job_request,
)
from backend.app.services.citation_revision import validate_citation_revision_request
from backend.app.services.selection import prepare_selection_revision, validate_outline_request
from backend.app.services.validation import validate_validation_job_request

logger = logging.getLogger(__name__)


class ResearchResult(Protocol):
    status: str
    run_id: str


ResearchRunner = Callable[[Settings, TopicRequest], ResearchResult]
SelectionBuilder = Callable[[Settings, OutlineJobRequest], str]
NarrativeRunner = Callable[[Settings, str], object]
NarrativeRevisionBuilder = Callable[[Settings, ScriptJobRequest], str]
ScriptRunner = Callable[[Settings, str], object]
ValidationRunner = Callable[[Settings, str], object]
CitationRevisionBuilder = Callable[[Settings, str, list[str] | None], str]


class ActiveJobError(RuntimeError):
    """Raised when the configured local job concurrency is exhausted."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_error_message(exc: Exception) -> str:
    """Return a bounded failure reason with the configured API key redacted."""
    message = f"{type(exc).__name__}: {exc}"
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    return message[:800]


def initialize_job_store(database_path: Path) -> None:
    """Create the persistent job table and fail work interrupted by a prior server exit."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pipeline_jobs (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                request_json TEXT NOT NULL,
                run_id TEXT,
                pipeline_status TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            )
            """
        )
        connection.execute(
            """
            UPDATE pipeline_jobs
            SET status = 'failed', stage = 'interrupted',
                error = '로컬 백엔드가 종료되어 작업이 중단되었습니다.', finished_at = ?
            WHERE status IN ('queued', 'running')
            """,
            (_now(),),
        )


def _to_response(row: sqlite3.Row) -> PipelineJobResponse:
    common = {
        "job_id": row["id"], "kind": row["kind"], "status": row["status"],
        "stage": row["stage"], "run_id": row["run_id"],
        "pipeline_status": row["pipeline_status"], "error": row["error"],
        "created_at": datetime.fromisoformat(row["created_at"]),
        "started_at": datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
        "finished_at": datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
    }
    if row["kind"] == "research":
        return ResearchJobResponse(
            **common, request=TopicRequest.model_validate_json(row["request_json"])
        )
    if row["kind"] == "outline":
        return OutlineJobResponse(
            **common, request=OutlineJobRequest.model_validate_json(row["request_json"])
        )
    if row["kind"] == "script":
        return ScriptJobResponse(
            **common, request=ScriptJobRequest.model_validate_json(row["request_json"])
        )
    if row["kind"] == "validation":
        return ValidationJobResponse(
            **common, request=ValidationJobRequest.model_validate_json(row["request_json"])
        )
    if row["kind"] == "citation_revision":
        return CitationRevisionJobResponse(
            **common,
            request=CitationRevisionJobRequest.model_validate_json(row["request_json"]),
        )
    raise ValueError(f"Unsupported pipeline job kind: {row['kind']}")


def create_research_job(settings: Settings, request: TopicRequest) -> ResearchJobResponse:
    """Persist one queued research job if local concurrency is available."""
    job_id = uuid4().hex
    created_at = _now()
    with connect_database(settings.project.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = int(
            connection.execute(
                "SELECT COUNT(*) FROM pipeline_jobs WHERE status IN ('queued', 'running')"
            ).fetchone()[0]
        )
        if active >= settings.backend.max_concurrent_jobs:
            raise ActiveJobError("이미 실행 중이거나 대기 중인 research 작업이 있습니다.")
        connection.execute(
            """
            INSERT INTO pipeline_jobs(id,kind,status,stage,request_json,created_at)
            VALUES (?, 'research', 'queued', 'queued', ?, ?)
            """,
            (job_id, request.model_dump_json(), created_at),
        )
        row = connection.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    response = _to_response(row)
    if not isinstance(response, ResearchJobResponse):
        raise TypeError("Created job did not have research kind")
    return response


def create_outline_job(settings: Settings, request: OutlineJobRequest) -> OutlineJobResponse:
    """Validate and persist one queued selection revision plus Phase 5 job."""
    validate_outline_request(settings, request)
    job_id = uuid4().hex
    created_at = _now()
    with connect_database(settings.project.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = int(connection.execute(
            "SELECT COUNT(*) FROM pipeline_jobs WHERE status IN ('queued', 'running')"
        ).fetchone()[0])
        if active >= settings.backend.max_concurrent_jobs:
            raise ActiveJobError("이미 실행 중이거나 대기 중인 파이프라인 작업이 있습니다.")
        connection.execute(
            """
            INSERT INTO pipeline_jobs(id,kind,status,stage,request_json,created_at)
            VALUES (?, 'outline', 'queued', 'queued', ?, ?)
            """,
            (job_id, request.model_dump_json(), created_at),
        )
        row = connection.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    response = _to_response(row)
    if not isinstance(response, OutlineJobResponse):
        raise TypeError("Created job did not have outline kind")
    return response


def create_script_job(settings: Settings, request: ScriptJobRequest) -> ScriptJobResponse:
    """Validate and persist one queued narrative revision plus Phase 6 job."""
    validate_script_job_request(settings, request)
    job_id = uuid4().hex
    created_at = _now()
    with connect_database(settings.project.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = int(connection.execute(
            "SELECT COUNT(*) FROM pipeline_jobs WHERE status IN ('queued', 'running')"
        ).fetchone()[0])
        if active >= settings.backend.max_concurrent_jobs:
            raise ActiveJobError("이미 실행 중이거나 대기 중인 파이프라인 작업이 있습니다.")
        connection.execute(
            """
            INSERT INTO pipeline_jobs(id,kind,status,stage,request_json,created_at)
            VALUES (?, 'script', 'queued', 'queued', ?, ?)
            """,
            (job_id, request.model_dump_json(), created_at),
        )
        row = connection.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    response = _to_response(row)
    if not isinstance(response, ScriptJobResponse):
        raise TypeError("Created job did not have script kind")
    return response


def create_validation_job(
    settings: Settings, request: ValidationJobRequest,
) -> ValidationJobResponse:
    """Validate and persist one queued Phase 7 job."""
    validate_validation_job_request(settings, request)
    job_id = uuid4().hex
    created_at = _now()
    with connect_database(settings.project.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = int(connection.execute(
            "SELECT COUNT(*) FROM pipeline_jobs WHERE status IN ('queued', 'running')"
        ).fetchone()[0])
        if active >= settings.backend.max_concurrent_jobs:
            raise ActiveJobError("이미 실행 중이거나 대기 중인 파이프라인 작업이 있습니다.")
        connection.execute(
            """
            INSERT INTO pipeline_jobs(id,kind,status,stage,request_json,created_at)
            VALUES (?, 'validation', 'queued', 'queued', ?, ?)
            """,
            (job_id, request.model_dump_json(), created_at),
        )
        row = connection.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    response = _to_response(row)
    if not isinstance(response, ValidationJobResponse):
        raise TypeError("Created job did not have validation kind")
    return response


def create_citation_revision_job(
    settings: Settings,
    request: CitationRevisionJobRequest,
) -> CitationRevisionJobResponse:
    """Validate and persist one targeted revision plus automatic revalidation job."""
    validate_citation_revision_request(settings, request)
    job_id = uuid4().hex
    created_at = _now()
    with connect_database(settings.project.database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        active = int(connection.execute(
            "SELECT COUNT(*) FROM pipeline_jobs WHERE status IN ('queued', 'running')"
        ).fetchone()[0])
        if active >= settings.backend.max_concurrent_jobs:
            raise ActiveJobError("이미 실행 중이거나 대기 중인 파이프라인 작업이 있습니다.")
        connection.execute(
            """
            INSERT INTO pipeline_jobs(id,kind,status,stage,request_json,created_at)
            VALUES (?, 'citation_revision', 'queued', 'queued', ?, ?)
            """,
            (job_id, request.model_dump_json(), created_at),
        )
        row = connection.execute(
            "SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)
        ).fetchone()
    response = _to_response(row)
    if not isinstance(response, CitationRevisionJobResponse):
        raise TypeError("Created job did not have citation_revision kind")
    return response


def get_research_job(database_path: Path, job_id: str) -> PipelineJobResponse:
    """Read one persistent job record."""
    with connect_database(database_path) as connection:
        row = connection.execute("SELECT * FROM pipeline_jobs WHERE id = ?", (job_id,)).fetchone()
    if row is None:
        raise FileNotFoundError(f"Job not found: {job_id}")
    return _to_response(row)


def list_research_jobs(database_path: Path, *, limit: int = 50) -> ResearchJobListResponse:
    """List recent local research jobs."""
    with connect_database(database_path) as connection:
        total = int(connection.execute("SELECT COUNT(*) FROM pipeline_jobs").fetchone()[0])
        rows = connection.execute(
            "SELECT * FROM pipeline_jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return ResearchJobListResponse(items=[_to_response(row) for row in rows], total=total)


def execute_research_job(
    settings: Settings,
    job_id: str,
    *,
    runner: ResearchRunner = run_phase4,
) -> None:
    """Run Phase 4 and persist success, insufficient evidence, or a bounded error message."""
    started_at = _now()
    with connect_database(settings.project.database_path) as connection:
        row = connection.execute(
            "SELECT request_json FROM pipeline_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            logger.error("Research job disappeared before execution: %s", job_id)
            return
        connection.execute(
            "UPDATE pipeline_jobs SET status='running', stage='phase4_research', started_at=? WHERE id=?",
            (started_at, job_id),
        )
    request = TopicRequest.model_validate_json(row["request_json"])
    try:
        result = runner(settings, request)
        stage = "research_complete" if result.status == "complete" else "insufficient_evidence"
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='succeeded', stage=?, run_id=?, pipeline_status=?, finished_at=?
                WHERE id=?
                """,
                (stage, result.run_id, result.status, _now(), job_id),
            )
    except Exception as exc:  # Background boundary must persist every failure.
        message = _safe_error_message(exc)
        logger.exception("Research job failed: job_id=%s", job_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='failed', stage='failed', error=?, finished_at=? WHERE id=?
                """,
                (message, _now(), job_id),
            )


def execute_outline_job(
    settings: Settings,
    job_id: str,
    *,
    selection_builder: SelectionBuilder = prepare_selection_revision,
    narrative_runner: NarrativeRunner = generate_narrative,
) -> None:
    """Persist an immutable selection revision, then generate and track Phase 5 artifacts."""
    with connect_database(settings.project.database_path) as connection:
        row = connection.execute(
            "SELECT request_json FROM pipeline_jobs WHERE id = ? AND kind = 'outline'", (job_id,)
        ).fetchone()
        if row is None:
            logger.error("Outline job disappeared before execution: %s", job_id)
            return
        connection.execute(
            "UPDATE pipeline_jobs SET status='running', stage='selection_revision', started_at=? WHERE id=?",
            (_now(), job_id),
        )
    request = OutlineJobRequest.model_validate_json(row["request_json"])
    try:
        run_id = selection_builder(settings, request)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                "UPDATE pipeline_jobs SET stage='phase5_narrative', run_id=? WHERE id=?",
                (run_id, job_id),
            )
        narrative_runner(settings, run_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='succeeded', stage='outline_ready', pipeline_status='complete', finished_at=?
                WHERE id=?
                """,
                (_now(), job_id),
            )
    except Exception as exc:  # Background boundary must persist every failure.
        message = _safe_error_message(exc)
        logger.exception("Outline job failed: job_id=%s", job_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='failed', stage='failed', error=?, finished_at=? WHERE id=?
                """,
                (message, _now(), job_id),
            )


def execute_script_job(
    settings: Settings,
    job_id: str,
    *,
    revision_builder: NarrativeRevisionBuilder = prepare_narrative_revision,
    script_runner: ScriptRunner = generate_script,
) -> None:
    """Persist a narrative revision, then generate and track Phase 6 script artifacts."""
    with connect_database(settings.project.database_path) as connection:
        row = connection.execute(
            "SELECT request_json FROM pipeline_jobs WHERE id = ? AND kind = 'script'", (job_id,)
        ).fetchone()
        if row is None:
            logger.error("Script job disappeared before execution: %s", job_id)
            return
        connection.execute(
            "UPDATE pipeline_jobs SET status='running', stage='narrative_revision', started_at=? WHERE id=?",
            (_now(), job_id),
        )
    request = ScriptJobRequest.model_validate_json(row["request_json"])
    try:
        run_id = revision_builder(settings, request)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                "UPDATE pipeline_jobs SET stage='phase6_script', run_id=? WHERE id=?",
                (run_id, job_id),
            )
        script_runner(settings, run_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='succeeded', stage='script_ready', pipeline_status='complete', finished_at=?
                WHERE id=?
                """,
                (_now(), job_id),
            )
    except Exception as exc:  # Background boundary must persist every failure.
        message = _safe_error_message(exc)
        logger.exception("Script job failed: job_id=%s", job_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='failed', stage='failed', error=?, finished_at=? WHERE id=?
                """,
                (message, _now(), job_id),
            )


def execute_validation_job(
    settings: Settings,
    job_id: str,
    *,
    validation_runner: ValidationRunner = validate_script_run,
) -> None:
    """Run Phase 7 and persist approval or revision-required status."""
    with connect_database(settings.project.database_path) as connection:
        row = connection.execute(
            "SELECT request_json FROM pipeline_jobs WHERE id = ? AND kind = 'validation'", (job_id,)
        ).fetchone()
        if row is None:
            logger.error("Validation job disappeared before execution: %s", job_id)
            return
        connection.execute(
            "UPDATE pipeline_jobs SET status='running', stage='phase7_validation', started_at=? WHERE id=?",
            (_now(), job_id),
        )
    request = ValidationJobRequest.model_validate_json(row["request_json"])
    try:
        result = validation_runner(settings, request.source_run_id)
        stage = "validation_approved" if result.status == "approved" else "validation_needs_revision"
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='succeeded', stage=?, run_id=?, pipeline_status=?, finished_at=?
                WHERE id=?
                """,
                (stage, request.source_run_id, result.status, _now(), job_id),
            )
    except Exception as exc:  # Background boundary must persist every failure.
        message = _safe_error_message(exc)
        logger.exception("Validation job failed: job_id=%s", job_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='failed', stage='failed', error=?, finished_at=? WHERE id=?
                """,
                (message, _now(), job_id),
            )


def execute_citation_revision_job(
    settings: Settings,
    job_id: str,
    *,
    revision_builder: CitationRevisionBuilder = create_validated_revision,
    validation_runner: ValidationRunner = validate_script_run,
) -> None:
    """Rewrite selected invalid paragraphs in a new run and immediately revalidate it."""
    with connect_database(settings.project.database_path) as connection:
        row = connection.execute(
            "SELECT request_json FROM pipeline_jobs WHERE id = ? AND kind = 'citation_revision'",
            (job_id,),
        ).fetchone()
        if row is None:
            logger.error("Citation revision job disappeared before execution: %s", job_id)
            return
        connection.execute(
            "UPDATE pipeline_jobs SET status='running', stage='targeted_revision', started_at=? WHERE id=?",
            (_now(), job_id),
        )
    request = CitationRevisionJobRequest.model_validate_json(row["request_json"])
    try:
        run_id = revision_builder(
            settings,
            request.source_run_id,
            request.paragraph_ids,
        )
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                "UPDATE pipeline_jobs SET stage='phase7_revalidation', run_id=? WHERE id=?",
                (run_id, job_id),
            )
        result = validation_runner(settings, run_id)
        stage = "revision_approved" if result.status == "approved" else "revision_needs_revision"
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='succeeded', stage=?, pipeline_status=?, finished_at=?
                WHERE id=?
                """,
                (stage, result.status, _now(), job_id),
            )
    except Exception as exc:  # Background boundary must persist every failure.
        message = _safe_error_message(exc)
        logger.exception("Citation revision job failed: job_id=%s", job_id)
        with connect_database(settings.project.database_path) as connection:
            connection.execute(
                """
                UPDATE pipeline_jobs
                SET status='failed', stage='failed', error=?, finished_at=? WHERE id=?
                """,
                (message, _now(), job_id),
            )
