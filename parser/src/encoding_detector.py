"""Encoding detection for txt files.

Strategy:
1. Use chardet – if confidence >= 0.9, trust it.
2. Enumerate: utf-8-sig > utf-8 > gbk > gb2312 > big5
3. Fallback: return 'utf-8' with errors='replace'.
"""

from __future__ import annotations

import chardet

# Ordered list of encodings to try when chardet confidence is low
_FALLBACK_ENCODINGS = ["utf-8-sig", "utf-8", "gbk", "gb2312", "big5"]
_CONFIDENCE_THRESHOLD = 0.9
_SAMPLE_BYTES = 20_000


def detect(file_path: str, sample_bytes: int = _SAMPLE_BYTES) -> str:
    """Detect the encoding of a text file.

    Args:
        file_path: Absolute or relative path to the file.
        sample_bytes: Number of bytes to read for detection.

    Returns:
        An encoding string suitable for use with ``open(file_path, encoding=...)``.
    """
    with open(file_path, "rb") as fh:
        raw = fh.read(sample_bytes)

    if not raw:
        return "utf-8"

    result = chardet.detect(raw)
    encoding = (result.get("encoding") or "").lower().replace("-", "")
    confidence = result.get("confidence") or 0.0

    # Normalise chardet encoding names
    _alias = {
        "utf8sig": "utf-8-sig",
        "utf8": "utf-8",
        "gb2312": "gbk",  # gbk is a superset
        "ascii": "utf-8",
    }
    encoding = _alias.get(encoding, result.get("encoding") or "utf-8")

    if confidence >= _CONFIDENCE_THRESHOLD and encoding:
        return encoding

    # Try each encoding in order
    for enc in _FALLBACK_ENCODINGS:
        try:
            with open(file_path, "r", encoding=enc, errors="strict") as fh:
                fh.read(sample_bytes)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "utf-8"


def read_text(file_path: str) -> tuple[str, str]:
    """Read a file and return (text, detected_encoding).

    The file is read with ``errors='replace'`` to avoid crashes on bad bytes.
    """
    encoding = detect(file_path)
    with open(file_path, "r", encoding=encoding, errors="replace") as fh:
        text = fh.read()
    return text, encoding
