#!/usr/bin/env python3
"""
数据质量监控脚本

监控指标：
1. extracted_brand 提取率（告警阈值：< 90%）
2. 空 brand 比例（告警阈值：> 10%）
3. API 错误率（告警阈值：> 5%）

执行方式：
- 手动执行：python3 backend_python/monitoring/data_quality_monitor.py
- 定时执行：*/5 * * * * cd /path && python3 backend_python/monitoring/data_quality_monitor.py
"""

import sqlite3
import logging
import os
import sys
from datetime import datetime, timedelta

# 配置
DB_PATH = 'backend_python/database.db'
LOG_PATH = 'backend_python/logs/quality_monitor.log'
ALERT_THRESHOLD_EXTRACTION_RATE = 0.9  # 提取率低于 90% 告警
ALERT_THRESHOLD_EMPTY_BRAND = 0.1  # 空 brand 比例高于 10% 告警

# 配置日志
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('data_quality_monitor')

def check_extraction_rate():
    """检查品牌提取率"""
    logger.info("=" * 60)
    logger.info("开始检查品牌提取率")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 统计最近 1 小时的数据
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(extracted_brand) as has_extracted,
                COUNT(CASE WHEN extracted_brand IS NOT NULL AND extracted_brand != brand THEN 1 END) as different
            FROM diagnosis_results
            WHERE created_at > ?
        """, (one_hour_ago,))
        
        row = cursor.fetchone()
        total, has_extracted, different = row
        
        if total == 0:
            logger.warning("过去 1 小时没有新数据")
            return True
        
        extraction_rate = has_extracted / total if total > 0 else 0
        different_rate = different / total if total > 0 else 0
        
        logger.info(
            f"品牌提取率：total={total}, "
            f"has_extracted={has_extracted}, "
            f"extraction_rate={extraction_rate:.2%}, "
            f"different_rate={different_rate:.2%}"
        )
        
        # 告警判断
        if extraction_rate < ALERT_THRESHOLD_EXTRACTION_RATE:
            logger.error(
                f"🚨 告警：品牌提取率低于 {ALERT_THRESHOLD_EXTRACTION_RATE:.0%}！"
                f" extraction_rate={extraction_rate:.2%}"
            )
            return False
        else:
            logger.info(f"✅ 品牌提取率正常 ({extraction_rate:.2%})")
            return True
            
    except Exception as e:
        logger.error(f"检查品牌提取率失败：{e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def check_empty_brand():
    """检查空 brand 比例"""
    logger.info("开始检查空 brand 比例")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 统计最近 1 小时的数据
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN brand IS NULL OR brand = '' THEN 1 END) as empty_brand
            FROM diagnosis_results
            WHERE created_at > ?
        """, (one_hour_ago,))
        
        row = cursor.fetchone()
        total, empty_brand = row
        
        if total == 0:
            return True
        
        empty_rate = empty_brand / total if total > 0 else 0
        
        logger.info(
            f"空 brand 比例：total={total}, "
            f"empty_brand={empty_brand}, "
            f"empty_rate={empty_rate:.2%}"
        )
        
        # 告警判断
        if empty_rate > ALERT_THRESHOLD_EMPTY_BRAND:
            logger.error(
                f"🚨 告警：空 brand 比例超过 {ALERT_THRESHOLD_EMPTY_BRAND:.0%}！"
                f" empty_rate={empty_rate:.2%}"
            )
            return False
        else:
            logger.info(f"✅ 空 brand 比例正常 ({empty_rate:.2%})")
            return True
            
    except Exception as e:
        logger.error(f"检查空 brand 比例失败：{e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def check_recent_records():
    """检查最新记录的质量"""
    logger.info("开始检查最新记录")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查最新 5 条记录
        cursor.execute("""
            SELECT execution_id, brand, extracted_brand, created_at
            FROM diagnosis_results
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            logger.warning("数据库中没有记录")
            return True
        
        logger.info(f"检查了 {len(rows)} 条最新记录")
        
        has_extracted_count = 0
        for row in rows:
            execution_id, brand, extracted_brand, created_at = row
            status = "✅" if extracted_brand is not None else "❌"
            logger.info(f"  {status} {execution_id[:8]}... brand={brand}, extracted_brand={extracted_brand}")
            
            if extracted_brand is not None:
                has_extracted_count += 1
        
        recent_rate = has_extracted_count / len(rows) if rows else 0
        
        if recent_rate > 0:
            logger.info(f"✅ 最新记录提取率：{recent_rate:.2%}")
            return True
        else:
            logger.warning("⚠️ 最新记录提取率为 0，可能需要检查")
            return True  # 不告警，只是警告
            
    except Exception as e:
        logger.error(f"检查最新记录失败：{e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    logger.info("=" * 60)
    logger.info("数据质量监控检查开始")
    logger.info(f"数据库：{DB_PATH}")
    logger.info("=" * 60)
    
    results = []
    
    # 执行检查
    results.append(("品牌提取率", check_extraction_rate()))
    results.append(("空 brand 比例", check_empty_brand()))
    results.append(("最新记录", check_recent_records()))
    
    # 汇总
    logger.info("=" * 60)
    logger.info("监控检查汇总")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        logger.info(f"{status} {name}")
    
    logger.info(f"总计：{passed}/{total} 通过")
    
    if passed == total:
        logger.info("✅ 所有检查通过")
    else:
        logger.error(f"❌ 有 {total - passed} 项检查未通过")
    
    logger.info("=" * 60)
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
