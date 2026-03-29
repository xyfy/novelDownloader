"""Text cleaning pipeline for downloaded novel txt files."""

from __future__ import annotations

import re

# Advertisement keywords to strip (line-level)
_AD_PATTERNS = re.compile(
    r"(求收藏|求月票|求推荐票|投推荐票|关注公众号|下载.{0,4}[Aa]pp|"
    r"扫码关注|回复.{0,4}领|加群|手机版|m\.)",
    re.IGNORECASE,
)

# 4+ consecutive blank lines → 2
_MULTI_BLANK = re.compile(r"\n{4,}")


def clean(text: str) -> str:
    """Apply a multi-stage cleaning pipeline to raw novel text.

    Stages (in order):
    1. Strip BOM (\\ufeff)
    2. Normalise line endings (\\r\\n → \\n, bare \\r → \\n)
    3. Collapse 4+ consecutive blank lines to 2
    4. Strip trailing whitespace / tabs from each line
    5. Remove lines that are purely advertisement text
    """
    # 1. Strip BOM
    text = text.lstrip("\ufeff")

    # 2. Normalise line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Collapse excessive blank lines
    text = _MULTI_BLANK.sub("\n\n", text)

    # 4 & 5. Process line by line
    lines = []
    for line in text.split("\n"):
        line = line.rstrip(" \t")
        if _AD_PATTERNS.search(line):
            continue
        lines.append(line)

    return "\n".join(lines)


def is_valid_content(text: str, min_len: int = 50) -> bool:
    """Return True if text appears to contain real novel content.

    A piece of content is considered valid if it has at least ``min_len``
    non-whitespace characters.
    """
    return len(text.replace(" ", "").replace("\n", "")) >= min_len
