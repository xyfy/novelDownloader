"""
TXT parser module for novelDownloader.

Parses a downloaded novel TXT file into a :class:`~src.models.Novel`
with title, author, and a list of :class:`~src.models.Chapter` objects.

TXT format assumptions
----------------------
* The very first non-blank, non-chapter-heading line (within the first
  ``title_search_lines`` lines) is the novel title.
* An optional author line starts with ``作者：`` or ``author:`` (case-insensitive)
  and appears shortly after the title.
* Chapter headings are identified by ``site.chapter_pattern``.
* Content between consecutive chapter headings belongs to the preceding chapter.
"""
import logging
import re
from typing import List, Optional, Tuple

from .config_loader import SiteConfig
from .models import Chapter, Novel

logger = logging.getLogger(__name__)

# Patterns used to strip the author name from a line
_AUTHOR_PREFIXES = re.compile(
    r"^(作\s*者[：:]\s*|author\s*:\s*)", re.IGNORECASE
)


def _strip_bom(text: str) -> str:
    """Remove a UTF-8 BOM character if present."""
    return text.lstrip("\ufeff")


def _extract_title_and_author(
    lines: List[str],
    search_limit: int,
    chapter_pattern: Optional[re.Pattern] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return ``(title, author)`` by scanning the first *search_limit* lines.

    Lines that match *chapter_pattern* (if provided) are skipped when looking
    for the title so that a file starting immediately with a chapter heading
    correctly triggers the URL-based fallback.
    """
    title: Optional[str] = None
    author: Optional[str] = None

    for line in lines[:search_limit]:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip chapter headings — they are not the title
        if chapter_pattern is not None and chapter_pattern.match(stripped):
            continue
        if title is None:
            title = stripped
        elif _AUTHOR_PREFIXES.match(stripped):
            author = _AUTHOR_PREFIXES.sub("", stripped).strip()
            break

    return title, author


def parse_txt(
    txt_content: str,
    source_url: str,
    site: SiteConfig,
    txt_url: Optional[str] = None,
) -> Novel:
    """Parse *txt_content* into a :class:`Novel` instance.

    Parameters
    ----------
    txt_content:
        The full decoded text of the TXT file.
    source_url:
        The detail-page URL this novel was fetched from.
    site:
        The :class:`SiteConfig` for the site — provides ``chapter_pattern``
        and ``title_search_lines``.
    txt_url:
        The direct URL of the TXT file (stored for reference).
    """
    txt_content = _strip_bom(txt_content)
    lines = txt_content.splitlines()

    title, author = _extract_title_and_author(
        lines, site.title_search_lines, chapter_pattern=site.chapter_pattern
    )
    if not title:
        # Fallback: derive title from the source URL path
        title = source_url.rstrip("/").rsplit("/", 1)[-1] or "Unknown"
        logger.warning(
            "[%s] Could not detect title from TXT; using fallback: %r",
            site.name,
            title,
        )

    chapters: List[Chapter] = _split_chapters(lines, site)

    novel = Novel(
        title=title,
        author=author,
        source_url=source_url,
        txt_url=txt_url,
        site_name=site.name,
        chapters=chapters,
    )
    logger.info(
        "[%s] Parsed '%s' — %d chapter(s)", site.name, novel.title, len(chapters)
    )
    return novel


def _split_chapters(lines: List[str], site: SiteConfig) -> List[Chapter]:
    """Split *lines* into :class:`Chapter` objects using ``site.chapter_pattern``."""
    chapters: List[Chapter] = []
    pattern = site.chapter_pattern

    current_title: Optional[str] = None
    current_content_lines: List[str] = []
    chapter_index = 0

    for line in lines:
        if pattern.match(line.strip()):
            # Save the previous chapter (if any)
            if current_title is not None:
                chapters.append(
                    Chapter(
                        chapter_index=chapter_index,
                        title=current_title,
                        content="\n".join(current_content_lines).strip(),
                    )
                )
                chapter_index += 1
            current_title = line.strip()
            current_content_lines = []
        else:
            if current_title is not None:
                current_content_lines.append(line)

    # Flush the last chapter
    if current_title is not None:
        chapters.append(
            Chapter(
                chapter_index=chapter_index,
                title=current_title,
                content="\n".join(current_content_lines).strip(),
            )
        )

    return chapters
