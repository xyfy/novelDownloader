"""
Tests for src/config_loader.py
"""
import re
import textwrap
from pathlib import Path

import pytest
import yaml

from src.config_loader import ConfigError, SiteConfig, load_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_yaml(tmp_path: Path, data: dict) -> str:
    p = tmp_path / "sites.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return str(p)


def _minimal_site(**overrides) -> dict:
    base = {
        "name": "test_site",
        "base_url": "https://example.com",
        "list_url": "https://example.com/latest/",
        "novel_link_selector": "a.novel",
        "txt_download_selector": "a.download",
        "txt_encoding": "utf-8",
        "chapter_pattern": r"^(第\d+章.*)$",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SiteConfig unit tests
# ---------------------------------------------------------------------------

class TestSiteConfig:
    def test_valid_minimal(self):
        cfg = SiteConfig(_minimal_site())
        assert cfg.name == "test_site"
        assert cfg.base_url == "https://example.com"
        assert cfg.txt_encoding == "utf-8"
        assert isinstance(cfg.chapter_pattern, re.Pattern)
        assert cfg.pagination_max_pages == 1
        assert cfg.list_page_urls() == ["https://example.com/latest/"]

    def test_trailing_slash_stripped_from_base_url(self):
        cfg = SiteConfig(_minimal_site(base_url="https://example.com/"))
        assert cfg.base_url == "https://example.com"

    def test_missing_required_key_raises(self):
        data = _minimal_site()
        del data["list_url"]
        with pytest.raises(ConfigError, match="list_url"):
            SiteConfig(data)

    def test_invalid_regex_raises(self):
        with pytest.raises(ConfigError, match="chapter_pattern"):
            SiteConfig(_minimal_site(chapter_pattern="[invalid"))

    def test_pagination_urls(self):
        data = _minimal_site()
        data["list_pagination"] = {
            "url_pattern": "https://example.com/latest/?page={page}",
            "start_page": 1,
            "max_pages": 3,
        }
        cfg = SiteConfig(data)
        assert cfg.list_page_urls() == [
            "https://example.com/latest/?page=1",
            "https://example.com/latest/?page=2",
            "https://example.com/latest/?page=3",
        ]

    def test_no_pagination_returns_list_url(self):
        cfg = SiteConfig(_minimal_site())
        assert cfg.list_page_urls() == ["https://example.com/latest/"]

    def test_default_headers_empty(self):
        cfg = SiteConfig(_minimal_site())
        assert cfg.headers == {}

    def test_custom_headers(self):
        data = _minimal_site(headers={"User-Agent": "TestBot/1.0"})
        cfg = SiteConfig(data)
        assert cfg.headers["User-Agent"] == "TestBot/1.0"


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_loads_single_site(self, tmp_path):
        path = _make_yaml(tmp_path, {"sites": [_minimal_site()]})
        configs = load_config(path)
        assert len(configs) == 1
        assert configs[0].name == "test_site"

    def test_loads_multiple_sites(self, tmp_path):
        path = _make_yaml(
            tmp_path,
            {"sites": [_minimal_site(name="site_a"), _minimal_site(name="site_b")]},
        )
        configs = load_config(path)
        assert [c.name for c in configs] == ["site_a", "site_b"]

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="not found"):
            load_config(str(tmp_path / "no_such_file.yaml"))

    def test_no_sites_key_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("foo: bar\n", encoding="utf-8")
        with pytest.raises(ConfigError, match="sites"):
            load_config(str(p))

    def test_empty_sites_list_raises(self, tmp_path):
        path = _make_yaml(tmp_path, {"sites": []})
        with pytest.raises(ConfigError, match="non-empty"):
            load_config(path)

    def test_default_config_loads(self):
        """The bundled config/sites.yaml must be valid."""
        configs = load_config()
        assert len(configs) >= 1
        assert any(c.name == "txt520" for c in configs)
