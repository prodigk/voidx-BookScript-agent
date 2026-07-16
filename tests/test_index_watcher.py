from pathlib import Path

from app.config import ChunkingSettings, IndexingSettings, ProjectSettings, Settings
from app.retrieval.keyword_search import keyword_search
from app.storage.watcher import watch_index
from app.llm.embeddings import EmbeddingBatch


class FakeEmbeddingProvider:
    def embed(self, texts: list[str]) -> EmbeddingBatch:
        return EmbeddingBatch([[1.0, 0.0] for _ in texts], len(texts))


def test_watcher_reflects_new_updated_and_deleted_markdown(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    original = library / "기존.md"
    original.write_text("# 기존\n처음 내용", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(library_path=library, database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=1, target_chars=50, max_chars=100, overlap_chars=0),
        indexing=IndexingSettings(watch_interval_seconds=1),
    )
    scan = 0

    def mutate(_: float) -> None:
        nonlocal scan
        scan += 1
        if scan == 1:
            original.write_text("# 기존\n수정된내용", encoding="utf-8")
        elif scan == 2:
            (library / "새책.md").write_text("# 새책\n새로운내용", encoding="utf-8")
        elif scan == 3:
            original.unlink()

    summaries = watch_index(settings, max_scans=3, sleep=mutate)
    assert len(summaries) == 4
    assert keyword_search(settings.project.database_path, "새로운내용", 10)
    assert not keyword_search(settings.project.database_path, "수정된내용", 10)
    assert summaries[-1].deleted == 1


def test_watcher_can_sync_embeddings_when_explicitly_enabled(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "책.md").write_text("# 책\n의미 내용", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(library_path=library, database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=1, target_chars=50, max_chars=100, overlap_chars=0),
        indexing=IndexingSettings(watch_interval_seconds=1),
        embedding={"model": "fake", "dimensions": 2, "batch_size": 10, "max_retries": 0},
    )
    updates = []
    watch_index(
        settings, max_scans=0, sync_embeddings=True,
        embedding_provider=FakeEmbeddingProvider(), on_embedding_update=updates.append,
    )
    assert updates[0].embedded == 1
