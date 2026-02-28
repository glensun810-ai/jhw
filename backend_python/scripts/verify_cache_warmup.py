#!/usr/bin/env python3
"""
缓存预热配置验证脚本

用于验证缓存预热配置是否正确，测试预热功能是否正常工作。

使用方法:
    python backend_python/scripts/verify_cache_warmup.py

参考：P2-7: 智能缓存预热未实现
"""

import sys
import os
import time
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from config.config_cache_warmup import CacheWarmupConfig, cache_warmup_config


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_item(name: str, value, status: str = "OK"):
    """打印配置项"""
    status_icon = "✅" if status == "OK" else "❌" if status == "ERROR" else "⚠️"
    print(f"{status_icon} {name}: {value}")


def verify_basic_config():
    """验证基础配置"""
    print_section("缓存预热基础配置验证")
    
    print_item("缓存预热启用状态", cache_warmup_config.is_warmup_enabled())
    print_item("启动时自动预热", cache_warmup_config.is_auto_warmup_enabled())
    print_item("定时预热启用", cache_warmup_config.is_scheduled_warmup_enabled())
    print_item("预热时间表", cache_warmup_config.WARMUP_SCHEDULE)
    print_item("预热间隔（分钟）", cache_warmup_config.WARMUP_INTERVAL_MINUTES)
    
    if cache_warmup_config.is_warmup_enabled():
        print_item("配置状态", "缓存预热已启用", "OK")
    else:
        print_item("配置状态", "缓存预热未启用", "OK")
    
    return True


def verify_warmup_tasks_config():
    """验证预热任务配置"""
    print_section("预热任务配置验证")
    
    print_item("热门品牌预热数量", cache_warmup_config.WARMUP_POPULAR_BRANDS_COUNT)
    print_item("热门用户预热数量", cache_warmup_config.WARMUP_POPULAR_USERS_COUNT)
    print_item("热门问题预热数量", cache_warmup_config.WARMUP_POPULAR_QUESTIONS_COUNT)
    print_item("最近报告预热数量", cache_warmup_config.WARMUP_RECENT_REPORTS_COUNT)
    
    # 验证预热优先级
    tasks = cache_warmup_config.get_warmup_tasks()
    print_item("预热任务列表", ", ".join(tasks))
    
    return True


def verify_cache_ttl_config():
    """验证缓存过期时间配置"""
    print_section("缓存过期时间配置验证")
    
    print_item("品牌统计缓存时间", f"{cache_warmup_config.get_brand_stats_ttl()}s ({cache_warmup_config.get_brand_stats_ttl() // 60}分钟)")
    print_item("用户统计缓存时间", f"{cache_warmup_config.USER_STATS_TTL}s ({cache_warmup_config.USER_STATS_TTL // 60}分钟)")
    print_item("问题统计缓存时间", f"{cache_warmup_config.QUESTION_STATS_TTL}s ({cache_warmup_config.QUESTION_STATS_TTL // 60}分钟)")
    print_item("诊断报告缓存时间", f"{cache_warmup_config.get_report_stats_ttl()}s ({cache_warmup_config.get_report_stats_ttl() // 60}分钟)")
    print_item("API 响应缓存时间", f"{cache_warmup_config.API_RESPONSE_TTL}s ({cache_warmup_config.API_RESPONSE_TTL // 60}分钟)")
    
    return True


def verify_concurrent_config():
    """验证并发配置"""
    print_section("并发预热配置验证")
    
    print_item("并发预热启用", cache_warmup_config.CONCURRENT_WARMUP_ENABLED)
    print_item("预热线程数", cache_warmup_config.WARMUP_THREAD_COUNT)
    print_item("预热超时时间", f"{cache_warmup_config.WARMUP_TIMEOUT_SECONDS}s")
    print_item("详细日志", cache_warmup_config.WARMUP_VERBOSE_LOGGING)
    
    if cache_warmup_config.WARMUP_THREAD_COUNT < 1:
        print_item("线程数配置", "必须大于 0", "ERROR")
        return False
    
    return True


def test_warmup_engine():
    """测试预热器"""
    print_section("预热器功能测试")
    
    try:
        from wechat_backend.cache.cache_warmup import (
            get_warmup_engine,
            get_warmup_status,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 获取预热器
        engine = get_warmup_engine()
        print_item("预热器初始化", "成功", "OK")
        
        # 获取状态
        status = get_warmup_status()
        print_item("预热器状态", "正常")
        print_item("已注册任务", len(status.get('warmup', {}).get('registered_tasks', [])))
        
        return True
        
    except Exception as e:
        print_item("预热器测试", f"失败：{e}", "ERROR")
        return False


def test_scheduler():
    """测试调度器"""
    print_section("调度器功能测试")
    
    try:
        from wechat_backend.cache.cache_warmup_scheduler import (
            get_scheduler,
            get_scheduler_status,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 获取调度器
        scheduler = get_scheduler()
        print_item("调度器初始化", "成功", "OK")
        
        # 获取状态
        status = get_scheduler_status()
        print_item("调度器状态", "正常")
        print_item("运行状态", status.get('running', False))
        
        return True
        
    except Exception as e:
        print_item("调度器测试", f"失败：{e}", "ERROR")
        return False


def test_warmup_tasks():
    """测试预热任务函数"""
    print_section("预热任务函数测试")
    
    try:
        from wechat_backend.cache.cache_warmup_tasks import (
            warmup_popular_brands,
            warmup_user_stats,
            warmup_popular_questions,
            warmup_recent_reports,
            warmup_api_responses,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 测试函数存在
        print_item("热门品牌预热函数", "存在", "OK")
        print_item("用户统计预热函数", "存在", "OK")
        print_item("问题统计预热函数", "存在", "OK")
        print_item("诊断报告预热函数", "存在", "OK")
        print_item("API 响应预热函数", "存在", "OK")
        
        return True
        
    except Exception as e:
        print_item("预热任务测试", f"失败：{e}", "ERROR")
        return False


def validate_full_config():
    """完整配置验证"""
    print_section("完整配置验证")
    
    is_valid, errors = cache_warmup_config.validate_config()
    
    if is_valid:
        print_item("配置验证结果", "通过", "OK")
    else:
        print_item("配置验证结果", "失败", "ERROR")
        print("\n错误列表:")
        for error in errors:
            print_item(f"  - {error}", "", "ERROR")
    
    return is_valid


def print_summary():
    """打印总结"""
    print_section("验证总结")
    
    print("""
缓存预热配置验证完成！

配置说明:

1. 启用缓存预热:
   - 编辑 .env 文件
   - 设置 CACHE_WARMUP_ENABLED=true
   - 设置 AUTO_WARMUP_ON_STARTUP=true (启动时预热)
   - 设置 SCHEDULED_WARMUP_ENABLED=true (定时预热)

2. 配置预热任务:
   - WARMUP_POPULAR_BRANDS_COUNT=20 (热门品牌数量)
   - WARMUP_POPULAR_USERS_COUNT=50 (热门用户数量)
   - WARMUP_POPULAR_QUESTIONS_COUNT=20 (热门问题数量)
   - WARMUP_RECENT_REPORTS_COUNT=100 (最近报告数量)

3. 配置定时任务:
   - WARMUP_SCHEDULE=0 3 * * * (每天凌晨 3 点)
   - WARMUP_INTERVAL_MINUTES=60 (每小时执行一次)

4. 配置缓存时间:
   - BRAND_STATS_TTL=3600 (品牌统计 1 小时)
   - REPORT_STATS_TTL=900 (诊断报告 15 分钟)
   - API_RESPONSE_TTL=300 (API 响应 5 分钟)

5. 重启 Flask 应用:
   cd backend_python
   python main.py

6. 查看预热状态:
   curl http://localhost:5000/api/cache/warmup/status

7. 手动触发预热:
   curl -X POST http://localhost:5000/api/cache/warmup/execute

8. 查看详细文档:
   docs/2026-02-28-P2-7-智能缓存预热实现报告.md
""")


def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        P2-7: 智能缓存预热配置验证脚本                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 执行验证
    results = []
    
    results.append(("基础配置", verify_basic_config()))
    results.append(("预热任务配置", verify_warmup_tasks_config()))
    results.append(("缓存过期时间", verify_cache_ttl_config()))
    results.append(("并发配置", verify_concurrent_config()))
    results.append(("预热器测试", test_warmup_engine()))
    results.append(("调度器测试", test_scheduler()))
    results.append(("预热任务函数", test_warmup_tasks()))
    results.append(("完整配置验证", validate_full_config()))
    
    # 打印总结
    print_summary()
    
    # 返回结果
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✅ 所有验证通过！")
        return 0
    else:
        print("\n❌ 部分验证失败，请检查上述错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
