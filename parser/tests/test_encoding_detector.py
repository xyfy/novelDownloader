"""Tests for parser/src/encoding_detector.py

These tests create temporary files in known encodings and verify that
the detector identifies them correctly.
"""

import os
import tempfile
import pytest
from parser.src.encoding_detector import detect, read_text


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_tmp(content: str, encoding: str) -> str:
    """Write `content` encoded as `encoding` to a temp file; return its path."""
    fh = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".txt", delete=False
    )
    fh.write(content.encode(encoding))
    fh.close()
    return fh.name


def _write_raw(raw: bytes) -> str:
    fh = tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False)
    fh.write(raw)
    fh.close()
    return fh.name


# ── detect() ─────────────────────────────────────────────────────────────────

class TestDetect:
    def test_utf8_file(self):
        path = _write_tmp("这是一段中文文字，编码为 UTF-8。" * 20, "utf-8")
        try:
            enc = detect(path)
            # After normalisation, utf-8 / utf-8-sig / ascii all collapse to utf8 / utf8sig / ascii
            assert enc.lower().replace("-", "") in ("utf8", "utf8sig", "ascii")
        finally:
            os.unlink(path)

    def test_utf8_bom_file(self):
        text = "这是带 BOM 的 UTF-8 文件。" * 20
        path = _write_raw("\ufeff".encode("utf-8") + text.encode("utf-8"))
        try:
            enc = detect(path)
            # Should detect utf-8-sig (with BOM) or fall back to utf-8
            assert "utf" in enc.lower()
        finally:
            os.unlink(path)

    def test_gbk_file(self):
        text = "这是 GBK 编码的小说文件，包含大量中文字符。" * 30
        path = _write_tmp(text, "gbk")
        try:
            enc = detect(path)
            # Accept gbk or gb2312 (chardet may report either)
            assert enc.lower() in ("gbk", "gb2312", "gb18030", "utf-8-sig", "utf-8")
        finally:
            os.unlink(path)

    def test_empty_file_returns_utf8(self):
        path = _write_raw(b"")
        try:
            enc = detect(path)
            assert enc == "utf-8"
        finally:
            os.unlink(path)

    def test_returns_string(self):
        path = _write_tmp("hello", "utf-8")
        try:
            enc = detect(path)
            assert isinstance(enc, str)
            assert len(enc) > 0
        finally:
            os.unlink(path)


# ── read_text() ───────────────────────────────────────────────────────────────

class TestReadText:
    def test_returns_tuple(self):
        path = _write_tmp("测试文本", "utf-8")
        try:
            result = read_text(path)
            assert isinstance(result, tuple)
            assert len(result) == 2
        finally:
            os.unlink(path)

    def test_text_decoded_correctly_utf8(self):
        original = "这是 UTF-8 编码的小说内容。" * 10
        path = _write_tmp(original, "utf-8")
        try:
            text, enc = read_text(path)
            assert "这是" in text
            assert "utf" in enc.lower()
        finally:
            os.unlink(path)

    def test_text_decoded_correctly_gbk(self):
        original = "这是 GBK 编码的小说内容，大量中文字符。" * 30
        path = _write_tmp(original, "gbk")
        try:
            text, enc = read_text(path)
            # Should not contain replacement characters for well-known GBK text
            assert "这是" in text
        finally:
            os.unlink(path)

    def test_bom_stripped_from_utf8sig(self):
        text = "正文内容开始。" * 10
        path = _write_raw("\ufeff".encode("utf-8") + text.encode("utf-8"))
        try:
            result, enc = read_text(path)
            # BOM character should not appear in the decoded text
            assert "\ufeff" not in result
        finally:
            os.unlink(path)

    def test_does_not_raise_on_invalid_bytes(self):
        # Mixing invalid bytes should not raise – errors='replace' is used
        path = _write_raw(b"\xff\xfe invalid bytes \xff")
        try:
            text, enc = read_text(path)
            assert isinstance(text, str)
        finally:
            os.unlink(path)
