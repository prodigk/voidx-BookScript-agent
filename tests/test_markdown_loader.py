from pathlib import Path

from app.ingestion.markdown_loader import discover_markdown_files, read_markdown


def test_discovers_markdown_recursively_and_preserves_korean() -> None:
    root = Path("tests/fixtures/library")
    files = discover_markdown_files(root)
    assert [path.name for path in files] == ["미움받을-용기.md", "행복론.md"]
    assert "인정 욕구" in read_markdown(files[0])


def test_excludes_hidden_files(tmp_path: Path) -> None:
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "secret.md").write_text("# 숨김", encoding="utf-8")
    (tmp_path / "visible.md").write_text("# 공개", encoding="utf-8")
    assert discover_markdown_files(tmp_path) == [tmp_path / "visible.md"]
