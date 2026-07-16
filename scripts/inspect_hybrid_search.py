"""Inspect transparent hybrid retrieval scores."""

import argparse

from app.config import load_settings
from app.retrieval.hybrid_search import hybrid_search


def main() -> None:
    parser = argparse.ArgumentParser(description="하이브리드 검색 결과 검사")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    results = hybrid_search(load_settings(), args.query, args.limit)
    for index, result in enumerate(results, start=1):
        print(
            f"[{index}] {result.title} / {result.author} | total={result.score:.4f} "
            f"keyword={result.keyword_score:.4f} semantic={result.semantic_score:.4f} "
            f"metadata={result.metadata_score:.4f} diversity={result.diversity_score:.4f}"
        )
        print(f"    {result.source_file}:{result.start_line}-{result.end_line} | {' > '.join(result.heading_path)}")
        print(f"    {result.content.replace(chr(10), ' ')[:240]}")


if __name__ == "__main__":
    main()
