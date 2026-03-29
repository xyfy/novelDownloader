"""
Downloader module for novelDownloader.

Opens a novel detail page, locates the TXT download link, downloads the file,
and returns the decoded text.
"""
import logging
import time
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from .config_loader import SiteConfig

logger = logging.getLogger(__name__)

REQUEST_DELAY = 1.0


def _get(url: str, site: SiteConfig, timeout: int = 30) -> requests.Response:
    resp = requests.get(url, headers=site.headers, timeout=timeout)
    resp.raise_for_status()
    return resp


def find_txt_url(detail_url: str, site: SiteConfig) -> Optional[str]:
    """Fetch the novel detail page and return the absolute URL of the TXT file.

    Returns ``None`` if no TXT link is found.
    """
    logger.info("[%s] Fetching detail page: %s", site.name, detail_url)
    try:
        resp = _get(detail_url, site)
    except requests.RequestException as exc:
        logger.error("[%s] Failed to fetch detail page %s: %s", site.name, detail_url, exc)
        return None

    soup = BeautifulSoup(resp.content, "lxml")
    anchor = soup.select_one(site.txt_download_selector)
    if anchor is None:
        logger.warning("[%s] No TXT download link found on %s", site.name, detail_url)
        return None

    href = anchor.get("href", "").strip()
    if not href:
        return None

    return urljoin(detail_url, href)


def download_txt(txt_url: str, site: SiteConfig) -> Optional[str]:
    """Download the TXT file at *txt_url* and return its decoded content.

    Uses ``site.txt_encoding`` to decode the raw bytes.  Falls back to
    ``utf-8`` with ``errors='replace'`` if the specified encoding fails.

    Returns ``None`` on network error.
    """
    logger.info("[%s] Downloading TXT: %s", site.name, txt_url)
    try:
        resp = _get(txt_url, site)
    except requests.RequestException as exc:
        logger.error("[%s] Failed to download TXT %s: %s", site.name, txt_url, exc)
        return None

    raw = resp.content
    try:
        text = raw.decode(site.txt_encoding)
    except (UnicodeDecodeError, LookupError):
        logger.warning(
            "[%s] Decoding with '%s' failed; falling back to utf-8.",
            site.name,
            site.txt_encoding,
        )
        text = raw.decode("utf-8", errors="replace")

    time.sleep(REQUEST_DELAY)
    return text


def fetch_novel_txt(detail_url: str, site: SiteConfig) -> Optional[str]:
    """Convenience wrapper: find the TXT URL then download and return the text.

    Returns ``None`` if either step fails.
    """
    txt_url = find_txt_url(detail_url, site)
    if txt_url is None:
        return None
    return download_txt(txt_url, site)
