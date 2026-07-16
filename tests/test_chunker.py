from pathlib import Path

from app.config import ChunkingSettings
from app.ingestion.chunker import chunk_markdown
from app.ingestion.frontmatter_parser import parse_frontmatter
from app.ingestion.metadata_parser import extract_book_metadata


def _book_and_parsed(tmp_path: Path, text: str):
    path = tmp_path / "책.md"
    path.write_text(text, encoding="utf-8")
    parsed = parse_frontmatter(text)
    return extract_book_metadata(path, parsed, tmp_path), parsed


def test_preserves_frontmatter_adjusted_lines_and_heading_path(tmp_path: Path) -> None:
    text = "---\ntitle: 테스트\nauthor: 저자\n---\n# 1부\n소개 문장\n\n## 주제\n인정 욕구에 관한 문장"
    book, parsed = _book_and_parsed(tmp_path, text)
    chunks = chunk_markdown(book, parsed.content, parsed.content_start_line, ChunkingSettings(min_chars=5, target_chars=30, max_chars=60, overlap_chars=0))
    assert chunks[0].heading_path == ["1부"]
    assert (chunks[0].start_line, chunks[0].end_line) == (6, 6)
    assert chunks[1].heading_path == ["1부", "주제"]
    assert (chunks[1].start_line, chunks[1].end_line) == (9, 9)


def test_never_exceeds_maximum_and_uses_overlap(tmp_path: Path) -> None:
    paragraphs = "\n\n".join(["가" * 30, "나" * 30, "다" * 30, "라" * 30])
    book, parsed = _book_and_parsed(tmp_path, f"# 장\n{paragraphs}")
    chunks = chunk_markdown(book, parsed.content, 1, ChunkingSettings(min_chars=20, target_chars=55, max_chars=75, overlap_chars=35))
    assert all(len(chunk.content) <= 75 for chunk in chunks)
    assert len(chunks) >= 2
    assert "나" * 30 in chunks[0].content and "나" * 30 in chunks[1].content


def test_line_range_stays_exact_with_blank_line_after_frontmatter(tmp_path: Path) -> None:
    text = "---\ntitle: 테스트\n---\n\n# 장\n첫 문장\n둘째 문장"
    book, parsed = _book_and_parsed(tmp_path, text)
    chunks = chunk_markdown(
        book, parsed.content, parsed.content_start_line,
        ChunkingSettings(min_chars=5, target_chars=100, max_chars=200, overlap_chars=0),
    )
    assert chunks[0].content == "첫 문장\n둘째 문장"
    assert (chunks[0].start_line, chunks[0].end_line) == (6, 7)
