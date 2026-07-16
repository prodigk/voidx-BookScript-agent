"""Run the Phase 1 library audit with configured paths."""

from app.config import load_settings
from app.ingestion.audit import audit_library
from app.utils.logging import configure_logging


if __name__ == "__main__":
    settings = load_settings()
    configure_logging(settings.logging.level)
    books, failures = audit_library(settings)
    print(f"Audit complete: {len(books)} parsed, {len(failures)} failed")
    print(settings.project.audit_report_path)
    print(settings.project.metadata_path)
