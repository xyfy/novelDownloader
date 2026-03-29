'use strict';

const Txt520Adapter = require('../sites/txt520');

/** @type {Map<string, import('../sites/base')>} */
const registry = new Map();

// Register all known adapters
const adapters = [new Txt520Adapter()];
for (const adapter of adapters) {
  registry.set(adapter.siteId, adapter);
}

/**
 * Look up an adapter by site ID.
 * @param {string} siteId
 * @returns {import('../sites/base')}
 */
function getAdapter(siteId) {
  const adapter = registry.get(siteId);
  if (!adapter) {
    throw new Error(`No adapter registered for site: "${siteId}". Available: ${[...registry.keys()].join(', ')}`);
  }
  return adapter;
}

/**
 * List all registered site IDs.
 * @returns {string[]}
 */
function listSites() {
  return [...registry.keys()];
}

module.exports = { getAdapter, listSites };
