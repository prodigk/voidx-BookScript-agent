"""Compare Phase 2 keyword and Phase 3 hybrid retrieval baselines."""

from pathlib import Path

from app.config import load_settings
from app.retrieval.evaluation import evaluate_keyword_search, evaluate_search, load_evaluation_dataset, write_evaluation_report
from app.retrieval.hybrid_search import hybrid_search


if __name__ == "__main__":
    settings = load_settings()
    dataset = load_evaluation_dataset(Path("data/evaluations/keyword_baseline.yaml"))
    keyword = evaluate_keyword_search(settings.project.database_path, dataset)
    hybrid = evaluate_search(dataset, lambda query: hybrid_search(settings, query, limit=100))
    write_evaluation_report(hybrid, Path("reports/hybrid_retrieval_baseline.md"))
    print(f"keyword_recall_at_5={keyword.mean_recall_at_5:.3f}")
    print(f"keyword_recall_at_10={keyword.mean_recall_at_10:.3f}")
    print(f"hybrid_recall_at_5={hybrid.mean_recall_at_5:.3f}")
    print(f"hybrid_recall_at_10={hybrid.mean_recall_at_10:.3f}")
    print("reports/hybrid_retrieval_baseline.md")
