from pathlib import Path

from app.config import ChunkingSettings, ProjectSettings, Settings
from app.retrieval.evaluation import evaluate_keyword_search
from app.schemas.evaluation import EvaluationDataset
from app.storage.indexer import build_index


def test_evaluation_calculates_recall_by_source_path(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "책.md").write_text("# 책\n인정 욕구와 타인의 평가", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(library_path=library, database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=5, target_chars=50, max_chars=100, overlap_chars=0),
    )
    build_index(settings)
    dataset = EvaluationDataset.model_validate(
        {"cases": [{"topic": "평가", "query": "인정 욕구", "expected_books": [{"label": "책", "source_contains": "책.md"}]}]}
    )
    result = evaluate_keyword_search(settings.project.database_path, dataset)
    assert result.mean_recall_at_5 == 1.0
    assert result.mean_recall_at_10 == 1.0
    assert result.cases[0].missing_at_10 == []


def test_evaluation_ranks_unique_books_not_duplicate_chunks(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "첫책.md").write_text("# 1\n검색어\n\n## 2\n검색어\n\n## 3\n검색어", encoding="utf-8")
    (library / "둘째책.md").write_text("# 책\n검색어", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(library_path=library, database_path=tmp_path / "db.sqlite"),
        chunking=ChunkingSettings(min_chars=1, target_chars=10, max_chars=20, overlap_chars=0),
    )
    build_index(settings)
    dataset = EvaluationDataset.model_validate(
        {"cases": [{"topic": "중복", "query": "검색어", "expected_books": [{"label": "둘째", "source_contains": "둘째책.md"}]}]}
    )
    result = evaluate_keyword_search(settings.project.database_path, dataset)
    assert result.mean_recall_at_5 == 1.0
    assert len(result.cases[0].returned_titles) == 2
