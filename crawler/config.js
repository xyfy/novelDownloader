'use strict';

const path = require('path');

// Root of the project (one level up from crawler/)
const ROOT = path.resolve(__dirname, '..');

module.exports = {
  sites: {
    txt520: {
      seedUrl: 'https://www.txt520.org/latest/index_1.html',
      concurrency: parseInt(process.env.CRAWLER_CONCURRENCY, 10) || 2,
      requestIntervalMs: parseInt(process.env.CRAWLER_REQUEST_INTERVAL_MS, 10) || 3000,
      requestIntervalMaxMs: parseInt(process.env.CRAWLER_REQUEST_INTERVAL_MAX_MS, 10) || 10000,
    },
  },
  dirs: {
    pending: process.env.PENDING_DIR || path.join(ROOT, 'data/downloads/pending'),
    processing: process.env.PROCESSING_DIR || path.join(ROOT, 'data/downloads/processing'),
    done: process.env.DONE_DIR || path.join(ROOT, 'data/downloads/done'),
    failed: process.env.FAILED_DIR || path.join(ROOT, 'data/downloads/failed'),
  },
  db: {
    sqlitePath: process.env.SQLITE_PATH || path.join(ROOT, 'data/crawler_tasks.db'),
  },
};
