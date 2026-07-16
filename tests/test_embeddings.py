from pathlib import Path

from app.config import ChunkingSettings, EmbeddingSettings, ProjectSettings, Settings
from app.llm.embeddings import EmbeddingBatch
from app.storage.embedding_index import build_embeddings
from app.storage.indexer import build_index


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        self.calls += 1
        return EmbeddingBatch([[float(len(text)), 1.0, 0.0] for text in texts], len(texts))


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project=ProjectSettings(library_path=tmp_path / "library", database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=1, target_chars=50, max_chars=100, overlap_chars=0),
        embedding=EmbeddingSettings(model="fake", dimensions=3, batch_size=2, max_retries=0),
    )


def test_embedding_cache_is_incremental_and_model_scoped(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.project.library_path.mkdir()
    path = settings.project.library_path / "책.md"
    path.write_text("# 책\n처음 내용", encoding="utf-8")
    build_index(settings)
    provider = FakeProvider()
    first = build_embeddings(settings, provider)
    assert (first.embedded, first.cached) == (1, 0)
    second = build_embeddings(settings, provider)
    assert (second.embedded, second.cached) == (0, 1)
    path.write_text("# 책\n수정된 내용", encoding="utf-8")
    build_index(settings)
    third = build_embeddings(settings, provider)
    assert (third.embedded, third.cached) == (1, 0)
