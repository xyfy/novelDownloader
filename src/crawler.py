"""
Crawler module for novelDownloader.

Fetches list/index pages and extracts individual novel detail-page URLs.
"""
import logging
import time
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config_loader import SiteConfig

logger = logging.getLogger(__name__)

# Seconds to wait between HTTP requests (be polite to servers)
REQUEST_DELAY = 1.0


def _get(url: str, site: SiteConfig, timeout: int = 30) -> requests.Response:
    """Perform a GET request with the site's headers and raise on HTTP errors."""
    resp = requests.get(url, headers=site.headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def crawl_novel_links(site: SiteConfig) -> List[str]:
    """Crawl all list/index pages for *site* and return unique novel URLs.

    Iterates over every paginated URL returned by :meth:`SiteConfig.list_page_urls`,
    parses each page with BeautifulSoup, and collects all ``<a>`` elements
    matched by ``site.novel_link_selector``.

    Returns a deduplicated list of absolute novel detail-page URLs.
    """
    seen: set = set()
    novel_urls: List[str] = []

    for page_url in site.list_page_urls():
        logger.info("[%s] Crawling list page: %s", site.name, page_url)
        try:
            resp = _get(page_url, site)
        except requests.RequestException as exc:
            logger.error("[%s] Failed to fetch %s: %s", site.name, page_url, exc)
            continue

        soup = BeautifulSoup(resp.content, "lxml")
        anchors = soup.select(site.novel_link_selector)
        logger.debug("[%s] Found %d anchor(s) on %s", site.name, len(anchors), page_url)

        for anchor in anchors:
            href = anchor.get("href", "").strip()
            if not href or href.startswith("#"):
                continue
            absolute_url = urljoin(site.base_url + "/", href)
            if absolute_url not in seen:
                seen.add(absolute_url)
                novel_urls.append(absolute_url)

        time.sleep(REQUEST_DELAY)

    logger.info("[%s] Total unique novel URLs found: %d", site.name, len(novel_urls))
    return novel_urls
