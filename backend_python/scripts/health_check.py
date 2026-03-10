#!/usr/bin/env python3
"""
后端健康检查脚本
检查所有必需组件是否正常

用法：
    python3 backend_python/scripts/health_check.py
"""

import sys
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
backend_path = project_root / 'backend_python'
sys.path.insert(0, str(backend_path))

def print_header(title):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(name, success, message=""):
    """打印检查结果"""
    status = "✅" if success else "❌"
    print(f"{status} {name}: {message if message else ('通过' if success else '失败')}")
    return success

def check_environment():
    """检查环境配置"""
    print_header("环境配置检查")
    results = []
    
    # 检查 Python 版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    results.append(print_result("Python 版本", sys.version_info >= (3, 8), python_version))
    
    # 检查 .env 文件
    env_file = backend_path / '.env'
    results.append(print_result(".env 文件", env_file.exists(), str(env_file)))
    
    # 检查必需的环境变量
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            env_content = f.read()
        
        required_vars = ['ARK_API_KEY', 'SECRET_KEY', 'DEBUG']
        for var in required_vars:
            exists = var in env_content
            results.append(print_result(f"环境变量 {var}", exists))
    
    return all(results)

def check_database():
    """检查数据库"""
    print_header("数据库检查")
    results = []
    
    try:
        from wechat_backend.database_connection_pool import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        results.append(print_result("数据库连接", True, f"表数量：{len(tables)}"))
        
        # 检查必需表
        required_tables = [
            'diagnosis_reports', 
            'diagnosis_results', 
            'diagnosis_analysis',
            'users',
            'task_status'
        ]
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            results.append(print_result("必需表", False, f"缺少：{missing_tables}"))
        else:
            results.append(print_result("必需表", True, "全部存在"))
        
        # 检查 diagnosis_reports schema
        if 'diagnosis_reports' in tables:
            cursor.execute("PRAGMA table_info(diagnosis_reports)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            required_columns = ['execution_id', 'user_id', 'brand_name', 'status', 'progress', 'stage']
            missing_cols = [c for c in required_columns if c not in columns]
            
            if missing_cols:
                results.append(print_result("diagnosis_reports schema", False, f"缺少列：{missing_cols}"))
            else:
                results.append(print_result("diagnosis_reports schema", True))
        
        # 检查 diagnosis_results schema
        if 'diagnosis_results' in tables:
            cursor.execute("PRAGMA table_info(diagnosis_results)")
            columns = {row[1]: row[2] for row in cursor.fetchall()}
            required_columns = ['report_id', 'execution_id', 'brand', 'model', 'response_content', 'sentiment', 'geo_data']
            missing_cols = [c for c in required_columns if c not in columns]
            
            if missing_cols:
                results.append(print_result("diagnosis_results schema", False, f"缺少列：{missing_cols}"))
            else:
                results.append(print_result("diagnosis_results schema", True))
        
        # 检查最近诊断记录
        cursor.execute("""
            SELECT COUNT(*), MAX(created_at) 
            FROM diagnosis_reports 
            WHERE created_at > datetime('now', '-24 hours')
        """)
        result = cursor.fetchone()
        recent_count = result[0] if result else 0
        last_diagnosis = result[1] if result and result[1] else '无记录'
        results.append(print_result("24 小时内诊断", True, f"{recent_count} 次，最后：{last_diagnosis}"))
        
        conn.close()
        
    except Exception as e:
        results.append(print_result("数据库检查", False, str(e)))
    
    return all(results)

def check_ai_platforms():
    """检查 AI 平台配置"""
    print_header("AI 平台配置检查")
    results = []
    
    try:
        from wechat_backend.ai_adapters.factory import AIAdapterFactory
        from wechat_backend.ai_adapters.base_adapter import AIPlatformType
        
        # 获取所有平台
        all_platforms = [pt.value for pt in AIPlatformType]
        available_platforms = [
            p for p in all_platforms 
            if AIAdapterFactory.is_platform_available(p)
        ]
        
        results.append(print_result(
            "可用 AI 平台", 
            len(available_platforms) > 0,
            f"{len(available_platforms)}/{len(all_platforms)}: {available_platforms}"
        ))
        
        # 检查豆包配置
        try:
            from wechat_backend.config_manager import config_manager
            doubao_key = config_manager.get_api_key('doubao')
            results.append(print_result(
                "豆包 API Key",
                doubao_key is not None and len(doubao_key) > 0,
                "已配置" if doubao_key else "未配置"
            ))
        except Exception as e:
            results.append(print_result("豆包 API Key", False, str(e)))
        
    except Exception as e:
        results.append(print_result("AI 平台检查", False, str(e)))
    
    return all(results)

def check_execution_store():
    """检查执行状态存储"""
    print_header("执行状态存储检查")
    results = []
    
    try:
        from wechat_backend.views.diagnosis_views import execution_store
        
        active_count = len(execution_store)
        results.append(print_result("execution_store", True, f"当前任务数：{active_count}"))
        
        # 检查是否有卡住的任务（超过 1 小时未完成）
        from datetime import datetime, timedelta
        stuck_tasks = []
        for eid, state in execution_store.items():
            if not state.get('is_completed', False):
                start_time_str = state.get('start_time')
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        if datetime.now() - start_time > timedelta(hours=1):
                            stuck_tasks.append(eid)
                    except:
                        pass
        
        if stuck_tasks:
            results.append(print_result("卡住的任务", False, f"{len(stuck_tasks)} 个：{stuck_tasks[:5]}"))
        else:
            results.append(print_result("卡住的任务", True, "无"))
        
    except Exception as e:
        results.append(print_result("执行存储检查", False, str(e)))
    
    return all(results)

def check_backend_routes():
    """检查后端路由"""
    print_header("后端路由检查")
    results = []
    
    try:
        # 尝试导入 Flask 应用
        import sys
        sys.path.insert(0, str(backend_path))
        
        from wechat_backend import create_app
        app = create_app()
        
        # 获取所有路由
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        
        # 检查必需路由
        required_routes = [
            '/api/perform-brand-test',
            '/api/test/status/<execution_id>',
            '/api/reports'
        ]
        
        missing_routes = [r for r in required_routes if not any(r.split('<')[0].strip('/') in route for route in routes)]
        
        if missing_routes:
            results.append(print_result("必需路由", False, f"缺少：{missing_routes}"))
        else:
            results.append(print_result("必需路由", True, f"共{len(routes)}个路由"))
        
    except Exception as e:
        results.append(print_result("路由检查", False, str(e)))
    
    return all(results)

def check_recent_diagnoses():
    """检查最近诊断任务"""
    print_header("最近诊断任务分析")
    results = []
    
    try:
        from wechat_backend.database_connection_pool import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近 20 次诊断
        cursor.execute("""
            SELECT execution_id, status, progress, stage, error_message, created_at
            FROM diagnosis_reports
            ORDER BY created_at DESC
            LIMIT 20
        """)
        
        diagnoses = cursor.fetchall()
        
        if not diagnoses:
            results.append(print_result("诊断记录", False, "无记录"))
        else:
            results.append(print_result("诊断记录", True, f"最近 20 次"))
            
            # 统计成功率
            success_count = sum(1 for d in diagnoses if d[1] in ['completed', 'partial_success'])
            failed_count = sum(1 for d in diagnoses if d[1] in ['failed', 'timeout'])
            
            results.append(print_result(
                "成功率",
                success_count > 0,
                f"成功:{success_count}, 失败:{failed_count}, 成功率:{success_count/len(diagnoses)*100:.1f}%"
            ))
            
            # 分析失败原因
            if failed_count > 0:
                error_messages = [d[4] for d in diagnoses if d[4]]
                if error_messages:
                    print("\n⚠️  常见错误:")
                    for i, err in enumerate(set(error_messages)[:5], 1):
                        print(f"   {i}. {err[:100]}")
        
        conn.close()
        
    except Exception as e:
        results.append(print_result("诊断分析", False, str(e)))
    
    return all(results)

def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + " " * 10 + "品牌诊断系统 - 后端健康检查" + " " * 17 + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print(f"\n检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    
    # 执行所有检查
    all_results.append(("环境配置", check_environment()))
    all_results.append(("数据库", check_database()))
    all_results.append(("AI 平台", check_ai_platforms()))
    all_results.append(("执行存储", check_execution_store()))
    all_results.append(("后端路由", check_backend_routes()))
    all_results.append(("诊断分析", check_recent_diagnoses()))
    
    # 总结
    print_header("检查总结")
    passed = sum(1 for _, r in all_results if r)
    total = len(all_results)
    
    for name, result in all_results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print("\n" + "-" * 60)
    print(f"总计：{passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("-" * 60)
    
    if passed == total:
        print("\n✅ 所有检查通过！系统健康状态良好。")
        return 0
    else:
        failed_items = [name for name, result in all_results if not result]
        print(f"\n❌ 以下检查失败：{', '.join(failed_items)}")
        print("\n建议：请查看上方详细错误信息并修复。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
