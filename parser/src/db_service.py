"""Database service layer for the parser.

Provides helpers for upserting books, bulk-inserting chapters, and writing
parse logs to MySQL via SQLAlchemy.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from parser.models.orm import Book, Chapter, ParseLog, engine

logger = logging.getLogger(__name__)

_BATCH_SIZE = 1000


def _session() -> Session:
    return Session(engine)


# ── Book ──────────────────────────────────────────────────────────────────────

def upsert_book(meta: dict) -> int:
    """Insert or update a book record and return its id.

    Uniqueness is determined by (source_site, source_id).

    Args:
        meta: dict with keys matching Book columns.  Required: source_site,
              source_id, title.

    Returns:
        The book's primary key (id).
    """
    with _session() as session:
        book = (
            session.query(Book)
            .filter_by(source_site=meta["source_site"], source_id=meta["source_id"])
            .first()
        )
        if book is None:
            book = Book(
                source_site=meta["source_site"],
                source_id=meta["source_id"],
                title=meta.get("title", ""),
                author=meta.get("author"),
                category=meta.get("category"),
                summary=meta.get("summary"),
                source_url=meta.get("source_url"),
                file_size_bytes=meta.get("file_size_bytes"),
                parse_status="pending",
                first_seen_at=datetime.now(timezone.utc),
                downloaded_at=meta.get("downloaded_at"),
            )
            session.add(book)
        else:
            # Update mutable fields
            for field in ("title", "author", "category", "summary", "source_url", "file_size_bytes"):
                if meta.get(field) is not None:
                    setattr(book, field, meta[field])
            if meta.get("downloaded_at"):
                book.downloaded_at = meta["downloaded_at"]

        session.commit()
        return book.id


def update_parse_status(
    book_id: int,
    status: str,
    total_words: Optional[int] = None,
    detected_encoding: Optional[str] = None,
) -> None:
    """Update a book's parse_status (and optionally total_words / encoding)."""
    with _session() as session:
        book = session.get(Book, book_id)
        if book is None:
            logger.warning("update_parse_status: book_id=%s not found", book_id)
            return
        book.parse_status = status
        if total_words is not None:
            book.total_words = total_words
        if detected_encoding is not None:
            book.detected_encoding = detected_encoding
        if status in ("success", "failed"):
            book.parsed_at = datetime.now(timezone.utc)
        session.commit()


# ── Chapters ──────────────────────────────────────────────────────────────────

def bulk_insert_chapters(book_id: int, chapters: list[dict]) -> int:
    """Bulk-insert chapters using INSERT IGNORE for idempotency.

    Args:
        book_id:  The parent book's id.
        chapters: List of dicts with keys: num, title, content, word_count,
                  content_hash.

    Returns:
        Number of rows actually inserted.
    """
    if not chapters:
        return 0

    inserted = 0
    with _session() as session:
        for i in range(0, len(chapters), _BATCH_SIZE):
            batch = chapters[i : i + _BATCH_SIZE]
            for ch in batch:
                result = session.execute(
                    text(
                        """
                        INSERT IGNORE INTO chapters
                            (book_id, chapter_num, chapter_title, content, content_hash, word_count)
                        VALUES
                            (:book_id, :chapter_num, :chapter_title, :content, :content_hash, :word_count)
                        """
                    ),
                    {
                        "book_id": book_id,
                        "chapter_num": ch["num"],
                        "chapter_title": ch.get("title", ""),
                        "content": ch.get("content", ""),
                        "content_hash": ch.get("content_hash", ""),
                        "word_count": ch.get("word_count", 0),
                    },
                )
                inserted += result.rowcount
        session.commit()
    return inserted


# ── Parse logs ────────────────────────────────────────────────────────────────

def write_log(
    book_id: Optional[int],
    log_type: str,
    message: str,
    detected_encoding: Optional[str] = None,
    parse_duration_ms: Optional[int] = None,
) -> None:
    """Append a row to parse_logs."""
    with _session() as session:
        log = ParseLog(
            book_id=book_id,
            log_type=log_type,
            message=message[:500],
            detected_encoding=detected_encoding,
            parse_duration_ms=parse_duration_ms,
            created_at=datetime.now(timezone.utc),
        )
        session.add(log)
        session.commit()
