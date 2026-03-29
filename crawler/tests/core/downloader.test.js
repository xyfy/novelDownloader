'use strict';

const path = require('path');
const os = require('os');
const fs = require('fs');

// Mock axios at the top level – Jest hoists this before any require
jest.mock('axios');

/**
 * Tests for src/core/downloader.js
 *
 * axios is mocked at module level, so no real HTTP calls are made.
 * A temp directory is used for all file-system operations.
 */

let tempDbDir;
let tempDir;
let db;
let axiosMock;
let downloadBook;

beforeEach(() => {
  jest.resetModules();

  tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'novel-dl-'));
  tempDbDir = fs.mkdtempSync(path.join(os.tmpdir(), 'novel-dldb-'));
  const dbPath = path.join(tempDbDir, 'test.db');

  // Re-require everything fresh so all modules share the same mocked axios
  db = require('../../src/core/db');
  db.getDb(dbPath);
  axiosMock = require('axios');
  ({ downloadBook } = require('../../src/core/downloader'));
});

afterEach(() => {
  db.close();
  fs.rmSync(tempDir, { recursive: true, force: true });
  fs.rmSync(tempDbDir, { recursive: true, force: true });
  jest.clearAllMocks();
});

// ── Helper ────────────────────────────────────────────────────────────────────

function makeMeta(overrides = {}) {
  return {
    siteId: 'txt520',
    sourceId: '99999',
    title: '测试小说',
    author: '张三',
    category: 'fantasy',
    fileSize: '1.2MB',
    sourceUrl: 'http://example.com/fantasy/99999.html',
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('downloader – downloadBook', () => {
  test('writes txt and meta.json to pendingDir on success', async () => {
    axiosMock.get.mockResolvedValue({ data: Buffer.alloc(2048, 0x41) });

    const meta = makeMeta();
    const result = await downloadBook('http://example.com/dl.txt', meta, tempDir);

    // txt file written with correct size
    expect(fs.existsSync(result)).toBe(true);
    expect(fs.readFileSync(result).length).toBe(2048);

    // meta.json written with correct fields
    const metaPath = path.join(tempDir, 'txt520__99999.meta.json');
    expect(fs.existsSync(metaPath)).toBe(true);
    const metaContent = JSON.parse(fs.readFileSync(metaPath, 'utf8'));
    expect(metaContent.title).toBe('测试小说');
    expect(metaContent.siteId).toBe('txt520');
    expect(metaContent.downloadedAt).toBeTruthy();
  });

  test('throws when downloaded file is smaller than MIN_FILE_SIZE_BYTES (1 KB)', async () => {
    axiosMock.get.mockResolvedValue({ data: Buffer.alloc(512, 0x41) });

    await expect(downloadBook('http://example.com/small.txt', makeMeta(), tempDir))
      .rejects.toThrow('too small');
  });

  test('skips download and returns existing path when txt already exists', async () => {
    const existingPath = path.join(tempDir, 'txt520__99999.txt');
    fs.writeFileSync(existingPath, Buffer.alloc(1024));

    const result = await downloadBook('http://example.com/dl.txt', makeMeta(), tempDir);

    expect(result).toBe(existingPath);
    expect(axiosMock.get).not.toHaveBeenCalled();
  });
});
