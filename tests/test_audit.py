from pathlib import Path

import yaml

from app.config import IngestionSettings, LoggingSettings, ProjectSettings, Settings
from app.ingestion.audit import audit_library


def test_audit_writes_outputs_and_continues_after_failure(tmp_path: Path) -> None:
    library = tmp_path / "library"
    library.mkdir()
    (library / "정상.md").write_text("# 정상\n저자: 작가", encoding="utf-8")
    (library / "오류.md").write_text("---\ntags: [broken\n---\n본문", encoding="utf-8")
    settings = Settings(
        project=ProjectSettings(
            library_path=library,
            metadata_path=tmp_path / "metadata/books.yaml",
            audit_report_path=tmp_path / "reports/library_audit.md",
        ),
        logging=LoggingSettings(),
        ingestion=IngestionSettings(),
    )
    books, failures = audit_library(settings)
    assert len(books) == 1
    assert len(failures) == 1
    payload = yaml.safe_load(settings.project.metadata_path.read_text(encoding="utf-8"))
    assert payload["books"][0]["title"] == "정상"
    report = settings.project.audit_report_path.read_text(encoding="utf-8")
    assert "전체 파일 수: 2" in report
    assert "오류.md" in report
