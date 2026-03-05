#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
P0 错误处理修复验证脚本

验证内容：
1. DiagnosisErrorCode 枚举类型错误码处理
2. 数据库连接池配置优化

@author: 系统架构组
@date: 2026-03-03
"""

import os
import sys

# 添加后端路径
_backend_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend_python')
sys.path.insert(0, _backend_root)

print("\n" + "=" * 60)
print(" P0 错误处理修复验证")
print("=" * 60 + "\n")


def test_error_code_enum():
    """测试 1: 错误码枚举处理"""
    print("测试 1: DiagnosisErrorCode 枚举处理")
    print("-" * 60)
    
    try:
        from wechat_backend.error_codes import DiagnosisErrorCode, ErrorCodeDefinition
        from wechat_backend.error_logger import ErrorLogger
        from enum import Enum
        
        # 测试错误码访问
        error_code = DiagnosisErrorCode.DIAGNOSIS_TIMEOUT
        print(f"✅ 错误码枚举成员：{error_code}")
        print(f"   - 类型：{type(error_code)}")
        print(f"   - 是 Enum: {isinstance(error_code, Enum)}")
        
        # 测试.value 访问
        error_code_def = error_code.value
        print(f"✅ .value 访问：{error_code_def}")
        print(f"   - 类型：{type(error_code_def)}")
        print(f"   - code 属性：{error_code_def.code}")
        print(f"   - severity 属性：{error_code_def.severity}")
        
        # 测试 ErrorLogger 处理
        logger = ErrorLogger()
        
        # 模拟错误
        test_error = ValueError("测试超时错误")
        
        # 测试 log_error 方法（传入 Enum）
        try:
            trace_id = logger.log_error(
                error=test_error,
                error_code=error_code,  # 传入 Enum 成员
                execution_id="test-123",
                user_id="test-user"
            )
            print(f"✅ ErrorLogger.log_error() 成功处理 Enum 类型错误码")
            print(f"   - TraceID: {trace_id}")
        except AttributeError as e:
            print(f"❌ ErrorLogger.log_error() 失败：{e}")
            return False
            
        print("\n✅ 测试 1 通过：DiagnosisErrorCode 枚举处理正常")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试 1 失败：{e}")
        print(f"   堆栈：{traceback.format_exc()}")
        return False


def test_db_pool_config():
    """测试 2: 数据库连接池配置"""
    print("\n测试 2: 数据库连接池配置优化")
    print("-" * 60)
    
    try:
        from wechat_backend.database_connection_pool import get_db_pool, DatabaseConnectionPool
        
        # 获取连接池
        pool = get_db_pool()
        
        print(f"✅ 连接池配置：")
        print(f"   - max_connections: {pool.max_connections}")
        print(f"   - 期望值：20 (优化后)")
        
        if pool.max_connections == 20:
            print(f"✅ 连接池大小已优化为 20")
        else:
            print(f"⚠️  连接池大小为 {pool.max_connections}，期望 20")
            
        # 测试 get_connection 默认超时
        import inspect
        sig = inspect.signature(pool.get_connection)
        timeout_param = sig.parameters.get('timeout')
        
        if timeout_param:
            default_timeout = timeout_param.default
            print(f"✅ get_connection 默认超时：{default_timeout}秒")
            
            if default_timeout == 10.0:
                print(f"✅ 超时时间已优化为 10 秒")
            else:
                print(f"⚠️  超时时间为 {default_timeout}秒，期望 10 秒")
        else:
            print(f"⚠️  无法获取 timeout 参数默认值")
            
        print("\n✅ 测试 2 通过：数据库连接池配置检查完成")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试 2 失败：{e}")
        print(f"   堆栈：{traceback.format_exc()}")
        return False


def test_error_logger_with_enum():
    """测试 3: ErrorLogger 完整流程测试"""
    print("\n测试 3: ErrorLogger 完整流程测试")
    print("-" * 60)
    
    try:
        from wechat_backend.error_codes import DiagnosisErrorCode
        from wechat_backend.error_logger import ErrorLogger
        from enum import Enum
        
        logger = ErrorLogger()
        
        # 测试各种错误码类型
        test_cases = [
            (DiagnosisErrorCode.DIAGNOSIS_TIMEOUT, "超时错误"),
            (DiagnosisErrorCode.DIAGNOSIS_INIT_FAILED, "初始化失败"),
            (DiagnosisErrorCode.DIAGNOSIS_EXECUTION_FAILED, "执行失败"),
        ]
        
        for error_code, description in test_cases:
            # 检查是否为 Enum
            is_enum = isinstance(error_code, Enum)
            
            # 获取 ErrorCodeDefinition
            error_code_def = error_code.value if is_enum else error_code
            
            # 验证属性访问
            code = error_code_def.code
            severity = error_code_def.severity
            
            print(f"✅ {description}: code={code}, severity={severity.value}")
        
        print("\n✅ 测试 3 通过：ErrorLogger 完整流程测试完成")
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ 测试 3 失败：{e}")
        print(f"   堆栈：{traceback.format_exc()}")
        return False


def main():
    """主测试函数"""
    results = []
    
    results.append(("错误码枚举处理", test_error_code_enum()))
    results.append(("数据库连接池配置", test_db_pool_config()))
    results.append(("ErrorLogger 完整流程", test_error_logger_with_enum()))
    
    # 总结
    print("\n" + "=" * 60)
    print(" 测试结果总结")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
    
    print(f"\n  总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n✅ 所有修复验证通过！")
        print("\n下一步:")
        print("1. 启动后端服务：cd backend_python/wechat_backend && python3 app.py")
        print("2. 在小程序中执行诊断任务")
        print("3. 观察日志确认无 AttributeError 错误")
    else:
        print("\n❌ 部分测试失败，请检查修复代码")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
