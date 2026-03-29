'use strict';

const path = require('path');
const os = require('os');
const fs = require('fs');

// Each test gets its own fresh DB file to avoid state leakage
function makeTempDb() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'novel-db-'));
  return path.join(dir, 'test.db');
}

describe('db – crawler_tasks CRUD', () => {
  let db;
  let dbPath;

  beforeEach(() => {
    // Reset the singleton so each test gets a clean DB
    jest.resetModules();
    dbPath = makeTempDb();
    db = require('../../src/core/db');
    db.getDb(dbPath); // initialise with the temp path
  });

  afterEach(() => {
    db.close();
  });

  // ── upsert ──────────────────────────────────────────────────────────────

  test('upsert inserts a new row', () => {
    db.upsert('http://example.com/1', 'list');
    expect(db.getStatus('http://example.com/1')).toBe('pending');
  });

  test('upsert is idempotent – duplicate insert does not throw', () => {
    db.upsert('http://example.com/2', 'detail');
    expect(() => db.upsert('http://example.com/2', 'detail')).not.toThrow();
    expect(db.getStatus('http://example.com/2')).toBe('pending');
  });

  // ── markDone ─────────────────────────────────────────────────────────────

  test('markDone sets status to done', () => {
    db.upsert('http://example.com/3', 'list');
    db.markDone('http://example.com/3');
    expect(db.getStatus('http://example.com/3')).toBe('done');
  });

  // ── markFailed ───────────────────────────────────────────────────────────

  test('markFailed sets status to failed and records error', () => {
    db.upsert('http://example.com/4', 'download');
    db.markFailed('http://example.com/4', 'timeout');
    expect(db.getStatus('http://example.com/4')).toBe('failed');
  });

  test('markFailed increments retry_count on repeated calls', () => {
    db.upsert('http://example.com/5', 'download');
    db.markFailed('http://example.com/5', 'err1');
    db.markFailed('http://example.com/5', 'err2');
    const row = db.getDb().prepare('SELECT retry_count FROM crawler_tasks WHERE url=?')
      .get('http://example.com/5');
    expect(row.retry_count).toBe(2);
  });

  // ── resetToPending ───────────────────────────────────────────────────────

  test('resetToPending restores a failed task', () => {
    db.upsert('http://example.com/6', 'list');
    db.markFailed('http://example.com/6', 'err');
    db.resetToPending('http://example.com/6');
    expect(db.getStatus('http://example.com/6')).toBe('pending');
  });

  // ── getPending ───────────────────────────────────────────────────────────

  test('getPending returns only pending tasks of the requested type', () => {
    db.upsert('http://example.com/a', 'list');
    db.upsert('http://example.com/b', 'list');
    db.upsert('http://example.com/c', 'detail');
    db.markDone('http://example.com/a');

    const pending = db.getPending('list');
    expect(pending).toHaveLength(1);
    expect(pending[0].url).toBe('http://example.com/b');
  });

  test('getPending returns empty array when nothing is pending', () => {
    expect(db.getPending('download')).toEqual([]);
  });

  // ── getStatus ────────────────────────────────────────────────────────────

  test('getStatus returns null for unknown URL', () => {
    expect(db.getStatus('http://not-in-db.com')).toBeNull();
  });

  // ── task_data ────────────────────────────────────────────────────────────

  test('setTaskData / getTaskData round-trip', () => {
    db.upsert('http://example.com/meta', 'detail');
    db.setTaskData('http://example.com/meta', { title: '斗破苍穹', id: '12345' });
    const data = db.getTaskData('http://example.com/meta');
    expect(data.title).toBe('斗破苍穹');
    expect(data.id).toBe('12345');
  });

  test('getTaskData returns empty object for missing task_data', () => {
    db.upsert('http://example.com/empty', 'list');
    expect(db.getTaskData('http://example.com/empty')).toEqual({});
  });

  test('getTaskData returns empty object for unknown URL', () => {
    expect(db.getTaskData('http://not-here.com')).toEqual({});
  });
});

// ── seedListPage ──────────────────────────────────────────────────────────────

describe('db – seedListPage', () => {
  let db;

  beforeEach(() => {
    jest.resetModules();
    db = require('../../src/core/db');
    db.getDb(require('path').join(require('os').tmpdir(), `novel-seed-${Date.now()}.db`));
  });

  afterEach(() => { db.close(); });

  test('inserts a new list URL as pending', () => {
    db.seedListPage('http://example.com/list/1');
    expect(db.getStatus('http://example.com/list/1')).toBe('pending');
  });

  test('resets an already-done list URL back to pending', () => {
    db.seedListPage('http://example.com/list/2');
    db.markDone('http://example.com/list/2');
    expect(db.getStatus('http://example.com/list/2')).toBe('done');

    db.seedListPage('http://example.com/list/2');
    expect(db.getStatus('http://example.com/list/2')).toBe('pending');
  });

  test('resets a failed list URL back to pending', () => {
    db.seedListPage('http://example.com/list/3');
    db.markFailed('http://example.com/list/3', 'err');
    db.seedListPage('http://example.com/list/3');
    expect(db.getStatus('http://example.com/list/3')).toBe('pending');
  });
});

// ── upsertOrReschedule ────────────────────────────────────────────────────────

describe('db – upsertOrReschedule', () => {
  let db;

  beforeEach(() => {
    jest.resetModules();
    db = require('../../src/core/db');
    db.getDb(require('path').join(require('os').tmpdir(), `novel-uor-${Date.now()}.db`));
  });

  afterEach(() => { db.close(); });

  test('inserts brand-new URL as pending and returns false', () => {
    const reset = db.upsertOrReschedule('http://example.com/d/1', 'detail', '2024-01-01T00:00:00.000Z');
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/1')).toBe('pending');
  });

  test('inserts with null lastUpdated and returns false', () => {
    const reset = db.upsertOrReschedule('http://example.com/d/2', 'detail', null);
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/2')).toBe('pending');
  });

  test('does not change a pending URL (returns false)', () => {
    db.upsertOrReschedule('http://example.com/d/3', 'detail', '2024-01-01T00:00:00.000Z');
    const reset = db.upsertOrReschedule('http://example.com/d/3', 'detail', '2025-01-01T00:00:00.000Z');
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/3')).toBe('pending');
  });

  test('resets a done URL to pending when newLastUpdated is strictly newer', () => {
    db.upsertOrReschedule('http://example.com/d/4', 'detail', '2024-01-01T00:00:00.000Z');
    db.markDone('http://example.com/d/4');

    const reset = db.upsertOrReschedule('http://example.com/d/4', 'detail', '2025-06-01T00:00:00.000Z');
    expect(reset).toBe(true);
    expect(db.getStatus('http://example.com/d/4')).toBe('pending');
  });

  test('does NOT reset a done URL when newLastUpdated equals stored value', () => {
    const ts = '2024-03-15T10:00:00.000Z';
    db.upsertOrReschedule('http://example.com/d/5', 'detail', ts);
    db.markDone('http://example.com/d/5');

    const reset = db.upsertOrReschedule('http://example.com/d/5', 'detail', ts);
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/5')).toBe('done');
  });

  test('does NOT reset a done URL when newLastUpdated is older than stored', () => {
    db.upsertOrReschedule('http://example.com/d/6', 'detail', '2025-01-01T00:00:00.000Z');
    db.markDone('http://example.com/d/6');

    const reset = db.upsertOrReschedule('http://example.com/d/6', 'detail', '2024-01-01T00:00:00.000Z');
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/6')).toBe('done');
  });

  test('does NOT reset a done URL when newLastUpdated is null', () => {
    db.upsertOrReschedule('http://example.com/d/7', 'detail', '2024-01-01T00:00:00.000Z');
    db.markDone('http://example.com/d/7');

    const reset = db.upsertOrReschedule('http://example.com/d/7', 'detail', null);
    expect(reset).toBe(false);
    expect(db.getStatus('http://example.com/d/7')).toBe('done');
  });

  test('resets a done URL when no lastUpdated was previously stored but a new one is provided', () => {
    // Insert without a lastUpdated (simulates old data)
    db.upsert('http://example.com/d/8', 'detail');
    db.markDone('http://example.com/d/8');

    const reset = db.upsertOrReschedule('http://example.com/d/8', 'detail', '2025-01-01T00:00:00.000Z');
    expect(reset).toBe(true);
    expect(db.getStatus('http://example.com/d/8')).toBe('pending');
  });
});

// ── getLastUpdated ────────────────────────────────────────────────────────────

describe('db – getLastUpdated', () => {
  let db;

  beforeEach(() => {
    jest.resetModules();
    db = require('../../src/core/db');
    db.getDb(require('path').join(require('os').tmpdir(), `novel-glu-${Date.now()}.db`));
  });

  afterEach(() => { db.close(); });

  test('returns null for unknown URL', () => {
    expect(db.getLastUpdated('http://not-here.com')).toBeNull();
  });

  test('returns null for URL inserted without lastUpdated', () => {
    db.upsert('http://example.com/x/1', 'detail');
    expect(db.getLastUpdated('http://example.com/x/1')).toBeNull();
  });

  test('returns the ISO string stored via upsertOrReschedule', () => {
    const ts = '2025-03-01T08:00:00.000Z';
    db.upsertOrReschedule('http://example.com/x/2', 'detail', ts);
    expect(db.getLastUpdated('http://example.com/x/2')).toBe(ts);
  });
});
