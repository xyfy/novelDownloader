'use strict';

const BaseSiteAdapter = require('./base');

/**
 * Template for a new site adapter.
 *
 * Steps to add a new site:
 * 1. Copy this file and rename it to <siteId>.js
 * 2. Fill in every TODO section.
 * 3. Register the adapter in src/core/siteRegistry.js.
 */
class TemplateSiteAdapter extends BaseSiteAdapter {
  // TODO: change to a unique lowercase identifier, e.g. 'mysite'
  get siteId() {
    return 'template';
  }

  /**
   * TODO: Generate all paginated list-page URLs.
   *
   * Typical pattern:
   *   - Fetch the first page to find the last-page number.
   *   - Build URLs for pages 1..lastPage (up to `pages` limit).
   */
  async getListPageUrls(seedUrl, pages = Infinity) {
    // TODO: implement
    return [seedUrl];
  }

  /**
   * TODO: Extract book entries from a list page.
   *
   * Each entry must have at least { id, detailUrl, title }.
   */
  parseListPage($, url) {
    const items = [];
    // TODO: implement – use cheerio to select the right elements
    // Example:
    // $('a.book-link').each((_, el) => {
    //   const href = $(el).attr('href');
    //   const id   = href.split('/').pop().replace('.html', '');
    //   items.push({ id, detailUrl: new URL(href, url).href, title: $(el).text().trim() });
    // });
    return items;
  }

  /**
   * TODO: Extract book metadata from the detail page.
   *
   * Must return at minimum { title, downloadPageUrl }.
   */
  parseDetailPage($, url) {
    return {
      title: '',           // TODO
      author: '',          // TODO
      category: '',        // TODO
      summary: '',         // TODO
      fileSize: '',        // TODO
      downloadPageUrl: '', // TODO – URL of the download-jump page
    };
  }

  /**
   * TODO: Extract the final direct-download URL from the download-jump page.
   *
   * Typically this is an <a> href containing 'doaction.php' or similar.
   */
  parseDownloadPage($, url) {
    // TODO: implement
    return '';
  }
}

module.exports = TemplateSiteAdapter;
