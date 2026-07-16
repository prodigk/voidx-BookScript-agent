"""Inspect source-aware FTS5 keyword search results."""

import argparse

from app.config import load_settings
from app.retrieval.keyword_search import keyword_search


def main() -> None:
    parser = argparse.ArgumentParser(description="SQLite FTS5 검색 결과 검사")
    parser.add_argument("--query", required=True)
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    settings = load_settings()
    results = keyword_search(settings.project.database_path, args.query, args.limit)
    if not results:
        print("검색 결과가 없습니다.")
    for index, result in enumerate(results, start=1):
        heading = " > ".join(result.heading_path) or "(heading 없음)"
        print(f"[{index}] {result.title} / {result.author} | score={result.score:.6f}")
        print(f"    {result.source_file}:{result.start_line}-{result.end_line} | {heading}")
        print(f"    {result.content.replace(chr(10), ' ')[:240]}")


if __name__ == "__main__":
    main()
