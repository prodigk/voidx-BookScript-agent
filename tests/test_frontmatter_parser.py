import pytest

from app.ingestion.frontmatter_parser import parse_frontmatter


def test_parses_korean_yaml_frontmatter() -> None:
    parsed = parse_frontmatter("---\ntitle: 생각의 지도\ntags: [문화, 심리]\n---\n# 본문")
    assert parsed.metadata["title"] == "생각의 지도"
    assert parsed.metadata["tags"] == ["문화", "심리"]
    assert parsed.has_frontmatter is True


def test_preserves_blank_line_after_frontmatter_for_exact_source_lines() -> None:
    parsed = parse_frontmatter("---\ntitle: 테스트\n---\n\n# 본문\n내용")
    assert parsed.content.startswith("\n# 본문")
    assert parsed.content_start_line == 4


def test_invalid_frontmatter_is_reportable() -> None:
    with pytest.raises(Exception):
        parse_frontmatter("---\ntags: [닫히지 않음\n---\n본문")
