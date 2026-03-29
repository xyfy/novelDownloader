#!/usr/bin/env python3
"""
novelDownloader — entry point.

Usage
-----
  # Run with the default config (config/sites.yaml), all sites, unlimited novels:
  python main.py

  # Only process novels from the 'txt520' site:
  python main.py --site txt520

  # Limit to the first 5 novels (useful for testing):
  python main.py --limit 5

  # Use a custom config file:
  python main.py --config /path/to/my_sites.yaml

  # Use a custom SQLite database path:
  python main.py --db /path/to/novels.db
"""
import argparse
import logging
import sys
from typing import List, Optional

from src.config_loader import ConfigError, SiteConfig, load_config
from src.crawler import crawl_novel_links
from src.downloader import fetch_novel_txt
from src.parser import parse_txt
from src.storage import Database


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )


def _process_site(
    site: SiteConfig,
    db: Database,
    limit: Optional[int] = None,
) -> int:
    """Crawl, download, parse and store all novels for *site*.

    Returns the number of novels successfully saved.
    """
    novel_urls = crawl_novel_links(site)

    if limit is not None:
        novel_urls = novel_urls[:limit]

    saved = 0
    for idx, detail_url in enumerate(novel_urls, start=1):
        logging.info(
            "[%s] Processing novel %d/%d: %s",
            site.name,
            idx,
            len(novel_urls),
            detail_url,
        )

        txt_content = fetch_novel_txt(detail_url, site)
        if txt_content is None:
            logging.warning("[%s] Skipping %s (download failed)", site.name, detail_url)
            continue

        novel = parse_txt(txt_content, source_url=detail_url, site=site)
        db.save_novel(novel)
        saved += 1

    return saved


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download and store novels from configurable web sources.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config",
        default=None,
        metavar="PATH",
        help="Path to the YAML config file (default: config/sites.yaml).",
    )
    parser.add_argument(
        "--site",
        default=None,
        metavar="NAME",
        help="Only process the site with this name (default: all sites).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of novels to process per site.",
    )
    parser.add_argument(
        "--db",
        default="novels.db",
        metavar="PATH",
        help="Path to the SQLite database file (default: novels.db).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    try:
        sites = load_config(args.config)
    except ConfigError as exc:
        logging.error("Configuration error: %s", exc)
        return 1

    if args.site:
        sites = [s for s in sites if s.name == args.site]
        if not sites:
            logging.error("No site named '%s' found in config.", args.site)
            return 1

    db = Database(args.db)
    total_saved = 0

    for site in sites:
        logging.info("=== Processing site: %s ===", site.name)
        saved = _process_site(site, db, limit=args.limit)
        logging.info("[%s] Saved %d novel(s).", site.name, saved)
        total_saved += saved

    logging.info("Done. Total novels saved: %d", total_saved)
    return 0


if __name__ == "__main__":
    sys.exit(main())
