import sqlite3
from pathlib import Path

from app.config import ChunkingSettings, ProjectSettings, Settings
from app.retrieval.keyword_search import keyword_search
from app.storage.indexer import build_index


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project=ProjectSettings(library_path=tmp_path / "library", database_path=tmp_path / "index.sqlite"),
        chunking=ChunkingSettings(min_chars=5, target_chars=50, max_chars=100, overlap_chars=10),
    )


def test_creates_tables_indexes_and_searches_korean(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.project.library_path.mkdir()
    (settings.project.library_path / "용기.md").write_text(
        "---\ntitle: 미움받을 용기\nauthor: 기시미 이치로\n---\n# 인간관계\n타인의 인정 욕구에서 벗어나야 한다.", encoding="utf-8"
    )
    summary = build_index(settings)
    assert (summary.indexed, summary.chunks, len(summary.failures)) == (1, 1, 0)
    with sqlite3.connect(settings.project.database_path) as connection:
        names = {row[0] for row in connection.execute("SELECT name FROM sqlite_master")}
    assert {"books", "chunks", "chunks_fts"} <= names
    results = keyword_search(settings.project.database_path, "인정 욕구", 10)
    assert results[0].title == "미움받을 용기"
    assert results[0].source_file == Path("용기.md")
    assert results[0].start_line == 6


def test_incremental_update_skips_unchanged_replaces_changed_and_deletes_missing(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.project.library_path.mkdir()
    path = settings.project.library_path / "책.md"
    path.write_text("# 제목\n첫 내용", encoding="utf-8")
    assert build_index(settings).indexed == 1
    second = build_index(settings)
    assert (second.indexed, second.unchanged) == (0, 1)
    path.write_text("# 제목\n바뀐 검색어", encoding="utf-8")
    changed = build_index(settings)
    assert (changed.indexed, changed.unchanged) == (1, 0)
    assert keyword_search(settings.project.database_path, "바뀐", 10)
    path.unlink()
    deleted = build_index(settings)
    assert deleted.deleted == 1
    assert not keyword_search(settings.project.database_path, "바뀐", 10)
