"""
Storage module for novelDownloader.

Manages a SQLite database that stores novels and their chapters.
"""
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional

from .models import Chapter, Novel

logger = logging.getLogger(__name__)

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS novels (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    title          TEXT    NOT NULL,
    author         TEXT,
    source_url     TEXT    UNIQUE NOT NULL,
    txt_url        TEXT,
    site_name      TEXT    NOT NULL,
    downloaded_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS chapters (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    novel_id       INTEGER NOT NULL,
    chapter_index  INTEGER NOT NULL,
    title          TEXT    NOT NULL,
    content        TEXT,
    FOREIGN KEY (novel_id) REFERENCES novels (id) ON DELETE CASCADE
);
"""


@contextmanager
def _connect(db_path: str) -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields an open :class:`sqlite3.Connection`."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class Database:
    """High-level interface for persisting novels and chapters."""

    def __init__(self, db_path: str = "novels.db") -> None:
        self.db_path = db_path
        self._init_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _init_schema(self) -> None:
        """Create tables if they do not already exist."""
        with _connect(self.db_path) as conn:
            conn.executescript(_SCHEMA_SQL)
        logger.debug("Database schema initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # Novel operations
    # ------------------------------------------------------------------

    def save_novel(self, novel: Novel) -> Novel:
        """Insert or update *novel* and all of its chapters.

        If a novel with the same ``source_url`` already exists the existing
        record is updated (title, author, txt_url) and its chapters are
        replaced wholesale.

        Returns the *novel* with its ``id`` set.
        """
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with _connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO novels (title, author, source_url, txt_url, site_name, downloaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_url) DO UPDATE SET
                    title        = excluded.title,
                    author       = excluded.author,
                    txt_url      = excluded.txt_url,
                    downloaded_at = excluded.downloaded_at
                RETURNING id
                """,
                (
                    novel.title,
                    novel.author,
                    novel.source_url,
                    novel.txt_url,
                    novel.site_name,
                    now,
                ),
            )
            row = cursor.fetchone()
            novel_id: int = row["id"]

            # Remove old chapters so we can re-insert them cleanly
            conn.execute("DELETE FROM chapters WHERE novel_id = ?", (novel_id,))

            conn.executemany(
                """
                INSERT INTO chapters (novel_id, chapter_index, title, content)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (novel_id, ch.chapter_index, ch.title, ch.content)
                    for ch in novel.chapters
                ],
            )

        novel.id = novel_id
        logger.info(
            "Saved novel '%s' (id=%d, chapters=%d)",
            novel.title,
            novel_id,
            len(novel.chapters),
        )
        return novel

    def get_novel_by_url(self, source_url: str) -> Optional[Novel]:
        """Return the :class:`Novel` stored for *source_url*, or ``None``."""
        with _connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM novels WHERE source_url = ?", (source_url,)
            ).fetchone()
            if row is None:
                return None

            chapter_rows = conn.execute(
                "SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_index",
                (row["id"],),
            ).fetchall()

        chapters = [
            Chapter(
                id=cr["id"],
                novel_id=cr["novel_id"],
                chapter_index=cr["chapter_index"],
                title=cr["title"],
                content=cr["content"] or "",
            )
            for cr in chapter_rows
        ]

        return Novel(
            id=row["id"],
            title=row["title"],
            author=row["author"],
            source_url=row["source_url"],
            txt_url=row["txt_url"],
            site_name=row["site_name"],
            chapters=chapters,
        )

    def list_novels(self) -> List[Novel]:
        """Return all stored novels (without chapters for efficiency)."""
        with _connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM novels ORDER BY downloaded_at DESC"
            ).fetchall()

        return [
            Novel(
                id=r["id"],
                title=r["title"],
                author=r["author"],
                source_url=r["source_url"],
                txt_url=r["txt_url"],
                site_name=r["site_name"],
            )
            for r in rows
        ]
