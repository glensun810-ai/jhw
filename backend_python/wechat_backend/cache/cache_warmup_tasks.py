"""
缓存预热任务实现

功能：
- 热门品牌统计预热
- 用户统计预热
- 问题统计预热
- 诊断报告预热
- API 响应预热

参考：P2-7: 智能缓存预热未实现
"""

import sys
import sqlite3
import json
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from wechat_backend.logging_config import api_logger, db_logger
from config.config_cache_warmup import cache_warmup_config


# 数据库路径
DB_PATH = Path(__file__).parent.parent.parent / 'database.db'


def get_db_connection() -> sqlite3.Connection:
    """获取数据库连接"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ==================== 热门品牌统计预热 ====================

def warmup_popular_brands() -> int:
    """
    预热热门品牌统计
    
    Returns:
        缓存的品牌数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询热门品牌
        cursor.execute('''
            SELECT 
                brand_name,
                COUNT(*) as report_count,
                AVG(
                    CAST(json_extract(geo_data, '$.quality_score') AS REAL)
                ) as avg_score
            FROM diagnosis_reports
            WHERE brand_name IS NOT NULL
              AND brand_name != ''
              AND brand_name != '无'
            GROUP BY brand_name
            ORDER BY report_count DESC
            LIMIT ?
        ''', (cache_warmup_config.WARMUP_POPULAR_BRANDS_COUNT,))
        
        brands = cursor.fetchall()
        cached_count = 0
        
        for brand in brands:
            brand_name = brand['brand_name']
            report_count = brand['report_count']
            avg_score = brand['avg_score'] or 0
            
            # 计算品牌统计数据
            stats = calculate_brand_stats(brand_name, cursor)
            
            # 缓存品牌统计
            cache_key = f"brand_stats:{brand_name}"
            cache_value = {
                'brand_name': brand_name,
                'report_count': report_count,
                'avg_score': round(avg_score, 2),
                'stats': stats,
                'cached_at': time.time(),
                'ttl': cache_warmup_config.get_brand_stats_ttl(),
            }
            
            # 写入缓存（使用内存缓存或 Redis）
            _set_cache(cache_key, cache_value, cache_warmup_config.get_brand_stats_ttl())
            cached_count += 1
            
            if cache_warmup_config.WARMUP_VERBOSE_LOGGING:
                db_logger.info(f"预热品牌统计：{brand_name}, 报告数：{report_count}")
        
        conn.close()
        
        api_logger.info(f"热门品牌预热完成：缓存 {cached_count} 个品牌")
        return cached_count
        
    except Exception as e:
        db_logger.error(f"热门品牌预热失败：{e}")
        return 0


def calculate_brand_stats(brand_name: str, cursor: sqlite3.Cursor = None) -> Dict[str, Any]:
    """
    计算品牌统计数据
    
    Args:
        brand_name: 品牌名称
        cursor: 数据库游标（可选）
        
    Returns:
        品牌统计数据
    """
    close_conn = False
    if cursor is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        close_conn = True
    
    try:
        # 查询品牌相关的诊断结果
        cursor.execute('''
            SELECT 
                COUNT(*) as total_tests,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
                AVG(response_latency) as avg_latency,
                AVG(quality_score) as avg_quality
            FROM diagnosis_results
            WHERE brand = ?
        ''', (brand_name,))
        
        result = cursor.fetchone()
        
        stats = {
            'total_tests': result['total_tests'] or 0,
            'success_count': result['success_count'] or 0,
            'success_rate': round(
                (result['success_count'] or 0) / (result['total_tests'] or 1) * 100, 2
            ),
            'avg_latency_ms': round(result['avg_latency'] or 0, 2),
            'avg_quality_score': round(result['avg_quality'] or 0, 2),
        }
        
        # 查询使用的 AI 模型分布
        cursor.execute('''
            SELECT model, COUNT(*) as count
            FROM diagnosis_results
            WHERE brand = ?
            GROUP BY model
            ORDER BY count DESC
        ''', (brand_name,))
        
        models = cursor.fetchall()
        stats['model_distribution'] = [
            {'model': m['model'], 'count': m['count']}
            for m in models
        ]
        
        # 查询情感分布
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN json_extract(geo_data, '$.sentiment') > 0 THEN 1 ELSE 0 END) as positive,
                SUM(CASE WHEN json_extract(geo_data, '$.sentiment') = 0 THEN 1 ELSE 0 END) as neutral,
                SUM(CASE WHEN json_extract(geo_data, '$.sentiment') < 0 THEN 1 ELSE 0 END) as negative
            FROM diagnosis_results
            WHERE brand = ?
              AND geo_data IS NOT NULL
        ''', (brand_name,))
        
        sentiment = cursor.fetchone()
        stats['sentiment_distribution'] = {
            'positive': sentiment['positive'] or 0,
            'neutral': sentiment['neutral'] or 0,
            'negative': sentiment['negative'] or 0,
        }
        
        return stats
        
    finally:
        if close_conn:
            conn.close()


# ==================== 用户统计预热 ====================

def warmup_user_stats() -> int:
    """
    预热用户统计
    
    Returns:
        缓存的用户数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询活跃用户
        cursor.execute('''
            SELECT 
                user_id,
                COUNT(*) as report_count,
                MAX(created_at) as last_active
            FROM diagnosis_reports
            WHERE user_id IS NOT NULL
            GROUP BY user_id
            ORDER BY report_count DESC
            LIMIT ?
        ''', (cache_warmup_config.WARMUP_POPULAR_USERS_COUNT,))
        
        users = cursor.fetchall()
        cached_count = 0
        
        for user in users:
            user_id = user['user_id']
            report_count = user['report_count']
            last_active = user['last_active']
            
            # 计算用户统计数据
            stats = {
                'user_id': user_id,
                'report_count': report_count,
                'last_active': last_active,
                'cached_at': time.time(),
                'ttl': cache_warmup_config.USER_STATS_TTL,
            }
            
            # 缓存用户统计
            cache_key = f"user_stats:{user_id}"
            _set_cache(cache_key, stats, cache_warmup_config.USER_STATS_TTL)
            cached_count += 1
        
        conn.close()
        
        api_logger.info(f"用户统计预热完成：缓存 {cached_count} 个用户")
        return cached_count
        
    except Exception as e:
        db_logger.error(f"用户统计预热失败：{e}")
        return 0


# ==================== 问题统计预热 ====================

def warmup_popular_questions() -> int:
    """
    预热热门问题统计
    
    Returns:
        缓存的问题数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询热门问题
        cursor.execute('''
            SELECT 
                custom_questions as question,
                COUNT(*) as usage_count
            FROM diagnosis_reports
            WHERE custom_questions IS NOT NULL
              AND custom_questions != '[]'
            GROUP BY custom_questions
            ORDER BY usage_count DESC
            LIMIT ?
        ''', (cache_warmup_config.WARMUP_POPULAR_QUESTIONS_COUNT,))
        
        questions = cursor.fetchall()
        cached_count = 0
        
        for q in questions:
            question = q['question']
            usage_count = q['usage_count']
            
            # 解析问题列表
            try:
                question_list = json.loads(question) if isinstance(question, str) else question
                if isinstance(question_list, list):
                    for question_text in question_list[:3]:  # 只缓存前 3 个问题
                        cache_key = f"question_stats:{hash(question_text) & 0xFFFFFFFF}"
                        cache_value = {
                            'question': question_text,
                            'usage_count': usage_count,
                            'cached_at': time.time(),
                            'ttl': cache_warmup_config.QUESTION_STATS_TTL,
                        }
                        _set_cache(cache_key, cache_value, cache_warmup_config.QUESTION_STATS_TTL)
                        cached_count += 1
            except Exception as e:
                # 单个问题预热失败不影响其他问题，记录日志
                api_logger.debug(f"问题 {question} 预热失败：{e}")
        
        conn.close()
        
        api_logger.info(f"问题统计预热完成：缓存 {cached_count} 个问题")
        return cached_count
        
    except Exception as e:
        db_logger.error(f"问题统计预热失败：{e}")
        return 0


# ==================== 诊断报告预热 ====================

def warmup_recent_reports() -> int:
    """
    预热最近的诊断报告
    
    Returns:
        缓存的报告数量
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询最近的诊断报告
        cursor.execute('''
            SELECT 
                execution_id,
                brand_name,
                status,
                progress,
                created_at
            FROM diagnosis_reports
            WHERE status = 'completed'
            ORDER BY created_at DESC
            LIMIT ?
        ''', (cache_warmup_config.WARMUP_RECENT_REPORTS_COUNT,))
        
        reports = cursor.fetchall()
        cached_count = 0
        
        for report in reports:
            execution_id = report['execution_id']
            
            # 缓存报告基本信息
            cache_key = f"report_info:{execution_id}"
            cache_value = {
                'execution_id': execution_id,
                'brand_name': report['brand_name'],
                'status': report['status'],
                'progress': report['progress'],
                'created_at': report['created_at'],
                'cached_at': time.time(),
                'ttl': cache_warmup_config.get_report_stats_ttl(),
            }
            
            _set_cache(cache_key, cache_value, cache_warmup_config.get_report_stats_ttl())
            cached_count += 1
        
        conn.close()
        
        api_logger.info(f"诊断报告预热完成：缓存 {cached_count} 个报告")
        return cached_count
        
    except Exception as e:
        db_logger.error(f"诊断报告预热失败：{e}")
        return 0


# ==================== API 响应预热 ====================

def warmup_api_responses() -> int:
    """
    预热常用 API 响应
    
    Returns:
        缓存的 API 数量
    """
    try:
        # 预热监控大盘数据
        from wechat_backend.services.diagnosis_monitor_service import get_monitoring_dashboard
        
        dashboard_data = get_monitoring_dashboard('today')
        _set_cache(
            'api_cache:monitoring_dashboard:today',
            dashboard_data,
            cache_warmup_config.API_RESPONSE_TTL
        )
        
        # 预热品牌分布数据
        from wechat_backend.analytics.source_aggregator import get_brand_distribution
        
        brand_dist = get_brand_distribution()
        _set_cache(
            'api_cache:brand_distribution',
            brand_dist,
            cache_warmup_config.API_RESPONSE_TTL
        )
        
        api_logger.info("API 响应预热完成")
        return 2  # 缓存了 2 个 API 响应
        
    except Exception as e:
        db_logger.error(f"API 响应预热失败：{e}")
        return 0


# ==================== 缓存工具函数 ====================

def _set_cache(key: str, value: Any, ttl: int):
    """
    设置缓存（支持内存缓存和 Redis）
    
    Args:
        key: 缓存键
        value: 缓存值
        ttl: 缓存时间（秒）
    """
    try:
        # 尝试使用 Redis 缓存
        from wechat_backend.cache.redis_cache import get_redis_client
        
        redis_client = get_redis_client()
        if redis_client:
            import json
            redis_client.setex(
                key,
                ttl,
                json.dumps(value, ensure_ascii=False)
            )
            return
        
    except Exception as e:
        # Redis 缓存失败，降级到内存缓存
        api_logger.debug(f"[CacheWarmup] Redis 缓存失败：{e}, key: {key}, 降级到内存")

    # 回退到内存缓存
    # P1-CACHE-2 修复：导入全局 memory_cache 实例
    from wechat_backend.cache.api_cache import memory_cache
    try:
        memory_cache.set(key, value, ttl)
        api_logger.debug(f"[CacheWarmup] ✅ 内存缓存写入成功：{key}")
    except Exception as mem_err:
        # 内存缓存也失败，记录日志
        api_logger.error(f"[CacheWarmup] 内存缓存失败：{mem_err}, key: {key}")


def _get_cache(key: str) -> Optional[Any]:
    """
    获取缓存
    
    Args:
        key: 缓存键
        
    Returns:
        缓存值，不存在则返回 None
    """
    try:
        # 尝试从 Redis 获取
        from wechat_backend.cache.redis_cache import get_redis_client
        
        redis_client = get_redis_client()
        if redis_client:
            value = redis_client.get(key)
            if value:
                import json
                return json.loads(value)
        
    except Exception as e:
        # Redis 获取失败，降级到内存缓存
        api_logger.debug(f"[CacheWarmup] Redis 获取失败：{e}, key: {key}")

    # 回退到内存缓存
    try:
        from wechat_backend.cache.api_cache import memory_cache
        return memory_cache.get(key)
    except Exception:
        return None


# 导出预热任务函数
__all__ = [
    'warmup_popular_brands',
    'warmup_user_stats',
    'warmup_popular_questions',
    'warmup_recent_reports',
    'warmup_api_responses',
    'calculate_brand_stats',
]
