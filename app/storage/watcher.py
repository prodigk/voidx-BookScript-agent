"""Polling watcher for continuous incremental indexing."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.ingestion.markdown_loader import discover_markdown_files
from app.storage.indexer import IndexSummary, build_index
from app.storage.embedding_index import EmbeddingSummary, build_embeddings
from app.llm.embeddings import EmbeddingProvider

LOGGER = logging.getLogger(__name__)
Snapshot = dict[str, tuple[int, int]]


def library_snapshot(settings: Settings) -> Snapshot:
    """Capture relative path, modification time, and size without reading file content."""
    root = settings.project.library_path
    snapshot: Snapshot = {}
    for path in discover_markdown_files(root, settings.ingestion.ignored_directories):
        try:
            stat = path.stat()
            snapshot[path.relative_to(root).as_posix()] = (stat.st_mtime_ns, stat.st_size)
        except OSError as exc:
            LOGGER.warning("Could not inspect %s during watch scan: %s", path, exc)
    return snapshot


def watch_index(
    settings: Settings,
    interval_seconds: float | None = None,
    *,
    max_scans: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    on_update: Callable[[IndexSummary], None] | None = None,
    sync_embeddings: bool = False,
    embedding_provider: EmbeddingProvider | None = None,
    on_embedding_update: Callable[[EmbeddingSummary], None] | None = None,
) -> list[IndexSummary]:
    """Continuously detect library changes and run the safe incremental indexer.

    ``max_scans`` and injected callbacks exist to make the loop deterministically testable.
    Production callers leave ``max_scans`` unset and stop with Ctrl-C.
    """
    interval = interval_seconds or settings.indexing.watch_interval_seconds
    if interval <= 0:
        raise ValueError("watch interval must be greater than zero")
    summaries: list[IndexSummary] = []
    previous = library_snapshot(settings)
    initial = build_index(settings)
    summaries.append(initial)
    if on_update:
        on_update(initial)
    if sync_embeddings:
        embedding_summary = build_embeddings(settings, embedding_provider)
        if on_embedding_update:
            on_embedding_update(embedding_summary)
    scans = 0
    while max_scans is None or scans < max_scans:
        sleep(interval)
        current = library_snapshot(settings)
        scans += 1
        if current == previous:
            continue
        LOGGER.info("Markdown library change detected; running incremental index")
        summary = build_index(settings)
        summaries.append(summary)
        if on_update:
            on_update(summary)
        if sync_embeddings:
            embedding_summary = build_embeddings(settings, embedding_provider)
            if on_embedding_update:
                on_embedding_update(embedding_summary)
        previous = current
    return summaries
