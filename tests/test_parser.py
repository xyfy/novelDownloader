"""
Tests for src/parser.py
"""
import re
import textwrap

import pytest

from src.config_loader import SiteConfig
from src.parser import _extract_title_and_author, _split_chapters, parse_txt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_site(**kwargs) -> SiteConfig:
    defaults = {
        "name": "test",
        "base_url": "https://example.com",
        "list_url": "https://example.com/",
        "novel_link_selector": "a",
        "txt_download_selector": "a",
        "txt_encoding": "utf-8",
        "chapter_pattern": r"^(第[\d零一二三四五六七八九十百千万]+[章节回]\s*.*)$",
        "title_search_lines": 5,
    }
    defaults.update(kwargs)
    return SiteConfig(defaults)


SITE = _make_site()

# ---------------------------------------------------------------------------
# _extract_title_and_author
# ---------------------------------------------------------------------------

class TestExtractTitleAndAuthor:
    def test_basic(self):
        lines = ["斗破苍穹", "作者：天蚕土豆", "第一章 天才陨落"]
        title, author = _extract_title_and_author(lines, 5)
        assert title == "斗破苍穹"
        assert author == "天蚕土豆"

    def test_author_colon_full_width(self):
        lines = ["某小说", "作者：作者名"]
        _, author = _extract_title_and_author(lines, 5)
        assert author == "作者名"

    def test_author_ascii_colon(self):
        lines = ["My Novel", "author: Some Author"]
        _, author = _extract_title_and_author(lines, 5)
        assert author == "Some Author"

    def test_no_author(self):
        lines = ["只有标题"]
        title, author = _extract_title_and_author(lines, 5)
        assert title == "只有标题"
        assert author is None

    def test_empty_lines_skipped(self):
        lines = ["", "  ", "真正标题", "作者：某人"]
        title, author = _extract_title_and_author(lines, 5)
        assert title == "真正标题"
        assert author == "某人"

    def test_search_limit_respected(self):
        lines = ["标题", "作者：某人"]
        title, author = _extract_title_and_author(lines, 1)
        assert title == "标题"
        assert author is None  # author line is beyond search_limit=1

    def test_chapter_heading_skipped_as_title(self):
        """Lines matching the chapter pattern are skipped when looking for title."""
        pattern = re.compile(r"^(第[\d零一二三四五六七八九十百千万]+章.*)$")
        # All lines in the window are chapter headings → no title found
        lines = ["第一章 开始", "第二章 续写"]
        title, _ = _extract_title_and_author(lines, 5, chapter_pattern=pattern)
        assert title is None


# ---------------------------------------------------------------------------
# _split_chapters
# ---------------------------------------------------------------------------

class TestSplitChapters:
    def test_basic_split(self):
        txt = textwrap.dedent("""\
            书名
            第一章 开始
            内容第一章
            第二章 中间
            内容第二章
            第三章 结束
            内容第三章
        """)
        lines = txt.splitlines()
        chapters = _split_chapters(lines, SITE)
        assert len(chapters) == 3
        assert chapters[0].title == "第一章 开始"
        assert "内容第一章" in chapters[0].content
        assert chapters[1].chapter_index == 1
        assert chapters[2].title == "第三章 结束"

    def test_no_chapters(self):
        txt = "这是一段没有章节的内容\n继续写\n"
        chapters = _split_chapters(txt.splitlines(), SITE)
        assert chapters == []

    def test_chapter_with_number_only(self):
        txt = "第1章\n内容\n第2章\n内容2\n"
        chapters = _split_chapters(txt.splitlines(), SITE)
        assert len(chapters) == 2
        assert chapters[0].chapter_index == 0
        assert chapters[1].chapter_index == 1

    def test_content_stripped(self):
        txt = "第一章 测试\n\n   内容行   \n\n"
        chapters = _split_chapters(txt.splitlines(), SITE)
        assert chapters[0].content == "内容行"

    def test_empty_content_chapter(self):
        txt = "第一章 空章节\n第二章 有内容\n内容\n"
        chapters = _split_chapters(txt.splitlines(), SITE)
        assert chapters[0].content == ""
        assert "内容" in chapters[1].content


# ---------------------------------------------------------------------------
# parse_txt
# ---------------------------------------------------------------------------

class TestParseTxt:
    _TXT = textwrap.dedent("""\
        斗破苍穹
        作者：天蚕土豆

        第一章 天才陨落
        萧炎坐在大殿之中，目光涣散……

        第二章 三年之约
        时间如流水般逝去……
    """)

    def test_full_parse(self):
        novel = parse_txt(self._TXT, source_url="https://example.com/book/1/", site=SITE)
        assert novel.title == "斗破苍穹"
        assert novel.author == "天蚕土豆"
        assert novel.site_name == "test"
        assert len(novel.chapters) == 2
        assert novel.chapters[0].title == "第一章 天才陨落"
        assert novel.chapters[1].title == "第二章 三年之约"

    def test_fallback_title_from_url(self):
        # When all lines in the title search window are chapter headings,
        # the parser falls back to deriving the title from the URL.
        all_headings = "\n".join(f"第{i + 1}章 内容" for i in range(6))
        novel = parse_txt(all_headings, source_url="https://example.com/book/my-novel/", site=SITE)
        assert novel.title == "my-novel"

    def test_bom_stripped(self):
        bom_txt = "\ufeff斗破苍穹\n第一章 章节\n内容\n"
        novel = parse_txt(bom_txt, source_url="https://example.com/1/", site=SITE)
        assert novel.title == "斗破苍穹"

    def test_txt_url_stored(self):
        novel = parse_txt(
            self._TXT,
            source_url="https://example.com/1/",
            site=SITE,
            txt_url="https://example.com/1/novel.txt",
        )
        assert novel.txt_url == "https://example.com/1/novel.txt"
