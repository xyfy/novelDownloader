'use strict';

const axios = require('axios');
const fs = require('fs');
const path = require('path');
const logger = require('./logger');
const db = require('./db');
const { buildRequestOptions } = require('./http');

// Minimum acceptable file size in bytes (files smaller than this are likely error pages)
const MIN_FILE_SIZE_BYTES = 1024;

/**
 * Download a txt file from `downloadUrl` and save it (with a meta.json sidecar)
 * into the `pendingDir` directory.
 *
 * @param {string} downloadUrl  - Final direct download URL.
 * @param {object} meta         - Book metadata object.
 * @param {string} meta.siteId
 * @param {string} meta.sourceId
 * @param {string} meta.title
 * @param {string} [meta.author]
 * @param {string} [meta.category]
 * @param {string} [meta.fileSize]
 * @param {string} [meta.sourceUrl]
 * @param {string} pendingDir   - Absolute path to the pending/ directory.
 * @returns {Promise<string>}   - Path to the written txt file.
 */
async function downloadBook(downloadUrl, meta, pendingDir) {
  const fileName = `${meta.siteId}__${meta.sourceId}.txt`;
  const metaFileName = `${meta.siteId}__${meta.sourceId}.meta.json`;
  const txtPath = path.join(pendingDir, fileName);
  const metaPath = path.join(pendingDir, metaFileName);

  // Skip if already downloaded, unless this is a re-download triggered by a
  // newer last-update timestamp detected on the source site.
  if (fs.existsSync(txtPath) && !meta.redownload) {
    logger.info('skip_existing', { file: fileName });
    return txtPath;
  }

  fs.mkdirSync(pendingDir, { recursive: true });

  const response = await axios.get(downloadUrl, buildRequestOptions({
    responseType: 'arraybuffer',
    maxRedirects: 10,
    timeout: 60000,
  }));

  const buffer = Buffer.from(response.data);

  // Guard: reject files smaller than 1 KB (likely error pages)
  if (buffer.length < MIN_FILE_SIZE_BYTES) {
    throw new Error(`Downloaded file too small (${buffer.length} bytes) – likely an error page`);
  }

  // Write txt (original bytes, preserving encoding)
  fs.writeFileSync(txtPath, buffer);

  // Write meta sidecar
  const metaData = {
    siteId: meta.siteId,
    sourceId: meta.sourceId,
    sourceUrl: meta.sourceUrl || '',
    title: meta.title || '',
    author: meta.author || '',
    category: meta.category || '',
    fileSize: meta.fileSize || '',
    downloadedAt: new Date().toISOString(),
  };
  fs.writeFileSync(metaPath, JSON.stringify(metaData, null, 2));

  logger.info('downloaded', { file: fileName, bytes: buffer.length, url: downloadUrl });

  // Mark URL as done in SQLite
  db.markDone(downloadUrl);

  return txtPath;
}

module.exports = { downloadBook };
