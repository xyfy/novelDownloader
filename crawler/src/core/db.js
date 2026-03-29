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
      last_updated  TEXT    DEFAULT NULL,      -- ISO-8601 last-update time from the source site
      created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
      updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
    );
  `);

  // Migrate: add last_updated to existing tables that pre-date this column.
  try {
    _db.exec('ALTER TABLE crawler_tasks ADD COLUMN last_updated TEXT DEFAULT NULL');
  } catch (_) {
    // Column already exists – safe to ignore.
  }

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

/**
 * Seed a list-page URL, always resetting it to 'pending' so it is
 * re-scraped on every run and any new or updated books are detected.
 *
 * @param {string} url
 */
function seedListPage(url) {
  getDb().prepare(`
    INSERT INTO crawler_tasks (url, task_type, status)
    VALUES (?, 'list', 'pending')
    ON CONFLICT(url) DO UPDATE SET status = 'pending', updated_at = datetime('now')
  `).run(url);
}

/**
 * Insert a new task as 'pending', or conditionally reset an existing 'done'
 * task back to 'pending' when the source site shows a newer last-update time.
 *
 * Behaviour:
 *   - New URL → insert as 'pending' with the supplied lastUpdated.
 *   - Existing row whose status is 'done' AND newLastUpdated is strictly newer
 *     than the stored value → reset status to 'pending', update last_updated.
 *   - All other cases → no change (idempotent, like the old upsert).
 *
 * @param {string}      url
 * @param {string}      taskType        - 'detail' | 'download'
 * @param {string|null} newLastUpdated  - ISO-8601 string from the source page, or null.
 * @returns {boolean}  true if an existing 'done' row was reset to 'pending'.
 */
function upsertOrReschedule(url, taskType, newLastUpdated = null) {
  const db = getDb();
  const existing = db.prepare(
    'SELECT status, last_updated FROM crawler_tasks WHERE url = ?'
  ).get(url);

  if (!existing) {
    // Brand-new URL – insert as pending.
    db.prepare(`
      INSERT INTO crawler_tasks (url, task_type, status, last_updated)
      VALUES (?, ?, 'pending', ?)
    `).run(url, taskType, newLastUpdated || null);
    return false;
  }

  // Only reset if the task is already done and the site shows a newer update.
  if (
    existing.status === 'done' &&
    newLastUpdated &&
    (!existing.last_updated || newLastUpdated > existing.last_updated)
  ) {
    db.prepare(`
      UPDATE crawler_tasks
      SET status = 'pending', last_updated = ?, updated_at = datetime('now')
      WHERE url = ?
    `).run(newLastUpdated, url);
    return true; // was reset
  }

  return false;
}

/**
 * Return the stored last_updated ISO-8601 string for a URL, or null.
 * @param {string} url
 * @returns {string|null}
 */
function getLastUpdated(url) {
  const row = getDb().prepare('SELECT last_updated FROM crawler_tasks WHERE url = ?').get(url);
  return row ? row.last_updated : null;
}

module.exports = {
  getDb, upsert, markDone, markFailed, resetToPending, getPending, getStatus,
  setTaskData, getTaskData, close,
  seedListPage, upsertOrReschedule, getLastUpdated,
};
