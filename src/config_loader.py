"""
Configuration loader for novelDownloader.

Loads and validates site configurations from a YAML file.
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Required top-level keys for each site entry
_REQUIRED_SITE_KEYS = [
    "name",
    "base_url",
    "list_url",
    "novel_link_selector",
    "txt_download_selector",
    "txt_encoding",
    "chapter_pattern",
]


class ConfigError(Exception):
    """Raised when a configuration file is invalid."""


class SiteConfig:
    """Holds the parsed configuration for a single scraping target site."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._validate(data)

        self.name: str = data["name"]
        self.base_url: str = data["base_url"].rstrip("/")
        self.list_url: str = data["list_url"]
        self.novel_link_selector: str = data["novel_link_selector"]
        self.txt_download_selector: str = data["txt_download_selector"]
        self.txt_encoding: str = data.get("txt_encoding", "utf-8")
        self.headers: Dict[str, str] = data.get("headers") or {}
        self.title_search_lines: int = int(data.get("title_search_lines", 5))

        # Compile the chapter regex once for reuse
        try:
            self.chapter_pattern: re.Pattern = re.compile(
                data["chapter_pattern"], re.MULTILINE
            )
        except re.error as exc:
            raise ConfigError(
                f"Site '{self.name}': invalid chapter_pattern regex — {exc}"
            ) from exc

        # Pagination settings
        pagination = data.get("list_pagination") or {}
        self.pagination_url_pattern: Optional[str] = pagination.get("url_pattern")
        self.pagination_start_page: int = int(pagination.get("start_page", 1))
        self.pagination_max_pages: int = int(pagination.get("max_pages", 1))

    # ------------------------------------------------------------------
    def list_page_urls(self) -> List[str]:
        """Return the full list of page URLs to crawl for this site."""
        if not self.pagination_url_pattern:
            return [self.list_url]

        urls: List[str] = []
        for page in range(
            self.pagination_start_page,
            self.pagination_start_page + self.pagination_max_pages,
        ):
            urls.append(self.pagination_url_pattern.format(page=page))
        return urls

    # ------------------------------------------------------------------
    @staticmethod
    def _validate(data: Dict[str, Any]) -> None:
        missing = [k for k in _REQUIRED_SITE_KEYS if not data.get(k)]
        if missing:
            name = data.get("name", "<unnamed>")
            raise ConfigError(
                f"Site '{name}' is missing required keys: {', '.join(missing)}"
            )


def load_config(config_path: Optional[str] = None) -> List[SiteConfig]:
    """Load site configurations from *config_path*.

    If *config_path* is not given, the default ``config/sites.yaml`` relative
    to this file's package root is used.

    Returns a list of :class:`SiteConfig` objects (one per enabled site).

    Raises :class:`ConfigError` on any structural problem.
    """
    if config_path is None:
        config_path = str(
            Path(__file__).parent.parent / "config" / "sites.yaml"
        )

    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    if not isinstance(raw, dict) or "sites" not in raw:
        raise ConfigError(
            f"Config file '{path}' must contain a top-level 'sites' list."
        )

    sites_raw = raw["sites"]
    if not isinstance(sites_raw, list) or not sites_raw:
        raise ConfigError(
            f"Config file '{path}': 'sites' must be a non-empty list."
        )

    return [SiteConfig(entry) for entry in sites_raw]
