"""FastAPI application factory for the local processing backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agents.phase4 import run_phase4
from app.agents.phase5 import generate_narrative
from app.agents.phase6 import generate_script
from app.agents.phase7 import validate_script_run
from app.config import Settings, load_settings
from backend.app.api.routes import router
from backend.app.services.jobs import (
    NarrativeRunner,
    NarrativeRevisionBuilder,
    ResearchRunner,
    SelectionBuilder,
    ScriptRunner,
    ValidationRunner,
    initialize_job_store,
)
from backend.app.services.narrative_revision import prepare_narrative_revision
from backend.app.services.selection import prepare_selection_revision


def create_app(
    settings: Settings | None = None,
    *,
    research_runner: ResearchRunner = run_phase4,
    selection_builder: SelectionBuilder = prepare_selection_revision,
    narrative_runner: NarrativeRunner = generate_narrative,
    revision_builder: NarrativeRevisionBuilder = prepare_narrative_revision,
    script_runner: ScriptRunner = generate_script,
    validation_runner: ValidationRunner = validate_script_run,
) -> FastAPI:
    """Create an explicitly configured local API application."""
    resolved = settings or load_settings()
    application = FastAPI(
        title="YouTube Book Script Agent API",
        version="0.1.0",
        description="Local-only API for library inspection and evidence-first research jobs.",
    )
    application.state.settings = resolved
    application.state.research_runner = research_runner
    application.state.selection_builder = selection_builder
    application.state.narrative_runner = narrative_runner
    application.state.revision_builder = revision_builder
    application.state.script_runner = script_runner
    application.state.validation_runner = validation_runner
    initialize_job_store(resolved.project.database_path)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.backend.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.include_router(router)
    return application


app = create_app()
