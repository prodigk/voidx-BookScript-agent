"""YAML frontmatter parsing."""

from dataclasses import dataclass
from typing import Any

import frontmatter


@dataclass(frozen=True)
class ParsedMarkdown:
    metadata: dict[str, Any]
    content: str
    has_frontmatter: bool
    content_start_line: int
    raw_text: str


def parse_frontmatter(text: str) -> ParsedMarkdown:
    """Parse frontmatter while retaining ordinary Markdown content."""
    has_frontmatter = text.startswith("---\n") or text.startswith("---\r\n")
    post = frontmatter.loads(text)
    content_start_line = 1
    content = text
    if has_frontmatter:
        lines = text.splitlines(keepends=True)
        closing_index = next(
            (index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---"),
            0,
        )
        content_start_line = closing_index + 2
        content = "".join(lines[closing_index + 1 :])
    return ParsedMarkdown(dict(post.metadata), content, has_frontmatter, content_start_line, text)
