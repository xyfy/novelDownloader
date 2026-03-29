'use strict';

const pLimit = require('p-limit');
const axios = require('axios');
const cheerio = require('cheerio');
const db = require('./db');
const { downloadBook } = require('./downloader');
const logger = require('./logger');

const MAX_RETRIES = 3;

/**
 * Sleep helper.
 * @param {number} ms
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Fetch a URL with exponential back-off retry.
 *
 * @param {string} url
 * @param {number} retries
 * @param {number} intervalMs  - Base interval between requests.
 * @returns {Promise<import('axios').AxiosResponse>}
 */
async function fetchWithRetry(url, retries = MAX_RETRIES, intervalMs = 3000) {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await axios.get(url, {
        timeout: 20000,
        headers: { 'User-Agent': 'Mozilla/5.0' },
        maxRedirects: 10,
      });
      if (res.status !== 200) throw new Error(`HTTP ${res.status}`);
      return res;
    } catch (err) {
      if (attempt === retries) throw err;
      const wait = intervalMs * Math.pow(2, attempt);
      logger.warn('retry', { url, attempt: attempt + 1, wait_ms: wait, error: err.message });
      await sleep(wait);
    }
  }
}

/**
 * Run the full scraping pipeline for a single adapter instance.
 *
 * @param {import('../sites/base')} adapter
 * @param {object} options
 * @param {number|string} options.pages        - Max list pages or 'all'.
 * @param {number}        options.concurrency  - Max concurrent requests.
 * @param {number}        options.intervalMs   - Milliseconds between requests.
 * @param {string}        options.pendingDir   - Target directory for txt files.
 */
async function run(adapter, { pages, concurrency, intervalMs, pendingDir }) {
  const limit = pLimit(concurrency);

  const stats = { downloaded: 0, failed: 0, skipped: 0 };

  // ── Step 1: Get list page URLs ───────────────────────────────────────────
  logger.info('phase_start', { phase: 'list_pages', site: adapter.siteId });
  const config = require('../../config');
  const seedUrl = config.sites[adapter.siteId].seedUrl;
  const listUrls = await adapter.getListPageUrls(seedUrl, pages);
  logger.info('list_pages_found', { count: listUrls.length });

  // Seed list-page tasks
  for (const url of listUrls) {
    db.upsert(url, 'list');
  }

  // ── Step 2: Scrape list pages → detail URLs ─────────────────────────────
  logger.info('phase_start', { phase: 'detail_pages', site: adapter.siteId });
  const pendingList = db.getPending('list');

  await Promise.all(pendingList.map(task => limit(async () => {
    const { url } = task;
    try {
      const res = await fetchWithRetry(url, MAX_RETRIES, intervalMs);
      const $ = cheerio.load(res.data);
      const items = adapter.parseListPage($, url);

      for (const item of items) {
        db.upsert(item.detailUrl, 'detail');
        db.setTaskData(item.detailUrl, { id: item.id, title: item.title, category: item.category });
      }

      db.markDone(url);
      logger.info('list_page_done', { url, books_found: items.length });
    } catch (err) {
      db.markFailed(url, err.message);
      logger.error('list_page_failed', { url, error: err.message });
    }
    await sleep(intervalMs);
  })));

  // ── Step 3: Scrape detail pages → download-jump URLs ───────────────────
  logger.info('phase_start', { phase: 'download_pages', site: adapter.siteId });
  const pendingDetail = db.getPending('detail');

  await Promise.all(pendingDetail.map(task => limit(async () => {
    const { url } = task;
    const itemMeta = db.getTaskData(url);

    try {
      const res = await fetchWithRetry(url, MAX_RETRIES, intervalMs);
      const $ = cheerio.load(res.data);
      const detail = adapter.parseDetailPage($, url);

      if (!detail.downloadPageUrl) {
        throw new Error('Could not find download page URL');
      }

      // Store detail meta alongside download task
      db.upsert(detail.downloadPageUrl, 'download');
      db.setTaskData(detail.downloadPageUrl, {
        siteId: adapter.siteId,
        sourceId: itemMeta.id || '',
        sourceUrl: url,
        title: detail.title || itemMeta.title || '',
        author: detail.author || '',
        category: detail.category || itemMeta.category || '',
        fileSize: detail.fileSize || '',
      });

      db.markDone(url);
      logger.info('detail_page_done', { url, title: detail.title });
    } catch (err) {
      db.markFailed(url, err.message);
      logger.error('detail_page_failed', { url, error: err.message });
      stats.failed++;
    }
    await sleep(intervalMs);
  })));

  // ── Step 4: Download txt files ──────────────────────────────────────────
  logger.info('phase_start', { phase: 'downloads', site: adapter.siteId });
  const pendingDownloads = db.getPending('download');

  await Promise.all(pendingDownloads.map(task => limit(async () => {
    const { url } = task;
    const meta = db.getTaskData(url);

    // Skip if txt already exists
    const existingStatus = db.getStatus(url);
    if (existingStatus === 'done') {
      stats.skipped++;
      return;
    }

    try {
      const res = await fetchWithRetry(url, MAX_RETRIES, intervalMs);
      const $ = cheerio.load(res.data);
      const finalUrl = adapter.parseDownloadPage($, url);

      if (!finalUrl) {
        throw new Error('Could not find final download URL');
      }

      await downloadBook(finalUrl, meta, pendingDir);
      db.markDone(url);
      stats.downloaded++;
      logger.info('book_downloaded', { title: meta.title, sourceId: meta.sourceId });
    } catch (err) {
      db.markFailed(url, err.message);
      logger.error('book_download_failed', { url, error: err.message });
      stats.failed++;
    }
    await sleep(intervalMs);
  })));

  // ── Summary ─────────────────────────────────────────────────────────────
  logger.info('run_complete', { site: adapter.siteId, ...stats });
}

module.exports = { run };
