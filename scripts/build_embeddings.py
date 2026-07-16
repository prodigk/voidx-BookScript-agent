"""Generate and cache embeddings for indexed chunks."""

from app.config import load_settings
from app.storage.embedding_index import build_embeddings
from app.utils.logging import configure_logging


if __name__ == "__main__":
    settings = load_settings()
    configure_logging(settings.logging.level)
    result = build_embeddings(settings)
    print(
        f"Embedding complete: discovered={result.discovered}, embedded={result.embedded}, "
        f"cached={result.cached}, stale_deleted={result.deleted_stale}, tokens={result.tokens}, "
        f"model={result.model}, dimensions={result.dimensions}"
    )
