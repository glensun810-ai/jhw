#!/usr/bin/env python3
"""
AI响应日志清理调度器
定期清理旧的日志文件，释放磁盘空间
"""

import schedule
import time
from datetime import datetime
import logging
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.ai_response_logger_enhanced import get_enhanced_logger

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path(__file__).parent.parent / 'logs' / 'cleanup_scheduler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_cleanup(retention_days: int = 30):
    """执行日志清理任务"""
    try:
        logger.info(f"开始执行日志清理任务，保留最近 {retention_days} 天的日志")
        
        enhanced_logger = get_enhanced_logger()
        enhanced_logger.cleanup_old_logs(retention_days=retention_days)
        
        logger.info("日志清理任务完成")
    except Exception as e:
        logger.error(f"日志清理任务失败: {e}")
        logger.exception(e)


def start_scheduler(retention_days: int = 30, cleanup_hour: int = 2):  # 默认凌晨2点执行
    """启动清理调度器"""
    logger.info(f"启动日志清理调度器，每天 {cleanup_hour} 点执行，保留 {retention_days} 天的日志")
    
    # 每天指定时间执行清理
    schedule.every().day.at(f"{cleanup_hour:02d}:00").do(run_cleanup, retention_days=retention_days)
    
    logger.info("日志清理调度器已启动")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        logger.info("日志清理调度器已停止")
    except Exception as e:
        logger.error(f"日志清理调度器异常: {e}")
        raise


if __name__ == "__main__":
    # 从命令行参数或环境变量获取配置
    import argparse
    
    parser = argparse.ArgumentParser(description='AI响应日志清理调度器')
    parser.add_argument('--retention-days', type=int, default=30, 
                       help='日志保留天数 (默认: 30)')
    parser.add_argument('--cleanup-hour', type=int, default=2,
                       help='清理执行时间 (小时, 0-23, 默认: 2)')
    
    args = parser.parse_args()
    
    # 确保logs目录存在
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    start_scheduler(retention_days=args.retention_days, cleanup_hour=args.cleanup_hour)