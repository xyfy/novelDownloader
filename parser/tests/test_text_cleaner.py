"""Tests for parser/src/text_cleaner.py"""
import pytest
from parser.src.text_cleaner import clean, is_valid_content


class TestClean:
    # ── BOM stripping ──────────────────────────────────────────────────────

    def test_strips_utf8_bom(self):
        text = "\ufeff第一章 开始\n内容"
        assert clean(text).startswith("第一章")

    # ── Line-ending normalisation ──────────────────────────────────────────

    def test_crlf_normalised_to_lf(self):
        text = "第一行\r\n第二行\r\n第三行"
        result = clean(text)
        assert "\r" not in result
        assert result == "第一行\n第二行\n第三行"

    def test_bare_cr_normalised_to_lf(self):
        text = "第一行\r第二行"
        result = clean(text)
        assert "\r" not in result

    # ── Blank-line collapse ────────────────────────────────────────────────

    def test_four_blank_lines_collapsed_to_two(self):
        text = "段落一\n\n\n\n\n段落二"
        result = clean(text)
        assert "\n\n\n" not in result

    def test_two_blank_lines_preserved(self):
        text = "段落一\n\n段落二"
        result = clean(text)
        assert "段落一\n\n段落二" in result

    # ── Trailing whitespace ────────────────────────────────────────────────

    def test_trailing_spaces_stripped(self):
        text = "一行文字   \n另一行\t"
        result = clean(text)
        for line in result.splitlines():
            assert line == line.rstrip(" \t")

    # ── Advertisement removal ──────────────────────────────────────────────

    def test_removes_collect_ad(self):
        text = "精彩内容\n求收藏，求月票！\n更多精彩"
        result = clean(text)
        assert "求收藏" not in result
        assert "精彩内容" in result

    def test_removes_recommend_ticket_ad(self):
        text = "前情提要\n投推荐票哦\n正文"
        result = clean(text)
        assert "投推荐票" not in result

    def test_removes_wechat_ad(self):
        text = "故事\n关注公众号获取更多内容\n继续"
        result = clean(text)
        assert "关注公众号" not in result

    def test_removes_app_download_ad(self):
        text = "章节内容\n下载App获取完整内容\n下一章"
        result = clean(text)
        assert "下载App" not in result

    def test_non_ad_lines_preserved(self):
        text = "第一章 起点\n这是正文，没有广告。\n结尾"
        result = clean(text)
        assert "这是正文，没有广告。" in result

    # ── Empty / edge cases ─────────────────────────────────────────────────

    def test_empty_string_returns_empty(self):
        assert clean("") == ""

    def test_already_clean_text_unchanged(self):
        text = "第一章\n内容"
        assert clean(text) == text


class TestIsValidContent:
    def test_long_text_is_valid(self):
        assert is_valid_content("这是一段很长的正文内容，包含了很多中文字符。" * 3)

    def test_short_text_is_invalid(self):
        assert not is_valid_content("短")

    def test_empty_string_is_invalid(self):
        assert not is_valid_content("")

    def test_only_whitespace_is_invalid(self):
        assert not is_valid_content("   \n\n  ")

    def test_custom_min_len(self):
        assert is_valid_content("ab", min_len=2)
        assert not is_valid_content("a", min_len=2)
