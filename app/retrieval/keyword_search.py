"""Inspectable SQLite FTS5 keyword search."""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.schemas.chunk import SearchResult
from app.storage.database import connect_database


def _fts_query(query: str) -> str:
    tokens = re.findall(r"[\w가-힣]+", query, flags=re.UNICODE)
    if not tokens:
        raise ValueError("검색어에는 문자나 숫자가 포함되어야 합니다.")
    # Prefix matching lets Korean search terms match tokens with attached particles
    # (for example, "욕구" matches "욕구에서").
    return " AND ".join(f'"{token}"*' for token in tokens)


def keyword_search(database_path: Path, query: str, limit: int = 10) -> list[SearchResult]:
    """Search indexed chunks and expose relevance and source traceability."""
    if limit < 1 or limit > 100:
        raise ValueError("limit은 1에서 100 사이여야 합니다.")
    sql = """
        SELECT f.chunk_id, f.book_id, b.title, b.author, b.source_file,
               c.heading_path, c.start_line, c.end_line, c.content, c.content_hash,
               -bm25(chunks_fts, 0.0, 0.0, 2.0, 1.0, 1.5, 1.0) AS score
        FROM chunks_fts AS f
        JOIN chunks AS c ON c.id = f.chunk_id
        JOIN books AS b ON b.id = f.book_id
        WHERE chunks_fts MATCH ?
        ORDER BY bm25(chunks_fts, 0.0, 0.0, 2.0, 1.0, 1.5, 1.0)
        LIMIT ?
    """
    with connect_database(database_path) as connection:
        rows = connection.execute(sql, (_fts_query(query), limit)).fetchall()
    return [
        SearchResult(
            chunk_id=row["chunk_id"], book_id=row["book_id"], title=row["title"],
            author=row["author"], source_file=Path(row["source_file"]),
            heading_path=json.loads(row["heading_path"]), start_line=row["start_line"],
            end_line=row["end_line"], content=row["content"], content_hash=row["content_hash"],
            score=row["score"],
        )
        for row in rows
    ]
