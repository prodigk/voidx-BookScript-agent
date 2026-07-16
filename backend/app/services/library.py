"""Read local library and SQLite status without exposing configured paths."""

from __future__ import annotations

from datetime import UTC, datetime

from app.config import Settings
from app.ingestion.markdown_loader import discover_markdown_files
from app.storage.database import connect_database
from backend.app.schemas import LibraryStatusResponse


def get_library_status(settings: Settings) -> LibraryStatusResponse:
    """Return counts required by the future library status screen."""
    library_available = settings.project.library_path.is_dir()
    source_count = len(discover_markdown_files(
        settings.project.library_path, settings.ingestion.ignored_directories,
    )) if library_available else 0
    database_available = settings.project.database_path.is_file()
    book_count = chunk_count = embedding_count = current_embedding_count = 0
    last_indexed_at = None
    if database_available:
        with connect_database(settings.project.database_path) as connection:
            book_count = int(connection.execute("SELECT COUNT(*) FROM books").fetchone()[0])
            chunk_count = int(connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
            embedding_count = int(connection.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0])
            current_embedding_count = int(connection.execute(
                "SELECT COUNT(*) FROM embeddings WHERE model = ? AND dimensions = ?",
                (settings.embedding.model, settings.embedding.dimensions),
            ).fetchone()[0])
            value = connection.execute("SELECT MAX(updated_at) FROM books").fetchone()[0]
            if value:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                last_indexed_at = parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
    return LibraryStatusResponse(
        library_available=library_available,
        database_available=database_available,
        source_file_count=source_count,
        book_count=book_count,
        chunk_count=chunk_count,
        embedding_count=embedding_count,
        current_embedding_count=current_embedding_count,
        embedding_model=settings.embedding.model,
        embedding_dimensions=settings.embedding.dimensions,
        last_indexed_at=last_indexed_at,
    )
