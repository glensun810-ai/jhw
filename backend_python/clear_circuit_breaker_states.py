#!/usr/bin/env python3
"""
熔断状态清理脚本
用于清理 NxM 执行引擎的熔断器状态

使用方法：
python3 clear_circuit_breaker_states.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clear_circuit_breaker_states():
    """清理所有熔断器状态"""
    try:
        from wechat_backend.nxm_circuit_breaker import get_circuit_breaker, CircuitBreaker
        
        print("="*60)
        print("熔断状态清理工具")
        print("="*60)
        
        # 获取所有熔断器实例
        breakers = CircuitBreaker._instances
        
        if not breakers:
            print("\n✅ 没有活跃的熔断器实例")
            return True
        
        print(f"\n找到 {len(breakers)} 个熔断器实例:")
        
        cleared_count = 0
        for key, breaker in breakers.items():
            state = breaker.state
            failure_count = breaker.failure_count
            
            print(f"  - {key}: 状态={state}, 失败次数={failure_count}")
            
            # 重置熔断器
            breaker.reset()
            cleared_count += 1
            print(f"    ✅ 已重置")
        
        print(f"\n✅ 已重置 {cleared_count} 个熔断器")
        print("\n建议：重启后端服务以确保更改生效")
        
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败：{e}")
        print("   请确保后端服务已正确安装依赖")
        return False
    except Exception as e:
        print(f"❌ 清理失败：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = clear_circuit_breaker_states()
    sys.exit(0 if success else 1)
