"""Phase 0 SQLite initialization."""

import sqlite3
from pathlib import Path


def initialize_database(path: Path) -> None:
    """Create the Phase 2 book, chunk, and FTS5 tables."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT NOT NULL,
                tags TEXT NOT NULL,
                source_file TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                book_id TEXT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                heading_path TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chunks_book_id ON chunks(book_id);
            CREATE TABLE IF NOT EXISTS embeddings (
                chunk_id TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
                model TEXT NOT NULL,
                dimensions INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                vector BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chunk_id, model, dimensions)
            );
            CREATE INDEX IF NOT EXISTS idx_embeddings_model ON embeddings(model, dimensions);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                book_id UNINDEXED,
                title,
                author,
                heading_path,
                content,
                tokenize='unicode61'
            );
            """
        )


def connect_database(path: Path) -> sqlite3.Connection:
    """Open a row-based SQLite connection with foreign keys enabled."""
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection
