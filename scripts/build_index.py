"""Build the configured Markdown index."""

from app.config import load_settings
from app.storage.indexer import build_index
from app.utils.logging import configure_logging


if __name__ == "__main__":
    settings = load_settings()
    configure_logging(settings.logging.level)
    result = build_index(settings)
    print(
        f"Index complete: discovered={result.discovered}, indexed={result.indexed}, "
        f"unchanged={result.unchanged}, deleted={result.deleted}, "
        f"chunks={result.chunks}, failed={len(result.failures)}"
    )
