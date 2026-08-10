"""Phase 8 foundation routes for local library and run inspection."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse, Response

from app.config import Settings
from app.schemas.topic import TopicRequest
from backend.app.schemas import (
    CitationRevisionJobRequest,
    CitationRevisionJobResponse,
    HealthResponse,
    LibraryStatusResponse,
    OutlineJobRequest,
    OutlineJobResponse,
    PipelineJobResponse,
    ResearchJobListResponse,
    ResearchJobResponse,
    RunDetailResponse,
    RunListResponse,
    ScriptJobRequest,
    ScriptJobResponse,
    ValidationJobRequest,
    ValidationJobResponse,
)
from backend.app.services.jobs import (
    ActiveJobError,
    CitationRevisionBuilder,
    NarrativeRunner,
    NarrativeRevisionBuilder,
    ResearchRunner,
    SelectionBuilder,
    ScriptRunner,
    ValidationRunner,
    create_outline_job,
    create_citation_revision_job,
    create_research_job,
    create_script_job,
    create_validation_job,
    execute_outline_job,
    execute_citation_revision_job,
    execute_research_job,
    execute_script_job,
    execute_validation_job,
    get_research_job,
    list_research_jobs,
)
from backend.app.services.library import get_library_status
from backend.app.services.runs import get_run, list_runs, resolve_artifact

router = APIRouter()


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_research_runner(request: Request) -> ResearchRunner:
    return request.app.state.research_runner


def get_selection_builder(request: Request) -> SelectionBuilder:
    return request.app.state.selection_builder


def get_narrative_runner(request: Request) -> NarrativeRunner:
    return request.app.state.narrative_runner


def get_revision_builder(request: Request) -> NarrativeRevisionBuilder:
    return request.app.state.revision_builder


def get_script_runner(request: Request) -> ScriptRunner:
    return request.app.state.script_runner


def get_validation_runner(request: Request) -> ValidationRunner:
    return request.app.state.validation_runner


def get_citation_revision_builder(request: Request) -> CitationRevisionBuilder:
    return request.app.state.citation_revision_builder


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()


@router.get("/api/library/status", response_model=LibraryStatusResponse, tags=["library"])
def library_status(settings: Settings = Depends(get_settings)) -> LibraryStatusResponse:
    return get_library_status(settings)


@router.get("/api/runs", response_model=RunListResponse, tags=["runs"])
def runs(
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> RunListResponse:
    return list_runs(settings.project.output_path, limit=limit)


@router.get("/api/runs/{run_id}", response_model=RunDetailResponse, tags=["runs"])
def run_detail(run_id: str, settings: Settings = Depends(get_settings)) -> RunDetailResponse:
    try:
        return get_run(settings.project.output_path, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/runs/{run_id}/artifacts/{artifact_name}", tags=["runs"])
def run_artifact(
    run_id: str,
    artifact_name: str,
    download: bool = False,
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        path, media_type = resolve_artifact(settings.project.output_path, run_id, artifact_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    headers = {"Content-Disposition": f'attachment; filename="{path.name}"'} if download else None
    if path.suffix == ".json":
        try:
            content = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=500, detail="Generated JSON artifact is malformed") from exc
        return JSONResponse(content=content, headers=headers)
    return PlainTextResponse(path.read_text(encoding="utf-8"), media_type=media_type, headers=headers)


@router.post(
    "/api/research-jobs",
    response_model=ResearchJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def create_research(
    request_body: TopicRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    runner: ResearchRunner = Depends(get_research_runner),
) -> ResearchJobResponse:
    try:
        job = create_research_job(settings, request_body)
    except ActiveJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    background_tasks.add_task(execute_research_job, settings, job.job_id, runner=runner)
    return job


@router.post(
    "/api/runs/{source_run_id}/outline-jobs",
    response_model=OutlineJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def create_outline(
    source_run_id: str,
    request_body: OutlineJobRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    selection_builder: SelectionBuilder = Depends(get_selection_builder),
    narrative_runner: NarrativeRunner = Depends(get_narrative_runner),
) -> OutlineJobResponse:
    if request_body.source_run_id != source_run_id:
        raise HTTPException(status_code=400, detail="경로와 요청의 source_run_id가 일치하지 않습니다.")
    try:
        job = create_outline_job(settings, request_body)
    except ActiveJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(
        execute_outline_job, settings, job.job_id,
        selection_builder=selection_builder, narrative_runner=narrative_runner,
    )
    return job


@router.post(
    "/api/runs/{source_run_id}/script-jobs",
    response_model=ScriptJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def create_script(
    source_run_id: str,
    request_body: ScriptJobRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    revision_builder: NarrativeRevisionBuilder = Depends(get_revision_builder),
    script_runner: ScriptRunner = Depends(get_script_runner),
) -> ScriptJobResponse:
    if request_body.source_run_id != source_run_id:
        raise HTTPException(status_code=400, detail="경로와 요청의 source_run_id가 일치하지 않습니다.")
    try:
        job = create_script_job(settings, request_body)
    except ActiveJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(
        execute_script_job, settings, job.job_id,
        revision_builder=revision_builder, script_runner=script_runner,
    )
    return job


@router.post(
    "/api/runs/{source_run_id}/validation-jobs",
    response_model=ValidationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def create_validation(
    source_run_id: str,
    request_body: ValidationJobRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    validation_runner: ValidationRunner = Depends(get_validation_runner),
) -> ValidationJobResponse:
    if request_body.source_run_id != source_run_id:
        raise HTTPException(status_code=400, detail="경로와 요청의 source_run_id가 일치하지 않습니다.")
    try:
        job = create_validation_job(settings, request_body)
    except ActiveJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(
        execute_validation_job, settings, job.job_id, validation_runner=validation_runner,
    )
    return job


@router.post(
    "/api/runs/{source_run_id}/citation-revision-jobs",
    response_model=CitationRevisionJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["jobs"],
)
def create_citation_revision(
    source_run_id: str,
    request_body: CitationRevisionJobRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    revision_builder: CitationRevisionBuilder = Depends(get_citation_revision_builder),
    validation_runner: ValidationRunner = Depends(get_validation_runner),
) -> CitationRevisionJobResponse:
    if request_body.source_run_id != source_run_id:
        raise HTTPException(status_code=400, detail="경로와 요청의 source_run_id가 일치하지 않습니다.")
    try:
        job = create_citation_revision_job(settings, request_body)
    except ActiveJobError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(
        execute_citation_revision_job,
        settings,
        job.job_id,
        revision_builder=revision_builder,
        validation_runner=validation_runner,
    )
    return job


@router.get("/api/jobs", response_model=ResearchJobListResponse, tags=["jobs"])
def jobs(
    limit: int = Query(default=50, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> ResearchJobListResponse:
    return list_research_jobs(settings.project.database_path, limit=limit)


def _job_or_404(settings: Settings, job_id: str) -> PipelineJobResponse:
    try:
        return get_research_job(settings.project.database_path, job_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/jobs/{job_id}", response_model=PipelineJobResponse, tags=["jobs"])
def job_detail(job_id: str, settings: Settings = Depends(get_settings)) -> PipelineJobResponse:
    return _job_or_404(settings, job_id)


@router.get("/api/jobs/{job_id}/status", response_model=PipelineJobResponse, tags=["jobs"])
def job_status(job_id: str, settings: Settings = Depends(get_settings)) -> PipelineJobResponse:
    return _job_or_404(settings, job_id)
