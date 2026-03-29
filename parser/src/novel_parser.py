"""Novel chapter parser.

Splits a cleaned novel text into structured chapters using three ordered regex
patterns.  The pattern that produces the most hits wins.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

# ── Chapter detection regexes (ordered by priority) ──────────────────────────
PATTERNS: list[re.Pattern] = [
    # 第X章/节/回/卷 (Chinese ordinal)
    re.compile(r"^第[零一二三四五六七八九十百千万\d]+[章节回卷]", re.MULTILINE),
    # Numeric prefix: 1. / 1、/ 001. etc.
    re.compile(r"^\d{1,5}[、.。]\s*\S", re.MULTILINE),
    # Special chapter names
    re.compile(r"^(?:前言|楔子|序章|尾声|番外[\w]*|后记)", re.MULTILINE),
]


# Minimum number of heading matches required to consider a pattern valid
_MINIMUM_CHAPTER_COUNT = 2


def _select_pattern(text: str) -> Optional[re.Pattern]:
    """Choose the regex pattern that hits the most lines."""
    best_pattern = None
    best_count = 0
    for pat in PATTERNS:
        count = len(pat.findall(text))
        if count > best_count:
            best_count = count
            best_pattern = pat
    # Need at least _MINIMUM_CHAPTER_COUNT hits to consider it a chapter-based structure
    return best_pattern if best_count >= _MINIMUM_CHAPTER_COUNT else None


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def _word_count(text: str) -> int:
    """Count CJK characters + ASCII words."""
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3400-\u4dbf]", text))
    ascii_words = len(re.findall(r"[a-zA-Z]+", text))
    return cjk + ascii_words


def split_chapters(text: str) -> list[dict]:
    """Split cleaned text into a list of chapter dicts.

    Each dict has:
        num (int)           – 1-based chapter number
        title (str)         – chapter heading line
        content (str)       – body text (excluding heading)
        word_count (int)
        content_hash (str)  – SHA-256 of content

    If no chapter pattern is detected, the entire text is returned as one
    chapter titled "全文".
    """
    pattern = _select_pattern(text)

    if pattern is None:
        # Treat whole text as a single chapter
        content = text.strip()
        return [
            {
                "num": 1,
                "title": "全文",
                "content": content,
                "word_count": _word_count(content),
                "content_hash": _content_hash(content),
            }
        ]

    # Find all heading positions
    matches = list(pattern.finditer(text))
    chapters = []

    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        # Split heading line from body
        chunk = text[start:end]
        lines = chunk.split("\n", 1)
        title = lines[0].strip()
        content = lines[1].strip() if len(lines) > 1 else ""

        chapters.append(
            {
                "num": i + 1,
                "title": title,
                "content": content,
                "word_count": _word_count(content),
                "content_hash": _content_hash(content),
            }
        )

    return chapters
