'use strict';

/**
 * BaseSiteAdapter – abstract base class for all site adapters.
 *
 * Every adapter must implement the four abstract methods below.
 * The scheduler calls them in order for each scraping run.
 */
class BaseSiteAdapter {
  /**
   * Unique site identifier used as a filename prefix and DB key.
   * @returns {string}
   */
  get siteId() {
    throw new Error(`${this.constructor.name} must implement siteId`);
  }

  /**
   * Given the seed URL of the listing section, return an array of all
   * paginated list-page URLs to scrape.
   *
   * @param {string} seedUrl  - The first page URL (from config).
   * @param {number} [pages]  - Max pages to return; Infinity means "all".
   * @returns {Promise<string[]>}
   */
  // eslint-disable-next-line no-unused-vars
  async getListPageUrls(seedUrl, pages = Infinity) {
    throw new Error(`${this.constructor.name} must implement getListPageUrls`);
  }

  /**
   * Parse a list/index page and extract a summary for each book.
   *
   * @param {import('cheerio').CheerioAPI} $  - Loaded cheerio instance.
   * @param {string} url                       - URL of the page being parsed.
   * @returns {{ id: string, detailUrl: string, title: string, category?: string }[]}
   */
  // eslint-disable-next-line no-unused-vars
  parseListPage($, url) {
    throw new Error(`${this.constructor.name} must implement parseListPage`);
  }

  /**
   * Parse a book detail page and extract metadata + the download-jump URL.
   *
   * @param {import('cheerio').CheerioAPI} $  - Loaded cheerio instance.
   * @param {string} url                       - URL of the page being parsed.
   * @returns {{
   *   title: string,
   *   author?: string,
   *   category?: string,
   *   summary?: string,
   *   fileSize?: string,
   *   downloadPageUrl: string
   * }}
   */
  // eslint-disable-next-line no-unused-vars
  parseDetailPage($, url) {
    throw new Error(`${this.constructor.name} must implement parseDetailPage`);
  }

  /**
   * Parse the download-jump page and return the final direct download URL.
   *
   * @param {import('cheerio').CheerioAPI} $  - Loaded cheerio instance.
   * @param {string} url                       - URL of the page being parsed.
   * @returns {string}  Final download URL (e.g. doaction.php?pass=…)
   */
  // eslint-disable-next-line no-unused-vars
  parseDownloadPage($, url) {
    throw new Error(`${this.constructor.name} must implement parseDownloadPage`);
  }
}

module.exports = BaseSiteAdapter;
