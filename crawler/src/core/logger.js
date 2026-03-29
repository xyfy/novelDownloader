'use strict';

const winston = require('winston');
const path = require('path');
const fs = require('fs');

const ROOT = path.resolve(__dirname, '../../..');
const logDir = path.join(ROOT, 'data/logs');
fs.mkdirSync(logDir, { recursive: true });

const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { service: 'crawler' },
  transports: [
    new winston.transports.Console({
      format: winston.format.combine(
        winston.format.colorize(),
        winston.format.printf(({ timestamp, level, message, ...rest }) => {
          const extra = Object.keys(rest).length > 1
            ? ' ' + JSON.stringify(rest)
            : '';
          return `${timestamp} [${level}] ${message}${extra}`;
        })
      ),
    }),
    new winston.transports.File({
      filename: path.join(logDir, 'crawler.log'),
    }),
  ],
});

module.exports = logger;
