"""Load versioned prompts from disk."""

from pathlib import Path


def load_prompt(name: str, root: Path = Path("prompts")) -> str:
    path = root / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")
