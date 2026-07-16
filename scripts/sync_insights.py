"""Synchronize the editorial insight Markdown manifest."""

from app.config import load_settings
from app.insights.registry import sync_insights


def main() -> None:
    settings = load_settings()
    _, summary = sync_insights(settings.insights)
    print(
        f"discovered={summary.discovered} added={summary.added} updated={summary.updated} "
        f"unchanged={summary.unchanged} deleted={summary.deleted}"
    )
    print(summary.manifest_path)


if __name__ == "__main__":
    main()
