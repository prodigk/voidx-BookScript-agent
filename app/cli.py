"""Command-line entry points for implemented phases."""

from pathlib import Path

import typer

from app.config import load_settings
from app.ingestion.audit import audit_library
from app.retrieval.keyword_search import keyword_search
from app.retrieval.hybrid_search import hybrid_search
from app.retrieval.semantic_search import semantic_search
from app.storage.database import initialize_database
from app.storage.embedding_index import build_embeddings
from app.storage.indexer import build_index
from app.storage.watcher import watch_index
from app.agents.phase4 import run_phase4
from app.agents.phase5 import generate_narrative
from app.agents.phase6 import create_script_revision, generate_script
from app.agents.phase7 import create_validated_revision, validate_script_run
from app.agents.editorial import suggest_topics
from app.insights.registry import sync_insights
from app.schemas.topic import TopicRequest
from app.utils.logging import configure_logging
from app.video.manifest import prepare_video_manifest

app = typer.Typer(help="Local-first YouTube Book Script Agent")


@app.command("sync-insights")
def sync_insights_command(
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Discover insight Markdown files and update the content-hash manifest."""
    settings = load_settings(config)
    _, summary = sync_insights(settings.insights)
    typer.echo(
        f"Insight sync: discovered={summary.discovered}, added={summary.added}, "
        f"updated={summary.updated}, unchanged={summary.unchanged}, deleted={summary.deleted}"
    )
    typer.echo(summary.manifest_path)


@app.command("suggest-topics")
def suggest_topics_command(
    count: int = typer.Option(10, "--count", min=3, max=20),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Generate topic candidates from the current editorial insight profile."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    result = suggest_topics(settings, count=count)
    typer.echo(f"Topic ideas: profile={result.profile}, count={len(result.ideas)}")
    typer.echo(settings.insights.manifest_path.parent / "topic_ideas.json")
    typer.echo(settings.project.output_path.parent / "reports" / "topic_ideas.md")


@app.command("audit-library")
def audit_library_command(
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Analyze the local Markdown library and write Phase 1 artifacts."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    books, failures = audit_library(settings)
    typer.echo(f"Audit complete: {len(books)} parsed, {len(failures)} failed")
    typer.echo(settings.project.audit_report_path)
    typer.echo(settings.project.metadata_path)


@app.command("init-db")
def init_db_command(
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Initialize the local Phase 0 SQLite database file."""
    settings = load_settings(config)
    initialize_database(settings.project.database_path)
    typer.echo(settings.project.database_path)


@app.command("build-index")
def build_index_command(
    full: bool = typer.Option(False, "--full", help="기존 인덱스를 비우고 전체 재구축"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Build or incrementally update the local Markdown index."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    summary = build_index(settings, full=full)
    typer.echo(
        f"Index complete: discovered={summary.discovered}, indexed={summary.indexed}, "
        f"unchanged={summary.unchanged}, deleted={summary.deleted}, "
        f"chunks={summary.chunks}, failed={len(summary.failures)}"
    )


@app.command("search")
def search_command(
    query: str = typer.Option(..., "--query", "-q", help="FTS5 검색어"),
    limit: int = typer.Option(10, "--limit", min=1, max=100),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Search indexed chunks and print source-aware results."""
    settings = load_settings(config)
    results = keyword_search(settings.project.database_path, query, limit)
    if not results:
        typer.echo("검색 결과가 없습니다.")
        return
    for index, result in enumerate(results, start=1):
        heading = " > ".join(result.heading_path) or "(heading 없음)"
        excerpt = result.content.replace("\n", " ")[:240]
        typer.echo(f"[{index}] {result.title} / {result.author} | score={result.score:.6f}")
        typer.echo(f"    {result.source_file}:{result.start_line}-{result.end_line} | {heading}")
        typer.echo(f"    {excerpt}")


@app.command("watch-index")
def watch_index_command(
    interval: float | None = typer.Option(None, "--interval", min=0.1, help="변경 확인 주기(초)"),
    embeddings: bool = typer.Option(False, "--embeddings", help="변경 청크의 임베딩도 자동 생성(API 비용 발생)"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Continuously detect Markdown additions, updates, and deletions."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    seconds = interval or settings.indexing.watch_interval_seconds
    typer.echo(f"Watching {settings.project.library_path} every {seconds:g}s (종료: Ctrl+C)")

    def show(summary) -> None:
        typer.echo(
            f"Index sync: discovered={summary.discovered}, indexed={summary.indexed}, "
            f"unchanged={summary.unchanged}, deleted={summary.deleted}, "
            f"chunks={summary.chunks}, failed={len(summary.failures)}"
        )

    def show_embeddings(summary) -> None:
        typer.echo(
            f"Embedding sync: embedded={summary.embedded}, cached={summary.cached}, "
            f"tokens={summary.tokens}, model={summary.model}"
        )

    try:
        watch_index(
            settings, seconds, on_update=show, sync_embeddings=embeddings,
            on_embedding_update=show_embeddings,
        )
    except KeyboardInterrupt:
        typer.echo("Index watcher stopped.")


@app.command("build-embeddings")
def build_embeddings_command(
    full: bool = typer.Option(False, "--full", help="현재 모델의 벡터 캐시 전체 재생성"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Generate missing embeddings for indexed chunks."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    summary = build_embeddings(settings, full=full)
    typer.echo(
        f"Embedding complete: discovered={summary.discovered}, embedded={summary.embedded}, "
        f"cached={summary.cached}, stale_deleted={summary.deleted_stale}, tokens={summary.tokens}, "
        f"model={summary.model}, dimensions={summary.dimensions}"
    )


def _show_results(results, hybrid: bool = False) -> None:
    if not results:
        typer.echo("검색 결과가 없습니다.")
        return
    for index, result in enumerate(results, start=1):
        heading = " > ".join(result.heading_path) or "(heading 없음)"
        components = ""
        if hybrid:
            components = (
                f" kw={result.keyword_score:.3f} sem={result.semantic_score:.3f} "
                f"meta={result.metadata_score:.3f} div={result.diversity_score:.3f}"
            )
        typer.echo(f"[{index}] {result.title} / {result.author} | score={result.score:.6f}{components}")
        typer.echo(f"    {result.source_file}:{result.start_line}-{result.end_line} | {heading}")
        typer.echo(f"    {result.content.replace(chr(10), ' ')[:240]}")


@app.command("semantic-search")
def semantic_search_command(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(10, "--limit", min=1, max=100),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    settings = load_settings(config)
    _show_results(semantic_search(settings, query, limit))


@app.command("hybrid-search")
def hybrid_search_command(
    query: str = typer.Option(..., "--query", "-q"),
    limit: int = typer.Option(10, "--limit", min=1, max=100),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    settings = load_settings(config)
    _show_results(hybrid_search(settings, query, limit), hybrid=True)


@app.command("research")
def research_command(
    topic: str = typer.Option(..., "--topic"),
    duration: int = typer.Option(12, "--duration", min=3, max=60),
    books: int = typer.Option(3, "--books", min=2, max=4),
    tone: str = typer.Option("사색적", "--tone"),
    audience: str = typer.Option("일반 성인", "--audience"),
    lens: list[str] = typer.Option(None, "--lens", help="원하는 관점(반복 지정 가능)"),
    emotional_effect: list[str] = typer.Option(None, "--emotional-effect", help="원하는 정서 효과"),
    exclude_lens: list[str] = typer.Option(None, "--exclude-lens", help="제외할 관점"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Run Phase 4 topic analysis, evidence curation, and book selection."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    result = run_phase4(
        settings,
        TopicRequest(
            topic=topic, duration_minutes=duration, target_book_count=books, tone=tone, audience=audience,
            desired_lenses=lens or [], desired_emotional_effects=emotional_effect or [],
            excluded_lenses=exclude_lens or [],
        ),
    )
    typer.echo(f"status={result.status}")
    typer.echo(f"run_id={result.run_id}")
    typer.echo(settings.project.output_path / result.run_id)


@app.command("generate-outline")
def generate_outline_command(
    run_id: str = typer.Option(..., "--run-id", help="완료된 Phase 4 실행 ID"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Generate the Phase 5 narrative plan and evidence-linked outline."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    plan = generate_narrative(settings, run_id)
    run_dir = settings.project.output_path / run_id
    typer.echo(f"Outline complete: sections={len(plan.sections)}, seconds={plan.total_seconds}")
    typer.echo(run_dir / "narrative.json")
    typer.echo(run_dir / "outline.md")


@app.command("generate-script")
def generate_script_command(
    run_id: str = typer.Option(..., "--run-id", help="완료된 Phase 5 실행 ID"),
    revision: bool = typer.Option(False, "--revision", help="기존 실행을 보존하고 새 대본 리비전 생성"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Generate Phase 6 internal and clean narration scripts."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    if revision:
        run_id = create_script_revision(settings, run_id)
    script = generate_script(settings, run_id)
    run_dir = settings.project.output_path / run_id
    typer.echo(f"run_id={run_id}")
    typer.echo(f"Script complete: sections={len(script.sections)}, seconds={script.target_duration_seconds}")
    typer.echo(run_dir / "script_with_sources.md")
    typer.echo(run_dir / "script.md")


@app.command("validate-script")
def validate_script_command(
    run_id: str = typer.Option(..., "--run-id", help="완료된 Phase 6 실행 ID"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Validate Phase 6 citations against local source chunks."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    result = validate_script_run(settings, run_id)
    run_dir = settings.project.output_path / run_id
    typer.echo(
        f"Validation complete: status={result.status}, valid={result.valid_count}, "
        f"review={result.needs_review_count}, invalid={result.invalid_count}"
    )
    typer.echo(run_dir / "citations.json")
    typer.echo(run_dir / "validation_report.md")


@app.command("revise-script")
def revise_script_command(
    run_id: str = typer.Option(..., "--run-id", help="needs_revision 상태의 Phase 7 실행 ID"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Create a new immutable run with targeted citation revisions."""
    settings = load_settings(config)
    configure_logging(settings.logging.level)
    revision_id = create_validated_revision(settings, run_id)
    typer.echo(f"run_id={revision_id}")
    typer.echo(settings.project.output_path / revision_id)


@app.command("prepare-video")
def prepare_video_command(
    run_id: str = typer.Option(..., "--run-id", help="approved 상태의 Phase 7 실행 ID"),
    sync_project: bool = typer.Option(True, "--sync-project/--no-sync-project"),
    config: Path = typer.Option(Path("config/default.yaml"), exists=True, dir_okay=False),
) -> None:
    """Convert an approved script run into the current Remotion video manifest."""
    settings = load_settings(config)
    manifest = prepare_video_manifest(settings, run_id, sync_project=sync_project)
    typer.echo(
        f"Video manifest: scenes={len(manifest.scenes)}, frames={manifest.duration_frames}, "
        f"size={manifest.width}x{manifest.height}"
    )
    typer.echo(settings.project.output_path / run_id / "video_manifest.json")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
