from pathlib import Path

from app.ingestion.frontmatter_parser import parse_frontmatter
from app.ingestion.metadata_parser import analyze_headings, extract_book_metadata


def test_frontmatter_has_metadata_priority() -> None:
    root = Path("tests/fixtures/library")
    path = root / "심리" / "미움받을-용기.md"
    parsed = parse_frontmatter(path.read_text(encoding="utf-8"))
    book = extract_book_metadata(path, parsed, root)
    assert book.title == "미움받을 용기"
    assert book.author == "기시미 이치로"
    assert book.category == ["심리", "자기계발"]
    assert book.tags == ["아들러", "인정 욕구"]


def test_infers_title_author_and_category() -> None:
    root = Path("tests/fixtures/library")
    path = root / "철학" / "행복론.md"
    parsed = parse_frontmatter(path.read_text(encoding="utf-8"))
    book = extract_book_metadata(path, parsed, root)
    assert (book.title, book.author, book.category) == ("행복론", "알랭", ["철학"])


def test_filename_is_title_fallback(tmp_path: Path) -> None:
    path = tmp_path / "이름으로 추론.md"
    path.write_text("본문뿐입니다.", encoding="utf-8")
    book = extract_book_metadata(path, parse_frontmatter("본문뿐입니다."), tmp_path)
    assert book.title == "이름으로 추론"
    assert book.author == "unknown"


def test_analyzes_heading_levels_and_lines() -> None:
    headings = analyze_headings("서문\n# 첫 장\n본문\n## 세부 주제")
    assert [(item.level, item.text, item.line) for item in headings] == [
        (1, "첫 장", 2),
        (2, "세부 주제", 4),
    ]
