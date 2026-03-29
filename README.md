# novelDownloader

A configurable web scraper that downloads Chinese novel TXT files, parses their
content (title, chapters, body text), and stores everything in a SQLite database.

The scraper targets **https://www.txt520.org/latest/index.html** out of the box,
but every site-specific detail (URL, CSS selectors, encoding, chapter-heading
pattern, pagination) lives in a single YAML file — so switching to a different
source requires only a config change, no code changes.

---

## Project layout

```
novelDownloader/
├── config/
│   └── sites.yaml        ← site configurations (editable)
├── src/
│   ├── config_loader.py  ← loads and validates sites.yaml
│   ├── crawler.py        ← crawls list pages for novel URLs
│   ├── downloader.py     ← downloads TXT files from novel detail pages
│   ├── parser.py         ← parses TXT → title / author / chapters
│   └── storage.py        ← SQLite persistence
├── tests/
│   ├── test_config_loader.py
│   ├── test_parser.py
│   └── test_storage.py
├── main.py               ← CLI entry point
└── requirements.txt
```

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run (downloads & stores all novels from the default site)
python main.py

# 3. Limit to 5 novels (useful for testing)
python main.py --limit 5

# 4. Only process a specific site
python main.py --site txt520

# 5. Use a custom database path
python main.py --db /path/to/my.db

# 6. Verbose / debug output
python main.py --verbose
```

---

## Adding a new site

Open `config/sites.yaml` and add an entry under `sites:`.  A commented-out
template is already included at the bottom of that file.  The required fields
are:

| Field | Description |
|---|---|
| `name` | Short identifier (e.g. `mysite`) |
| `base_url` | Root URL of the site |
| `list_url` | URL of the "latest updates" list page |
| `novel_link_selector` | CSS selector that matches novel links on the list page |
| `txt_download_selector` | CSS selector for the TXT download link on a novel's detail page |
| `txt_encoding` | Encoding of the downloaded TXT files (`utf-8`, `gbk`, …) |
| `chapter_pattern` | Python regex that matches a chapter-heading line |

Optional fields: `headers`, `list_pagination` (for multi-page lists),
`title_search_lines`.

---

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```
