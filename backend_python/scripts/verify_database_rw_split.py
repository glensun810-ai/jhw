#!/usr/bin/env python3
"""
数据库读写分离配置验证脚本

用于验证数据库读写分离配置是否正确，测试读写分离功能是否正常工作。

使用方法:
    python backend_python/scripts/verify_database_rw_split.py

参考：P2-6: 数据库读写分离未实现
"""

import sys
import os
import time
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from config.config_database import DatabaseRouterConfig, db_router_config


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
    print_section("数据库读写分离基础配置验证")
    
    print_item("读写分离启用状态", db_router_config.is_read_write_splitting_enabled())
    print_item("主数据库路径", db_router_config.get_master_db_path())
    print_item("从数据库路径数量", len(db_router_config.get_slave_db_paths()))
    print_item("路由策略", db_router_config.ROUTE_STRATEGY)
    print_item("故障转移启用", db_router_config.is_failover_enabled())
    
    if db_router_config.is_read_write_splitting_enabled():
        print_item("配置状态", "读写分离已启用", "OK")
    else:
        print_item("配置状态", "读写分离未启用（兼容模式）", "OK")
    
    return True


def verify_master_config():
    """验证主数据库配置"""
    print_section("主数据库配置验证")
    
    master_path = db_router_config.get_master_db_path()
    print_item("主库路径", master_path)
    print_item("主库最大连接数", db_router_config.MASTER_DB_MAX_CONNECTIONS)
    print_item("主库超时时间", f"{db_router_config.MASTER_DB_TIMEOUT}s")
    
    # 检查主库文件是否存在
    if master_path.exists():
        print_item("主库文件", "存在", "OK")
    else:
        print_item("主库文件", "不存在（将自动创建）", "OK")
    
    return True


def verify_slave_config():
    """验证从数据库配置"""
    print_section("从数据库配置验证")
    
    slave_paths = db_router_config.get_slave_db_paths()
    
    if not slave_paths:
        print_item("从库配置", "未配置从库", "OK")
        return True
    
    print_item("从库数量", len(slave_paths))
    
    for i, slave_path in enumerate(slave_paths):
        print_item(f"从库 {i+1} 路径", slave_path)
        
        if slave_path.exists():
            print_item(f"从库 {i+1} 状态", "存在", "OK")
        else:
            print_item(f"从库 {i+1} 状态", "不存在（将自动创建）", "OK")
    
    print_item("从库最大连接数", db_router_config.SLAVE_DB_MAX_CONNECTIONS)
    print_item("从库超时时间", f"{db_router_config.SLAVE_DB_TIMEOUT}s")
    
    return True


def verify_route_strategy():
    """验证路由策略"""
    print_section("路由策略配置验证")
    
    strategy = db_router_config.ROUTE_STRATEGY
    print_item("路由策略", strategy)
    
    if strategy == 'round_robin':
        print_item("策略说明", "轮询分发读请求到各从库")
    elif strategy == 'random':
        print_item("策略说明", "随机分发读请求到各从库")
    elif strategy == 'least_connections':
        print_item("策略说明", "分发到连接数最少的从库")
    elif strategy == 'priority':
        print_item("策略说明", "按优先级分发到从库")
    else:
        print_item("策略说明", "未知策略，使用默认轮询", "OK")
    
    return True


def verify_replication_config():
    """验证复制配置"""
    print_section("数据库复制配置验证")
    
    print_item("复制延迟检查间隔", f"{db_router_config.REPLICATION_LAG_CHECK_INTERVAL}s")
    print_item("最大允许复制延迟", f"{db_router_config.MAX_REPLICATION_LAG}s")
    print_item("复制延迟告警阈值", f"{db_router_config.REPLICATION_LAG_ALERT_THRESHOLD}s")
    print_item("从库健康检查间隔", f"{db_router_config.SLAVE_HEALTH_CHECK_INTERVAL}s")
    print_item("从库失败阈值", db_router_config.SLAVE_FAILURE_THRESHOLD)
    print_item("从库恢复检查间隔", f"{db_router_config.SLAVE_RECOVERY_CHECK_INTERVAL}s")
    
    return True


def verify_write_read_consistency():
    """验证写后读一致性配置"""
    print_section("写后读一致性配置验证")
    
    print_item("写后从主库读取", db_router_config.READ_AFTER_WRITE_FROM_MASTER)
    print_item("写后读取时间窗口", f"{db_router_config.READ_AFTER_WRITE_WINDOW}s")
    
    if db_router_config.READ_AFTER_WRITE_FROM_MASTER:
        print_item("一致性保证", "写操作后在时间窗口内从主库读取", "OK")
    else:
        print_item("一致性保证", "不保证写后读一致性")
    
    return True


def test_connection_routing():
    """测试连接路由功能"""
    print_section("连接路由功能测试")
    
    try:
        # 测试导入
        from wechat_backend.database.database_read_write_split import (
            get_master_connection,
            get_slave_connection,
            get_db_connection,
            return_master_connection,
            return_slave_connection,
            get_master_slave_pool,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 测试获取主从连接池
        pool = get_master_slave_pool()
        print_item("连接池初始化", "成功", "OK")
        
        # 测试获取连接（不实际使用，只测试接口）
        if db_router_config.is_read_write_splitting_enabled():
            print_item("读写分离模式", "已启用")
        else:
            print_item("读写分离模式", "未启用（使用默认连接池）", "OK")
        
        return True
        
    except Exception as e:
        print_item("连接路由测试", f"失败：{e}", "ERROR")
        return False


def test_replication_manager():
    """测试复制管理器"""
    print_section("复制管理器测试")
    
    try:
        from wechat_backend.database.database_replication import (
            get_replication_manager,
            get_replication_status,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 获取复制状态
        status = get_replication_status()
        print_item("复制状态", status.get('enabled', False))
        
        if 'message' in status:
            print_item("状态消息", status['message'])
        
        return True
        
    except Exception as e:
        print_item("复制管理器测试", f"失败：{e}", "ERROR")
        return False


def test_monitoring():
    """测试监控功能"""
    print_section("复制监控测试")
    
    try:
        from wechat_backend.database.database_replication_monitor import (
            get_replication_monitor,
            get_replication_metrics,
        )
        
        print_item("模块导入", "成功", "OK")
        
        # 获取监控指标
        metrics = get_replication_metrics()
        print_item("监控状态", metrics.get('enabled', False))
        
        if 'message' in metrics:
            print_item("监控消息", metrics['message'])
        
        return True
        
    except Exception as e:
        print_item("监控测试", f"失败：{e}", "ERROR")
        return False


def validate_full_config():
    """完整配置验证"""
    print_section("完整配置验证")
    
    is_valid, errors = db_router_config.validate_config()
    
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
数据库读写分离配置验证完成！

配置说明:

1. 启用读写分离（生产环境）:
   - 编辑 .env 文件
   - 设置 READ_WRITE_SPLITTING_ENABLED=true
   - 配置 MASTER_DB_PATH=/path/to/master.db
   - 配置 SLAVE_DB_PATHS=/path/to/slave1.db,/path/to/slave2.db

2. 配置路由策略:
   - ROUTE_STRATEGY=round_robin (轮询)
   - ROUTE_STRATEGY=random (随机)
   - ROUTE_STRATEGY=least_connections (最少连接)
   - ROUTE_STRATEGY=priority (优先级)

3. 配置复制监控:
   - REPLICATION_LAG_CHECK_INTERVAL=60 (检查间隔)
   - MAX_REPLICATION_LAG=5.0 (最大延迟)

4. 重启 Flask 应用:
   cd backend_python
   python main.py

5. 查看监控状态:
   curl http://localhost:5000/api/database/replication/status

6. 查看详细文档:
   docs/2026-02-28-P2-6-数据库读写分离实现报告.md
""")


def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║        P2-6: 数据库读写分离配置验证脚本                      ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 执行验证
    results = []
    
    results.append(("基础配置", verify_basic_config()))
    results.append(("主库配置", verify_master_config()))
    results.append(("从库配置", verify_slave_config()))
    results.append(("路由策略", verify_route_strategy()))
    results.append(("复制配置", verify_replication_config()))
    results.append(("写后读一致性", verify_write_read_consistency()))
    results.append(("连接路由测试", test_connection_routing()))
    results.append(("复制管理器", test_replication_manager()))
    results.append(("复制监控", test_monitoring()))
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
