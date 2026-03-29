'use strict';

const cheerio = require('cheerio');

// Load the adapter under test
const Txt520Adapter = require('../../src/sites/txt520');
const adapter = new Txt520Adapter();

// ── Helper ────────────────────────────────────────────────────────────────────

function load(html) {
  return cheerio.load(html);
}

const BASE_URL = 'https://www.txt520.org';

// ── siteId ───────────────────────────────────────────────────────────────────

describe('Txt520Adapter.siteId', () => {
  test('returns "txt520"', () => {
    expect(adapter.siteId).toBe('txt520');
  });
});

// ── parseListPage ─────────────────────────────────────────────────────────────

describe('Txt520Adapter.parseListPage', () => {
  const listHtml = `
    <ul>
      <li><a href="/xuanhuan/12345.html">斗破苍穹</a></li>
      <li><a href="/wuxia/67890.html">天龙八部</a></li>
      <li><a href="/xuanhuan/99.html">短书名</a></li>
      <li><a href="/about">关于我们</a></li>
      <li><a href="/xuanhuan/notanumber.html">非数字ID</a></li>
    </ul>
  `;

  test('extracts books with numeric IDs', () => {
    const $ = load(listHtml);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    expect(items.length).toBe(3);
  });

  test('item has correct id, title, category, and full detailUrl', () => {
    const $ = load(listHtml);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    const first = items[0];
    expect(first.id).toBe('12345');
    expect(first.title).toBe('斗破苍穹');
    expect(first.category).toBe('xuanhuan');
    expect(first.detailUrl).toBe(`${BASE_URL}/xuanhuan/12345.html`);
  });

  test('ignores non-book links (no /{category}/{id}.html pattern)', () => {
    const $ = load(listHtml);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    const urls = items.map(i => i.detailUrl);
    expect(urls).not.toContain(`${BASE_URL}/about`);
  });

  test('ignores links with non-numeric IDs', () => {
    const $ = load(listHtml);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    const ids = items.map(i => i.id);
    expect(ids).not.toContain('notanumber');
  });

  test('returns empty array for blank page', () => {
    const $ = load('<html><body></body></html>');
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    expect(items).toEqual([]);
  });
});

// ── parseDetailPage ───────────────────────────────────────────────────────────

describe('Txt520Adapter.parseDetailPage', () => {
  const detailHtml = `
    <html>
      <body>
        <h1>斗破苍穹</h1>
        <p>作者：天蚕土豆</p>
        <p>类型：玄幻</p>
        <p>大小：3.5 MB</p>
        <div class="intro">少年，意气风发，英雄盖世。</div>
        <a href="/e/DownSys/page/1-12345.html">下载</a>
      </body>
    </html>
  `;

  test('extracts title from h1', () => {
    const $ = load(detailHtml);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.title).toBe('斗破苍穹');
  });

  test('extracts author', () => {
    const $ = load(detailHtml);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.author).toBe('天蚕土豆');
  });

  test('extracts fileSize', () => {
    const $ = load(detailHtml);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.fileSize).toContain('3.5');
  });

  test('extracts downloadPageUrl as absolute URL', () => {
    const $ = load(detailHtml);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.downloadPageUrl).toBe(`${BASE_URL}/e/DownSys/page/1-12345.html`);
  });

  test('downloadPageUrl is empty when no DownSys link is present', () => {
    const $ = load('<html><body><h1>书名</h1></body></html>');
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.downloadPageUrl).toBe('');
  });

  test('preserves absolute downloadPageUrl without prepending origin', () => {
    const html = `
      <html><body>
        <h1>书</h1>
        <a href="https://cdn.example.com/e/DownSys/page/1-99.html">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/99.html`);
    expect(result.downloadPageUrl).toBe('https://cdn.example.com/e/DownSys/page/1-99.html');
  });

  // ── lastUpdated extraction ────────────────────────────────────────────────

  test('returns null lastUpdated when no update-time element exists', () => {
    const $ = load(detailHtml);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/12345.html`);
    expect(result.lastUpdated).toBeNull();
  });

  test('extracts lastUpdated from <p>更新时间：…</p>', () => {
    const html = `
      <html><body>
        <h1>书名</h1>
        <p>更新时间：2025-03-15 08:30</p>
        <a href="/e/DownSys/page/1-1.html">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/1.html`);
    expect(result.lastUpdated).toBeTruthy();
    expect(result.lastUpdated).toContain('2025-03-15');
  });

  test('extracts lastUpdated from <p>最后更新：…</p>', () => {
    const html = `
      <html><body>
        <h1>书名</h1>
        <p>最后更新：2024-12-01</p>
        <a href="/e/DownSys/page/1-1.html">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/1.html`);
    expect(result.lastUpdated).toBeTruthy();
    expect(result.lastUpdated).toContain('2024-12-01');
  });

  test('extracts lastUpdated from <span class="update_time">…</span>', () => {
    const html = `
      <html><body>
        <h1>书名</h1>
        <span class="update_time">更新时间：2026-01-10 12:00</span>
        <a href="/e/DownSys/page/1-2.html">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const result = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/2.html`);
    expect(result.lastUpdated).toBeTruthy();
    expect(result.lastUpdated).toContain('2026-01-10');
  });

  test('lastUpdated is an ISO-8601 string when successfully parsed', () => {
    const html = `
      <html><body>
        <h1>书名</h1>
        <p>更新时间：2025-06-20 09:15</p>
        <a href="/e/DownSys/page/1-3.html">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const { lastUpdated } = adapter.parseDetailPage($, `${BASE_URL}/xuanhuan/3.html`);
    expect(lastUpdated).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });
});

// ── parseListPage – lastUpdated ───────────────────────────────────────────────

describe('Txt520Adapter.parseListPage – lastUpdated', () => {
  test('returns null lastUpdated when list items have no date', () => {
    const html = `
      <ul>
        <li><a href="/xuanhuan/11111.html">书名甲</a></li>
        <li><a href="/xuanhuan/22222.html">书名乙</a></li>
      </ul>
    `;
    const $ = load(html);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    expect(items.length).toBeGreaterThan(0);
    items.forEach(item => expect(item.lastUpdated).toBeNull());
  });

  test('extracts lastUpdated from a <span class="date"> sibling', () => {
    const html = `
      <ul>
        <li>
          <a href="/xuanhuan/33333.html">书名丙</a>
          <span class="date">2025-09-01</span>
        </li>
      </ul>
    `;
    const $ = load(html);
    const items = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    expect(items).toHaveLength(1);
    expect(items[0].lastUpdated).toBeTruthy();
    expect(items[0].lastUpdated).toContain('2025-09-01');
  });

  test('lastUpdated from list item is an ISO-8601 string', () => {
    const html = `
      <ul>
        <li>
          <a href="/wuxia/44444.html">书名丁</a>
          <span class="date">2024-07-15</span>
        </li>
      </ul>
    `;
    const $ = load(html);
    const [item] = adapter.parseListPage($, `${BASE_URL}/latest/index_1.html`);
    expect(item.lastUpdated).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/);
  });
});

// ── parseDownloadPage ─────────────────────────────────────────────────────────

describe('Txt520Adapter.parseDownloadPage', () => {
  const jumpHtml = `
    <html>
      <body>
        <a href="/e/DownSys/doaction.php?pass=ABC123&id=12345&t=1">点击下载</a>
      </body>
    </html>
  `;

  test('extracts final download URL from doaction.php link', () => {
    const $ = load(jumpHtml);
    const result = adapter.parseDownloadPage($, `${BASE_URL}/e/DownSys/page/1-12345.html`);
    expect(result).toContain('doaction.php');
    expect(result).toContain('pass=ABC123');
  });

  test('returns absolute URL', () => {
    const $ = load(jumpHtml);
    const result = adapter.parseDownloadPage($, `${BASE_URL}/e/DownSys/page/1-12345.html`);
    expect(result.startsWith('http')).toBe(true);
  });

  test('returns empty string when no doaction.php link is found', () => {
    const $ = load('<html><body><a href="/other">其他</a></body></html>');
    const result = adapter.parseDownloadPage($, `${BASE_URL}/e/DownSys/page/1-12345.html`);
    expect(result).toBe('');
  });

  test('preserves already-absolute doaction.php URL', () => {
    const html = `
      <html><body>
        <a href="https://cdn.example.com/e/DownSys/doaction.php?pass=XYZ">下载</a>
      </body></html>
    `;
    const $ = load(html);
    const result = adapter.parseDownloadPage($, `${BASE_URL}/e/DownSys/page/1-99.html`);
    expect(result).toBe('https://cdn.example.com/e/DownSys/doaction.php?pass=XYZ');
  });
});
