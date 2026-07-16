"""Measure the repeatable Phase 2 FTS5 retrieval baseline."""

import argparse
from pathlib import Path

from app.config import load_settings
from app.retrieval.evaluation import evaluate_keyword_search, load_evaluation_dataset, write_evaluation_report


def main() -> None:
    parser = argparse.ArgumentParser(description="FTS5 검색 Recall 기준선 평가")
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluations/keyword_baseline.yaml"))
    parser.add_argument("--report", type=Path, default=Path("reports/retrieval_baseline.md"))
    args = parser.parse_args()
    settings = load_settings()
    dataset = load_evaluation_dataset(args.dataset)
    result = evaluate_keyword_search(settings.project.database_path, dataset)
    write_evaluation_report(result, args.report)
    print(f"cases={result.case_count}")
    print(f"mean_recall_at_5={result.mean_recall_at_5:.3f}")
    print(f"mean_recall_at_10={result.mean_recall_at_10:.3f}")
    print(f"no_result_cases={result.cases_with_no_results}")
    print(args.report)


if __name__ == "__main__":
    main()
