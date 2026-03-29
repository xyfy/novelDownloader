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
