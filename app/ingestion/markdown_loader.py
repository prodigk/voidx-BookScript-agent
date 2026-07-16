"""Safe recursive discovery and loading of local Markdown files."""

from pathlib import Path


def discover_markdown_files(root: Path, ignored_directories: set[str] | None = None) -> list[Path]:
    """Return visible Markdown files recursively in deterministic order."""
    ignored = ignored_directories or set()
    if not root.exists():
        return []
    return sorted(
        path
        for path in root.rglob("*.md")
        if path.is_file()
        and not any(part.startswith(".") or part in ignored for part in path.relative_to(root).parts)
    )


def read_markdown(path: Path) -> str:
    """Read a Markdown document as UTF-8, surfacing decoding errors to the caller."""
    return path.read_text(encoding="utf-8")
