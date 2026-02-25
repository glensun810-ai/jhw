/**
 * 工具模块统一导出
 * 
 * 用于微信开发者工具模块解析
 */

const logger = require('./logger');

module.exports = {
  logger,
  ...logger
};
