#!/usr/bin/env node
'use strict';

// Load .env from project root if present
require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const { getAdapter, listSites } = require('./src/core/siteRegistry');
const scheduler = require('./src/core/scheduler');
const config = require('./config');
const logger = require('./src/core/logger');

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--site') args.site = argv[++i];
    else if (argv[i] === '--pages') args.pages = argv[++i];
    else if (argv[i] === '--help' || argv[i] === '-h') args.help = true;
  }
  return args;
}

function printHelp() {
  console.log(`
Usage:
  node index.js --site <siteId> [--pages <n|all>]

Options:
  --site    Site identifier. Available: ${listSites().join(', ')}
  --pages   Number of list pages to crawl (default: all)
  --help    Show this help message

Examples:
  node index.js --site txt520 --pages 2
  node index.js --site txt520 --pages all
`);
}

async function main() {
  const args = parseArgs(process.argv);

  if (args.help || !args.site) {
    printHelp();
    process.exit(args.help ? 0 : 1);
  }

  const siteId = args.site;
  const pages = args.pages === 'all' || !args.pages ? 'all' : parseInt(args.pages, 10);

  const siteConfig = config.sites[siteId];
  if (!siteConfig) {
    console.error(`Error: No config found for site "${siteId}". Check crawler/config.js`);
    process.exit(1);
  }

  const adapter = getAdapter(siteId);
  const pendingDir = config.dirs.pending;

  logger.info('crawl_start', { site: siteId, pages, pendingDir });

  await scheduler.run(adapter, {
    pages,
    concurrency: siteConfig.concurrency,
    intervalMs: siteConfig.requestIntervalMs,
    pendingDir,
  });
}

main().catch(err => {
  logger.error('fatal', { error: err.message, stack: err.stack });
  process.exit(1);
});
