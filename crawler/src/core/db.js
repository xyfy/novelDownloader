'use strict';

const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

let _db = null;

/**
 * Return the singleton SQLite connection, creating / migrating the schema on
 * first call.
 *
 * @param {string} [dbPath]  Path to the .db file.  Defaults to config value.
 * @returns {import('better-sqlite3').Database}
 */
function getDb(dbPath) {
  if (_db) return _db;

  if (!dbPath) {
    const config = require('../../config');
    dbPath = config.db.sqlitePath;
  }

  // Ensure parent directory exists
  fs.mkdirSync(path.dirname(dbPath), { recursive: true });

  _db = new Database(dbPath);
  _db.pragma('journal_mode = WAL');

  _db.exec(`
    CREATE TABLE IF NOT EXISTS crawler_tasks (
      url           TEXT    PRIMARY KEY,
      task_type     TEXT    NOT NULL,          -- 'list' | 'detail' | 'download'
      status        TEXT    NOT NULL DEFAULT 'pending',  -- pending | done | failed
      task_data     TEXT    DEFAULT NULL,      -- JSON metadata for the task
      retry_count   INTEGER NOT NULL DEFAULT 0,
      last_error    TEXT    DEFAULT NULL,
      created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
      updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    );
  `);

  return _db;
}

/**
 * Insert or ignore a task URL.
 * @param {string} url
 * @param {string} taskType
 * @param {string} [status='pending']
 */
function upsert(url, taskType, status = 'pending') {
  const db = getDb();
  db.prepare(`
    INSERT INTO crawler_tasks (url, task_type, status)
    VALUES (?, ?, ?)
    ON CONFLICT(url) DO NOTHING
  `).run(url, taskType, status);
}

/**
 * Mark a URL as done.
 * @param {string} url
 */
function markDone(url) {
  getDb().prepare(`
    UPDATE crawler_tasks
    SET status = 'done', updated_at = datetime('now')
    WHERE url = ?
  `).run(url);
}

/**
 * Mark a URL as failed and record the error message.
 * @param {string} url
 * @param {string} err
 */
function markFailed(url, err) {
  getDb().prepare(`
    UPDATE crawler_tasks
    SET status = 'failed',
        last_error = ?,
        retry_count = retry_count + 1,
        updated_at = datetime('now')
    WHERE url = ?
  `).run(String(err).slice(0, 500), url);
}

/**
 * Reset a failed task back to pending for retry.
 * @param {string} url
 */
function resetToPending(url) {
  getDb().prepare(`
    UPDATE crawler_tasks
    SET status = 'pending', updated_at = datetime('now')
    WHERE url = ?
  `).run(url);
}

/**
 * Get all pending tasks of a given type.
 * @param {string} taskType
 * @returns {{ url: string, task_type: string, retry_count: number }[]}
 */
function getPending(taskType) {
  return getDb().prepare(`
    SELECT url, task_type, retry_count
    FROM crawler_tasks
    WHERE task_type = ? AND status = 'pending'
    ORDER BY created_at ASC
  `).all(taskType);
}

/**
 * Get the status of a single URL.
 * @param {string} url
 * @returns {string|null}
 */
function getStatus(url) {
  const row = getDb().prepare('SELECT status FROM crawler_tasks WHERE url = ?').get(url);
  return row ? row.status : null;
}

/**
 * Set the task_data JSON blob for a URL.
 * @param {string} url
 * @param {object} data
 */
function setTaskData(url, data) {
  getDb().prepare(`
    UPDATE crawler_tasks SET task_data = ?, updated_at = datetime('now') WHERE url = ?
  `).run(JSON.stringify(data), url);
}

/**
 * Get the task_data JSON blob for a URL.
 * @param {string} url
 * @returns {object}
 */
function getTaskData(url) {
  const row = getDb().prepare('SELECT task_data FROM crawler_tasks WHERE url = ?').get(url);
  if (!row || !row.task_data) return {};
  try { return JSON.parse(row.task_data); } catch (_) { return {}; }
}

/**
 * Close the database connection (useful in tests).
 */
function close() {
  if (_db) {
    _db.close();
    _db = null;
  }
}

module.exports = { getDb, upsert, markDone, markFailed, resetToPending, getPending, getStatus, setTaskData, getTaskData, close };
