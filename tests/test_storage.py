"""
Tests for src/storage.py
"""
import textwrap

import pytest

from src.models import Chapter, Novel
from src.storage import Database


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_novel(source_url: str = "https://example.com/book/1/", **kwargs) -> Novel:
    defaults = dict(
        title="斗破苍穹",
        author="天蚕土豆",
        source_url=source_url,
        txt_url="https://example.com/book/1/novel.txt",
        site_name="test",
        chapters=[
            Chapter(chapter_index=0, title="第一章 天才陨落", content="内容一"),
            Chapter(chapter_index=1, title="第二章 三年之约", content="内容二"),
        ],
    )
    defaults.update(kwargs)
    return Novel(**defaults)


# ---------------------------------------------------------------------------
# Database tests
# ---------------------------------------------------------------------------

class TestDatabase:
    @pytest.fixture()
    def db(self, tmp_path):
        return Database(str(tmp_path / "test.db"))

    def test_schema_created(self, db):
        """Tables must exist after Database() is created."""
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()
        assert "novels" in tables
        assert "chapters" in tables

    def test_save_novel_returns_id(self, db):
        novel = _make_novel()
        saved = db.save_novel(novel)
        assert saved.id is not None
        assert saved.id > 0

    def test_save_and_retrieve(self, db):
        novel = _make_novel()
        db.save_novel(novel)

        retrieved = db.get_novel_by_url(novel.source_url)
        assert retrieved is not None
        assert retrieved.title == novel.title
        assert retrieved.author == novel.author
        assert len(retrieved.chapters) == 2
        assert retrieved.chapters[0].title == "第一章 天才陨落"

    def test_chapters_ordered(self, db):
        novel = _make_novel()
        db.save_novel(novel)

        retrieved = db.get_novel_by_url(novel.source_url)
        indices = [ch.chapter_index for ch in retrieved.chapters]
        assert indices == sorted(indices)

    def test_upsert_updates_existing(self, db):
        novel = _make_novel()
        db.save_novel(novel)

        updated = _make_novel(title="斗破苍穹（修订版）")
        updated.chapters = [Chapter(chapter_index=0, title="第一章 新版", content="新内容")]
        db.save_novel(updated)

        retrieved = db.get_novel_by_url(novel.source_url)
        assert retrieved.title == "斗破苍穹（修订版）"
        assert len(retrieved.chapters) == 1
        assert retrieved.chapters[0].title == "第一章 新版"

    def test_get_nonexistent_returns_none(self, db):
        assert db.get_novel_by_url("https://no.such.url/") is None

    def test_list_novels_empty(self, db):
        assert db.list_novels() == []

    def test_list_novels_returns_all(self, db):
        db.save_novel(_make_novel("https://example.com/1/", title="小说甲"))
        db.save_novel(_make_novel("https://example.com/2/", title="小说乙"))

        novels = db.list_novels()
        titles = {n.title for n in novels}
        assert {"小说甲", "小说乙"} == titles

    def test_novel_without_chapters(self, db):
        novel = _make_novel(chapters=[])
        saved = db.save_novel(novel)
        retrieved = db.get_novel_by_url(novel.source_url)
        assert retrieved.chapters == []

    def test_save_novel_no_author(self, db):
        novel = _make_novel(author=None)
        db.save_novel(novel)
        retrieved = db.get_novel_by_url(novel.source_url)
        assert retrieved.author is None
