"""Parser entry point.

Usage:
    python main.py           # run continuously
    python main.py --once    # process pending files once and exit
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

# ── Logging setup ─────────────────────────────────────────────────────────────
_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)

# ── Optional JSON log file ────────────────────────────────────────────────────
_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

try:
    import json as _json

    class _JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            d = {
                "time": self.formatTime(record),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
            }
            for k, v in record.__dict__.items():
                if k not in ("args", "exc_info", "exc_text", "stack_info", "msg",
                             "levelname", "levelno", "name", "pathname", "filename",
                             "module", "funcName", "lineno", "created", "msecs",
                             "relativeCreated", "thread", "threadName", "processName",
                             "process", "taskName"):
                    d[k] = v
            return _json.dumps(d, ensure_ascii=False, default=str)

    _fh = logging.FileHandler(os.path.join(_LOG_DIR, "parser.log"), encoding="utf-8")
    _fh.setFormatter(_JsonFormatter())
    logging.getLogger().addHandler(_fh)
except Exception:  # pylint: disable=broad-except
    pass  # JSON log is optional; don't crash if it fails


def main():
    parser = argparse.ArgumentParser(description="Novel parser service")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process all files currently in pending/ then exit",
    )
    args = parser.parse_args()

    from parser.src.watcher import Watcher

    logger.info(
        "parser_start",
        extra={
            "pending_dir": os.environ.get("PENDING_DIR", "data/downloads/pending"),
            "mode": "once" if args.once else "continuous",
        },
    )

    watcher = Watcher()
    watcher.start(once=args.once)


if __name__ == "__main__":
    main()
