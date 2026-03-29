'use strict';

/**
 * Shared HTTP utilities: user-agent pool, random delay helper, and proxy config.
 *
 * All axios calls should go through buildRequestOptions() so that every
 * outgoing request carries a realistic User-Agent and (optionally) a proxy.
 */

// A small pool of up-to-date desktop browser UA strings.
const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0',
];

/**
 * Pick a random User-Agent from the pool.
 * @returns {string}
 */
function getRandomUserAgent() {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

/**
 * Return a random integer in [min, max] (both inclusive).
 *
 * @param {number} min
 * @param {number} max
 * @returns {number}
 */
function randomBetween(min, max) {
  if (min >= max) return min;
  return Math.floor(min + Math.random() * (max - min + 1));
}

/**
 * Parse a proxy URL string (e.g. "http://user:pass@host:8080") into an axios
 * proxy config object.  Returns undefined when the string is empty or invalid.
 *
 * @param {string} [raw]
 * @returns {{ protocol: string, host: string, port: number, auth?: { username: string, password: string } } | undefined}
 */
function _parseProxy(raw) {
  if (!raw) return undefined;
  try {
    const u = new URL(raw);
    const proxy = {
      protocol: u.protocol,
      host: u.hostname,
      port: parseInt(u.port, 10) || (u.protocol === 'https:' ? 443 : 80),
    };
    if (u.username) {
      proxy.auth = {
        username: decodeURIComponent(u.username),
        password: decodeURIComponent(u.password),
      };
    }
    return proxy;
  } catch (_) {
    return undefined;
  }
}

// Resolve proxy once at module load from env vars (standard names accepted).
const _proxy = _parseProxy(
  process.env.CRAWLER_PROXY || process.env.HTTP_PROXY || process.env.HTTPS_PROXY || ''
);

/**
 * Build an axios options object with a random User-Agent header and, if
 * configured, a proxy.  Caller-supplied options (e.g. timeout, maxRedirects)
 * are merged in; caller-supplied headers are merged on top of the UA header.
 *
 * @param {object} [extra]  Additional axios options.
 * @returns {object}
 */
function buildRequestOptions(extra = {}) {
  const { headers: extraHeaders, ...rest } = extra;
  const opts = {
    ...rest,
    headers: { 'User-Agent': getRandomUserAgent(), ...extraHeaders },
  };
  if (_proxy) opts.proxy = _proxy;
  return opts;
}

module.exports = { USER_AGENTS, getRandomUserAgent, randomBetween, buildRequestOptions };
