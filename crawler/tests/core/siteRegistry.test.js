'use strict';

const { getAdapter, listSites } = require('../../src/core/siteRegistry');

describe('siteRegistry', () => {
  test('listSites returns an array containing "txt520"', () => {
    const sites = listSites();
    expect(Array.isArray(sites)).toBe(true);
    expect(sites).toContain('txt520');
  });

  test('getAdapter("txt520") returns a Txt520Adapter', () => {
    const adapter = getAdapter('txt520');
    expect(adapter).toBeDefined();
    expect(adapter.siteId).toBe('txt520');
  });

  test('getAdapter throws for unknown site', () => {
    expect(() => getAdapter('unknown_site_xyz')).toThrow('"unknown_site_xyz"');
  });

  test('getAdapter error message lists available sites', () => {
    let msg = '';
    try { getAdapter('nope'); } catch (e) { msg = e.message; }
    expect(msg).toContain('txt520');
  });
});
