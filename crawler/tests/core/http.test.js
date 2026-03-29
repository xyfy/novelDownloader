'use strict';

/**
 * Tests for src/core/http.js
 *
 * Validates user-agent rotation, random delay helper, proxy parsing, and
 * request option building – all without making real network calls.
 */

// Re-require the module fresh before each describe block to allow
// environment-variable overrides to take effect.
let http;

beforeEach(() => {
  jest.resetModules();
  delete process.env.CRAWLER_PROXY;
  delete process.env.HTTP_PROXY;
  delete process.env.HTTPS_PROXY;
  http = require('../../src/core/http');
});

// ── USER_AGENTS pool ──────────────────────────────────────────────────────────

describe('http – USER_AGENTS', () => {
  test('contains at least 5 distinct entries', () => {
    expect(http.USER_AGENTS.length).toBeGreaterThanOrEqual(5);
    const unique = new Set(http.USER_AGENTS);
    expect(unique.size).toBe(http.USER_AGENTS.length);
  });
});

// ── getRandomUserAgent ────────────────────────────────────────────────────────

describe('http – getRandomUserAgent', () => {
  test('returns a non-empty string', () => {
    expect(typeof http.getRandomUserAgent()).toBe('string');
    expect(http.getRandomUserAgent().length).toBeGreaterThan(0);
  });

  test('always returns a value from the USER_AGENTS pool', () => {
    for (let i = 0; i < 100; i++) {
      expect(http.USER_AGENTS).toContain(http.getRandomUserAgent());
    }
  });

  test('returns different values over many calls (pool coverage)', () => {
    const seen = new Set();
    for (let i = 0; i < 200; i++) {
      seen.add(http.getRandomUserAgent());
    }
    // With 6 agents and 200 draws, seeing > 1 distinct value is almost certain.
    expect(seen.size).toBeGreaterThan(1);
  });
});

// ── randomBetween ─────────────────────────────────────────────────────────────

describe('http – randomBetween', () => {
  test('always returns a value within [min, max]', () => {
    for (let i = 0; i < 2000; i++) {
      const v = http.randomBetween(3000, 10000);
      expect(v).toBeGreaterThanOrEqual(3000);
      expect(v).toBeLessThanOrEqual(10000);
    }
  });

  test('returns min when min === max', () => {
    expect(http.randomBetween(5000, 5000)).toBe(5000);
  });

  test('returns min when max < min (degenerate case)', () => {
    expect(http.randomBetween(8000, 3000)).toBe(8000);
  });

  test('returns an integer', () => {
    for (let i = 0; i < 100; i++) {
      expect(Number.isInteger(http.randomBetween(0, 100))).toBe(true);
    }
  });
});

// ── buildRequestOptions (no proxy) ───────────────────────────────────────────

describe('http – buildRequestOptions (no proxy)', () => {
  test('includes a User-Agent header', () => {
    const opts = http.buildRequestOptions();
    expect(opts.headers).toBeDefined();
    expect(typeof opts.headers['User-Agent']).toBe('string');
    expect(http.USER_AGENTS).toContain(opts.headers['User-Agent']);
  });

  test('merges top-level extra options', () => {
    const opts = http.buildRequestOptions({ timeout: 5000, maxRedirects: 5 });
    expect(opts.timeout).toBe(5000);
    expect(opts.maxRedirects).toBe(5);
  });

  test('merges extra headers alongside User-Agent', () => {
    const opts = http.buildRequestOptions({ headers: { Accept: 'text/html' } });
    expect(opts.headers.Accept).toBe('text/html');
    expect(opts.headers['User-Agent']).toBeTruthy();
  });

  test('does not include proxy when CRAWLER_PROXY is not set', () => {
    const opts = http.buildRequestOptions();
    expect(opts.proxy).toBeUndefined();
  });

  test('preserves responseType from extra options', () => {
    const opts = http.buildRequestOptions({ responseType: 'arraybuffer' });
    expect(opts.responseType).toBe('arraybuffer');
  });
});

// ── buildRequestOptions (with proxy) ─────────────────────────────────────────

describe('http – buildRequestOptions (with CRAWLER_PROXY)', () => {
  beforeEach(() => {
    process.env.CRAWLER_PROXY = 'http://proxyhost:8080';
    jest.resetModules();
    http = require('../../src/core/http');
  });

  test('includes proxy.host and proxy.port when CRAWLER_PROXY is set', () => {
    const opts = http.buildRequestOptions();
    expect(opts.proxy).toBeDefined();
    expect(opts.proxy.host).toBe('proxyhost');
    expect(opts.proxy.port).toBe(8080);
  });
});

describe('http – buildRequestOptions (proxy with auth)', () => {
  beforeEach(() => {
    process.env.CRAWLER_PROXY = 'http://alice:s3cr3t@proxyhost:3128';
    jest.resetModules();
    http = require('../../src/core/http');
  });

  test('includes proxy.auth when credentials are present', () => {
    const opts = http.buildRequestOptions();
    expect(opts.proxy.auth).toEqual({ username: 'alice', password: 's3cr3t' });
  });
});
