"""
Data models for novelDownloader.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Chapter:
    """Represents a single chapter of a novel."""

    chapter_index: int
    title: str
    content: str
    id: Optional[int] = None
    novel_id: Optional[int] = None


@dataclass
class Novel:
    """Represents a novel and its chapters."""

    title: str
    source_url: str
    site_name: str
    author: Optional[str] = None
    txt_url: Optional[str] = None
    chapters: List[Chapter] = field(default_factory=list)
    downloaded_at: Optional[datetime] = None
    id: Optional[int] = None
