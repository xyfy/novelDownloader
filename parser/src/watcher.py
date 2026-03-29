"""File watcher.

Polls the pending/ directory every 5 seconds. When it finds a *.txt file with
an accompanying *.meta.json sidecar it processes the book:

1. Move txt + meta.json to processing/
2. Detect encoding → read + clean text
3. Split chapters
4. Upsert book record in MySQL
5. Bulk-insert chapters
6. On success: move files to done/, update parse_status = success
7. On failure: increment retry counter; after 3 failures move to failed/
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from parser.src.encoding_detector import read_text
from parser.src.novel_parser import split_chapters
from parser.src.text_cleaner import clean, is_valid_content
from parser.src import db_service

logger = logging.getLogger(__name__)

_POLL_INTERVAL = int(os.environ.get("WATCHER_POLL_INTERVAL", "5"))
_MAX_RETRIES = 3


def _dirs() -> dict[str, Path]:
    return {
        "pending": Path(os.environ.get("PENDING_DIR", "data/downloads/pending")),
        "processing": Path(os.environ.get("PROCESSING_DIR", "data/downloads/processing")),
        "done": Path(os.environ.get("DONE_DIR", "data/downloads/done")),
        "failed": Path(os.environ.get("FAILED_DIR", "data/downloads/failed")),
    }


def _move(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    shutil.move(str(src), str(dest))
    return dest


def _process_file(txt_path: Path, dirs: dict[str, Path]) -> None:
    """Process a single txt file end-to-end."""
    meta_path = txt_path.with_suffix(".meta.json")

    if not meta_path.exists():
        logger.warning("missing_meta", extra={"file": txt_path.name})
        return

    # ── Load meta ───────────────────────────────────────────────────────────
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("meta_read_error", extra={"file": meta_path.name, "error": str(exc)})
        return

    # ── Move to processing ───────────────────────────────────────────────────
    proc_txt = _move(txt_path, dirs["processing"])
    proc_meta = _move(meta_path, dirs["processing"])

    start = time.monotonic()
    book_id: Optional[int] = None
    retry_count = 0
    retry_file = dirs["processing"] / f".retry_{txt_path.stem}"

    # Load retry count
    if retry_file.exists():
        try:
            retry_count = int(retry_file.read_text())
        except ValueError:
            retry_count = 0

    try:
        # ── Upsert book ──────────────────────────────────────────────────────
        downloaded_at = None
        if meta.get("downloadedAt"):
            try:
                downloaded_at = datetime.fromisoformat(meta["downloadedAt"])
            except ValueError:
                pass

        book_id = db_service.upsert_book({
            "source_site": meta.get("siteId", "unknown"),
            "source_id": meta.get("sourceId", txt_path.stem),
            "title": meta.get("title", txt_path.stem),
            "author": meta.get("author"),
            "category": meta.get("category"),
            "source_url": meta.get("sourceUrl"),
            "downloaded_at": downloaded_at,
        })

        db_service.update_parse_status(book_id, "processing")

        # ── Detect encoding + read ───────────────────────────────────────────
        raw_text, encoding = read_text(str(proc_txt))
        cleaned = clean(raw_text)

        if not is_valid_content(cleaned):
            raise ValueError("Content appears empty or too short after cleaning")

        # ── Parse chapters ───────────────────────────────────────────────────
        chapters = split_chapters(cleaned)
        if not chapters:
            raise ValueError("No chapters detected")

        # ── Bulk insert ──────────────────────────────────────────────────────
        inserted = db_service.bulk_insert_chapters(book_id, chapters)

        duration_ms = int((time.monotonic() - start) * 1000)
        total_words = sum(ch["word_count"] for ch in chapters)

        db_service.update_parse_status(
            book_id, "success", total_words=total_words, detected_encoding=encoding
        )
        db_service.write_log(
            book_id,
            "info",
            f"Parsed successfully: {len(chapters)} chapters, {inserted} inserted, {total_words} words",
            detected_encoding=encoding,
            parse_duration_ms=duration_ms,
        )

        logger.info(
            "parse_success",
            extra={
                "book_id": book_id,
                "title": meta.get("title"),
                "chapters": len(chapters),
                "inserted": inserted,
                "words": total_words,
                "encoding": encoding,
                "duration_ms": duration_ms,
            },
        )

        # ── Move to done ─────────────────────────────────────────────────────
        _move(proc_txt, dirs["done"])
        _move(proc_meta, dirs["done"])
        if retry_file.exists():
            retry_file.unlink()

    except Exception as exc:  # pylint: disable=broad-except
        duration_ms = int((time.monotonic() - start) * 1000)
        retry_count += 1
        logger.error(
            "parse_error",
            extra={
                "file": txt_path.name,
                "error": str(exc),
                "retry_count": retry_count,
            },
        )

        if book_id is not None:
            db_service.update_parse_status(book_id, "failed")
            db_service.write_log(
                book_id,
                "error",
                str(exc)[:500],
                parse_duration_ms=duration_ms,
            )

        if retry_count >= _MAX_RETRIES:
            _move(proc_txt, dirs["failed"])
            _move(proc_meta, dirs["failed"])
            if retry_file.exists():
                retry_file.unlink()
            logger.error("moved_to_failed", extra={"file": txt_path.name})
        else:
            # Return to pending for retry
            retry_file.write_text(str(retry_count))
            _move(proc_txt, dirs["pending"])
            _move(proc_meta, dirs["pending"])


class Watcher:
    """Polls pending/ and processes txt files."""

    def __init__(self):
        self._running = False
        self._dirs = _dirs()

    def start(self, once: bool = False) -> None:
        """Start the polling loop.

        Args:
            once: If True, process all pending files and exit.
        """
        self._running = True

        # Graceful shutdown on SIGINT/SIGTERM
        def _stop(signum, _frame):
            logger.info("shutdown_signal", extra={"signal": signum})
            self._running = False

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        logger.info("watcher_start", extra={"dirs": {k: str(v) for k, v in self._dirs.items()}})

        stats = {"success": 0, "failed": 0}

        while self._running:
            pending = self._dirs["pending"]
            pending.mkdir(parents=True, exist_ok=True)

            txt_files = sorted(pending.glob("*.txt"))
            for txt_path in txt_files:
                if not self._running:
                    break
                try:
                    _process_file(txt_path, self._dirs)
                    stats["success"] += 1
                except Exception as exc:  # pylint: disable=broad-except
                    stats["failed"] += 1
                    logger.error("watcher_unhandled", extra={"file": txt_path.name, "error": str(exc)})

            if once:
                break

            time.sleep(_POLL_INTERVAL)

        logger.info("watcher_stop", extra=stats)
        total = stats["success"] + stats["failed"]
        logger.info(
            "run_summary",
            extra={
                "success": stats["success"],
                "failed": stats["failed"],
                "total": total,
            },
        )
