'use strict';

const BaseSiteAdapter = require('./base');
const axios = require('axios');
const cheerio = require('cheerio');

// Regex patterns used across parser methods
const RE_PAGINATION = /index_(\d+)\.html/;
const RE_BOOK_HREF = /\/\w+\/\d+\.html$/;
const RE_NUMERIC_ID = /^\d+$/;

/**
 * Parse a raw date/time string scraped from the site into an ISO-8601 string.
 * Accepts formats like "2024-01-15", "2024/01/15 12:30", "2024年01月15日", etc.
 *
 * @param {string} raw
 * @returns {string|null}  ISO-8601 string, or null if parsing fails.
 */
function _parseUpdateTime(raw) {
  if (!raw) return null;
  // Strip leading labels like "更新时间：" or "最后更新："
  const cleaned = raw.replace(/^[\s\S]*?[：:]\s*/, '').trim();
  // Match YYYY[sep]MM[sep]DD [HH:MM[:SS]]
  const m = cleaned.match(
    /(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})(?:[^\d](\d{1,2})[^\d](\d{1,2}))?/
  );
  if (!m) return null;
  const [, year, month, day, hour = '00', min = '00'] = m;
  const d = new Date(
    `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}` +
    `T${hour.padStart(2, '0')}:${min.padStart(2, '0')}:00Z`
  );
  return isNaN(d.getTime()) ? null : d.toISOString();
}

/**
 * Site adapter for txt520.org
 *
 * Link chain:
 *   List page  /latest/index_{n}.html
 *     → Detail page  /{category}/{id}.html
 *       → Download-jump page  /e/DownSys/page/{classid}-{id}.html
 *         → Final download  /e/DownSys/doaction.php?pass=HASH…
 */
class Txt520Adapter extends BaseSiteAdapter {
  get siteId() {
    return 'txt520';
  }

  /**
   * Fetch the first list page, read the last-page number, then build all URLs.
   * @param {string} seedUrl
   * @param {number|string} pages  number or 'all'
   * @returns {Promise<string[]>}
   */
  async getListPageUrls(seedUrl, pages = Infinity) {
    const base = new URL(seedUrl);
    const origin = base.origin;

    // Fetch page 1 to find total page count
    const res = await axios.get(seedUrl, { timeout: 15000, headers: { 'User-Agent': 'Mozilla/5.0' } });
    const $ = cheerio.load(res.data);

    // Pagination links like: /latest/index_47.html
    let lastPage = 1;
    $('a[href*="/latest/index_"]').each((_, el) => {
      const m = $(el).attr('href').match(RE_PAGINATION);
      if (m) lastPage = Math.max(lastPage, parseInt(m[1], 10));
    });

    const maxPages = pages === 'all' || pages === Infinity ? lastPage : Math.min(Number(pages), lastPage);
    const urls = [];
    for (let i = 1; i <= maxPages; i++) {
      urls.push(`${origin}/latest/index_${i}.html`);
    }
    return urls;
  }

  /**
   * @param {import('cheerio').CheerioAPI} $
   * @param {string} url
   * @returns {{ id: string, detailUrl: string, title: string, category: string, lastUpdated: string|null }[]}
   */
  parseListPage($, url) {
    const origin = new URL(url).origin;
    const items = [];

    // Each book row: <li> contains <a href="/{category}/{id}.html">title</a>
    // Optionally a <span> or <em> inside the <li> holds the update date.
    $('ul.txt_list li, div.list_con li, .list_ul li, li').each((_, el) => {
      const a = $(el).find('a').first();
      const href = a.attr('href');
      if (!href || !RE_BOOK_HREF.test(href)) return;

      const parts = href.replace(/^\//, '').split('/');
      const idPart = parts[parts.length - 1].replace('.html', '');
      if (!RE_NUMERIC_ID.test(idPart)) return;

      // Try to extract last-update time from a sibling element inside the <li>
      const dateText = $(el).find('span.date, em.date, span.time, em.time, .update_time').first().text().trim()
        || $(el).find('span, em').filter((__, e) => /\d{4}/.test($(e).text())).first().text().trim();
      const lastUpdated = _parseUpdateTime(dateText);

      items.push({
        id: idPart,
        detailUrl: `${origin}${href}`,
        title: a.text().trim(),
        category: parts[0] || '',
        lastUpdated,
      });
    });

    return items;
  }

  /**
   * @param {import('cheerio').CheerioAPI} $
   * @param {string} url
   * @returns {{ title, author, category, summary, fileSize, downloadPageUrl, lastUpdated: string|null }}
   */
  parseDetailPage($, url) {
    const origin = new URL(url).origin;

    const title = $('h1').first().text().trim()
      || $('meta[property="og:title"]').attr('content')?.trim()
      || '';

    const author = $('p:contains("作者")').text().replace(/.*作者[：:]\s*/, '').trim()
      || $('span.author').text().trim()
      || '';

    const category = $('p:contains("类型"), p:contains("分类")').text()
      .replace(/.*[类型分类][：:]\s*/, '').trim()
      || '';

    const summary = $('div.intro, div.summary, p.intro').text().trim() || '';

    const fileSize = $('p:contains("大小"), span:contains("大小")').text()
      .replace(/.*大小[：:]\s*/, '').trim()
      || '';

    // Download jump page: /e/DownSys/page/{classid}-{id}.html
    let downloadPageUrl = '';
    $('a[href*="/e/DownSys/page/"]').each((_, el) => {
      const href = $(el).attr('href');
      if (href) {
        downloadPageUrl = href.startsWith('http') ? href : `${origin}${href}`;
        return false; // break
      }
    });

    // Fallback: look for txt download link pattern
    if (!downloadPageUrl) {
      $('a[href*="DownSys"]').each((_, el) => {
        const href = $(el).attr('href');
        if (href) {
          downloadPageUrl = href.startsWith('http') ? href : `${origin}${href}`;
          return false;
        }
      });
    }

    // Last-update time: try several common element patterns used by Chinese novel sites
    const lastUpdatedRaw = [
      $('p:contains("更新时间")').first().text(),
      $('p:contains("最后更新")').first().text(),
      $('span.update_time, span.updatetime, .last-update').first().text(),
      $('td:contains("更新时间")').first().text(),
      $('li:contains("更新时间")').first().text(),
    ].find(t => t.trim()) || '';
    const lastUpdated = _parseUpdateTime(lastUpdatedRaw);

    return { title, author, category, summary, fileSize, downloadPageUrl, lastUpdated };
  }

  /**
   * @param {import('cheerio').CheerioAPI} $
   * @param {string} url
   * @returns {string}  Final download URL
   */
  parseDownloadPage($, url) {
    const origin = new URL(url).origin;

    // The pass hash is embedded in a link like:
    //   <a href="/e/DownSys/doaction.php?pass=HASH&...">下载</a>
    let downloadUrl = '';
    $('a[href*="doaction.php"]').each((_, el) => {
      const href = $(el).attr('href');
      if (href) {
        downloadUrl = href.startsWith('http') ? href : `${origin}${href}`;
        return false;
      }
    });

    return downloadUrl;
  }
}

module.exports = Txt520Adapter;
