"""Tests for parser/src/novel_parser.py"""
import hashlib
import pytest
from parser.src.novel_parser import split_chapters, _select_pattern, _content_hash, _word_count, PATTERNS


# ── Fixtures / shared text ────────────────────────────────────────────────────

# Body text must NOT accidentally start with a chapter pattern.
CHINESE_NOVEL = """\
第一章 序幕
故事从这里开始，英雄踏上旅途，走向未知。
正文描述了主角的背景。

第二章 相遇
主角与伙伴相遇，结下深厚友情。
两人并肩作战，共同前行。

第三章 危机
危险悄然降临，众人面临考验。
危机中方显英雄本色。
"""

NUMERIC_NOVEL = """\
1. 序幕
故事开始了，主角出场，迎接新的冒险。

2. 相遇
主角与伙伴正式相遇了，友情深厚。

3. 结局
故事圆满结束了，所有人都很高兴。
"""

SPECIAL_NOVEL = """\
楔子
故事的起源，世界的背景在此说明，详细描述了设定。

序章
正式故事开始之前的铺垫，介绍了主要人物。

前言
作者的话：感谢每一位读者的支持，这本书是我的心血。
"""


# ── _content_hash ─────────────────────────────────────────────────────────────

class TestContentHash:
    def test_produces_64_char_hex_string(self):
        h = _content_hash("测试内容")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_content_same_hash(self):
        assert _content_hash("abc") == _content_hash("abc")

    def test_different_content_different_hash(self):
        assert _content_hash("abc") != _content_hash("ABC")

    def test_matches_sha256(self):
        text = "hello world"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert _content_hash(text) == expected


# ── _word_count ───────────────────────────────────────────────────────────────

class TestWordCount:
    def test_counts_cjk_characters(self):
        assert _word_count("你好世界") == 4

    def test_counts_ascii_words(self):
        assert _word_count("hello world") == 2

    def test_ignores_punctuation_and_numbers(self):
        count = _word_count("123 ！。，")
        assert count == 0

    def test_mixed_cjk_and_ascii(self):
        count = _word_count("你好 hello 世界 world")
        assert count == 6  # 4 CJK + 2 ASCII words


# ── _select_pattern ───────────────────────────────────────────────────────────

class TestSelectPattern:
    def test_selects_chinese_ordinal_for_chinese_novel(self):
        pattern = _select_pattern(CHINESE_NOVEL)
        assert pattern is PATTERNS[0]

    def test_selects_numeric_pattern_for_numeric_novel(self):
        pattern = _select_pattern(NUMERIC_NOVEL)
        assert pattern is PATTERNS[1]

    def test_selects_special_pattern(self):
        pattern = _select_pattern(SPECIAL_NOVEL)
        assert pattern is PATTERNS[2]

    def test_returns_none_for_unstructured_text(self):
        assert _select_pattern("这是普通文字，没有任何章节划分标记。") is None

    def test_returns_none_for_single_chapter_hit(self):
        # Only one match – below minimum threshold of 2
        text = "第一章 唯一章节\n正文内容。"
        assert _select_pattern(text) is None


# ── split_chapters ────────────────────────────────────────────────────────────

class TestSplitChapters:
    # ── Chinese ordinal ───────────────────────────────────────────────────

    def test_chinese_novel_splits_into_correct_count(self):
        chapters = split_chapters(CHINESE_NOVEL)
        assert len(chapters) == 3

    def test_chapters_are_numbered_from_1(self):
        chapters = split_chapters(CHINESE_NOVEL)
        assert [ch["num"] for ch in chapters] == [1, 2, 3]

    def test_chapter_titles_extracted(self):
        chapters = split_chapters(CHINESE_NOVEL)
        assert chapters[0]["title"] == "第一章 序幕"
        assert chapters[1]["title"] == "第二章 相遇"
        assert chapters[2]["title"] == "第三章 危机"

    def test_chapter_content_starts_with_body_not_heading(self):
        # The first line of content should NOT be the heading line itself
        chapters = split_chapters(CHINESE_NOVEL)
        first_content_line = chapters[0]["content"].splitlines()[0]
        assert first_content_line != "第一章 序幕"
        assert "故事从这里开始" in first_content_line

    def test_word_count_positive_for_all_chapters(self):
        chapters = split_chapters(CHINESE_NOVEL)
        assert all(ch["word_count"] > 0 for ch in chapters)

    def test_content_hash_is_64_chars(self):
        chapters = split_chapters(CHINESE_NOVEL)
        assert all(len(ch["content_hash"]) == 64 for ch in chapters)

    def test_no_duplicate_hashes(self):
        chapters = split_chapters(CHINESE_NOVEL)
        hashes = [ch["content_hash"] for ch in chapters]
        assert len(set(hashes)) == len(hashes)

    # ── Numeric ordinal ───────────────────────────────────────────────────

    def test_numeric_novel_splits_correctly(self):
        chapters = split_chapters(NUMERIC_NOVEL)
        assert len(chapters) == 3
        assert chapters[0]["title"] == "1. 序幕"

    # ── Special chapter names ─────────────────────────────────────────────

    def test_special_chapters_split_correctly(self):
        chapters = split_chapters(SPECIAL_NOVEL)
        assert len(chapters) == 3
        titles = [ch["title"] for ch in chapters]
        assert "楔子" in titles
        assert "序章" in titles
        assert "前言" in titles

    # ── Fallback: no pattern ──────────────────────────────────────────────

    def test_no_pattern_returns_single_chapter(self):
        text = "这是一段没有章节标记的普通文字，足够长以通过检查。" * 3
        chapters = split_chapters(text)
        assert len(chapters) == 1
        assert chapters[0]["num"] == 1
        assert chapters[0]["title"] == "全文"

    def test_fallback_chapter_contains_full_content(self):
        text = "普通文字内容。" * 10
        chapters = split_chapters(text)
        assert chapters[0]["content"] == text.strip()

    # ── Edge cases ────────────────────────────────────────────────────────

    def test_chapter_with_no_body_has_empty_content(self):
        text = "第一章 开始\n第二章 继续\n内容在这里，文字很丰富。"
        chapters = split_chapters(text)
        assert chapters[0]["content"] == ""
        assert "内容在这里" in chapters[1]["content"]

    def test_large_chapter_count(self):
        lines = []
        for i in range(1, 51):
            lines.append(f"第{i}章 章节{i}")
            lines.append("这是章节正文内容，详细描述了情节发展。\n")
        chapters = split_chapters("\n".join(lines))
        assert len(chapters) == 50
