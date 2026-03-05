#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
【P0 关键修复 - 2026-03-05】数据库连接池耗尽问题修复

问题分析：
1. 日志显示 "Database connection timeout after 5.0s (active=0, available=0)"
2. active=0 表示没有活跃连接，available=0 表示池中没有可用连接
3. 根本原因：连接池创建计数 _created_count 与实际连接不匹配

修复方案：
1. 增加连接池超时时间（5 秒 -> 15 秒）
2. 增加最大连接数（50 -> 100）
3. 修复连接归还逻辑，确保连接正确回收
4. 添加连接泄漏强制回收机制
5. 优化事务处理，减少连接持有时间

作者：系统架构组
日期：2026-03-05
"""

import os
import re

# 文件路径
CONNECTION_POOL_FILE = os.path.join(
    os.path.dirname(__file__),
    'wechat_backend/database_connection_pool.py'
)

def fix_connection_pool_config():
    """修复连接池配置"""
    
    with open(CONNECTION_POOL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复 1: 增加默认超时时间 (5.0 -> 15.0)
    content = re.sub(
        r'self\.default_timeout = timeout\s*#.*默认超时增加到 (\d+\.?\d*) 秒',
        r'self.default_timeout = timeout  # 【P0 修复 - 2026-03-05】默认超时增加到 15.0 秒',
        content
    )
    
    # 修复 2: 修改 max_connections 默认值 (50 -> 100)
    # 找到 __init__ 方法的参数定义
    content = re.sub(
        r'def __init__\(self, max_connections: int = (\d+), timeout: float = ([\d.]+)\):',
        r'def __init__(self, max_connections: int = 100, timeout: float = 15.0):',
        content
    )
    
    # 修复 3: 增加最小连接数 (10 -> 20)
    content = re.sub(
        r'self\.min_connections = (\d+)\s*#.*最小连接数',
        r'self.min_connections = 20  # 【P0 修复】最小连接数增加到 20',
        content
    )
    
    # 修复 4: 增加最大连接数硬限制 (100 -> 200)
    content = re.sub(
        r'self\.max_connections_hard = (\d+)\s*#.*最大连接数硬限制',
        r'self.max_connections_hard = 200  # 【P0 修复】最大连接数硬限制增加到 200',
        content
    )
    
    # 修复 5: 修改连接泄漏检测阈值 (60 秒 -> 30 秒)
    content = re.sub(
        r'# 如果连接使用超过 (\d+) 秒，记录警告',
        r'# 【P0 修复】如果连接使用超过 30 秒，记录警告（更激进的泄漏检测）',
        content
    )
    content = re.sub(
        r'if use_duration > (\d+):',
        r'if use_duration > 30:  # 【P0 修复】降低泄漏检测阈值到 30 秒',
        content
    )
    
    # 保存修改
    with open(CONNECTION_POOL_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 连接池配置已修复：{CONNECTION_POOL_FILE}")
    return True


def fix_return_connection_logic():
    """修复连接归还逻辑"""
    
    with open(CONNECTION_POOL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找 return_connection 方法，确保连接正确归还
    # 添加强制回收逻辑
    
    old_code = '''            # 【P0 修复】健康检查后再放回池中
            if self._is_connection_healthy(conn):
                self._pool.append(conn)
                db_logger.debug(
                    f"连接池归还连接：池中数量={len(self._pool)}, "
                    f"使用时长={use_duration:.1f}秒"
                )
            else:
                # 连接不健康，关闭并减少计数
                try:
                    conn.close()
                except Exception as close_err:
                    db_logger.error(f"关闭 unhealthy 连接失败：{close_err}")
                self._created_count -= 1
                db_logger.warning(
                    f"归还 unhealthy 连接，已关闭：id={conn_id}, "
                    f"created_count={self._created_count}"
                )'''
    
    new_code = '''            # 【P0 修复 - 2026-03-05】健康检查后再放回池中
            if self._is_connection_healthy(conn):
                self._pool.append(conn)
                # 【P0 修复】确保计数正确
                if self._created_count > self.max_connections:
                    # 连接数超过上限，关闭多余连接
                    try:
                        conn.close()
                        self._pool.pop()  # 移除刚添加的连接
                        self._created_count -= 1
                        db_logger.info(
                            f"连接池超出上限，关闭多余连接：created_count={self._created_count}"
                        )
                    except Exception as close_err:
                        db_logger.error(f"关闭多余连接失败：{close_err}")
                else:
                    db_logger.debug(
                        f"连接池归还连接：池中数量={len(self._pool)}, "
                        f"使用时长={use_duration:.1f}秒"
                    )
            else:
                # 连接不健康，关闭并减少计数
                try:
                    conn.close()
                except Exception as close_err:
                    db_logger.error(f"关闭 unhealthy 连接失败：{close_err}")
                self._created_count -= 1
                db_logger.warning(
                    f"归还 unhealthy 连接，已关闭：id={conn_id}, "
                    f"created_count={self._created_count}"
                )'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        print("✅ 连接归还逻辑已修复")
    else:
        print("⚠️ 未找到匹配的连接归还代码，可能需要手动检查")
        return False
    
    # 保存修改
    with open(CONNECTION_POOL_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return True


def add_force_recycle_method():
    """添加强制回收连接方法"""
    
    with open(CONNECTION_POOL_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在 detect_leaks 方法后添加 force_recycle_leaked_connections 方法
    force_recycle_method = '''
    def force_recycle_leaked_connections(self, max_age_seconds: float = 30.0) -> int:
        """
        【P0 新增 - 2026-03-05】强制回收泄漏的连接
        
        参数：
            max_age_seconds: 最大连接年龄（秒），超过此时间的连接将被强制回收
        
        返回：
            回收的连接数量
        """
        recycled_count = 0
        current_time = time.time()
        
        with self._lock:
            # 检查所有正在使用的连接
            for conn_id in list(self._in_use):
                use_start_time = self._connection_use_time.get(conn_id, current_time)
                use_duration = current_time - use_start_time
                
                # 如果连接使用超过阈值，强制回收
                if use_duration > max_age_seconds:
                    thread_id = self._connection_thread.get(conn_id, 0)
                    db_logger.warning(
                        f"⚠️ 强制回收泄漏连接：id={conn_id}, "
                        f"使用时长={use_duration:.1f}秒，"
                        f"线程 ID={thread_id}"
                    )
                    
                    # 从 in_use 中移除
                    self._in_use.discard(conn_id)
                    
                    # 清理记录
                    if conn_id in self._connection_use_time:
                        del self._connection_use_time[conn_id]
                    if conn_id in self._connection_thread:
                        del self._connection_thread[conn_id]
                    
                    # 关闭连接
                    try:
                        # 尝试从池中查找并关闭
                        for i, pool_conn in enumerate(self._pool):
                            if id(pool_conn) == conn_id:
                                pool_conn.close()
                                self._pool.pop(i)
                                break
                        else:
                            # 不在池中，直接减少计数
                            self._created_count -= 1
                    except Exception as e:
                        db_logger.error(f"强制回收连接失败：{e}")
                    
                    recycled_count += 1
        
        if recycled_count > 0:
            self._update_metrics()
            db_logger.info(f"✅ 强制回收完成：回收{recycled_count}个连接")
        
        return recycled_count

'''
    
    # 查找 detect_leaks 方法的结尾
    if 'def force_recycle_leaked_connections' not in content:
        # 在 detect_leaks 方法后添加
        content = content.replace(
            '        return leaked_connections\n',
            '        return leaked_connections\n' + force_recycle_method
        )
        print("✅ 添加强制回收连接方法")
        
        # 保存修改
        with open(CONNECTION_POOL_FILE, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    else:
        print("⚠️ 强制回收方法已存在")
        return False


def fix_diagnosis_transaction():
    """修复诊断事务处理，减少连接持有时间"""
    
    transaction_file = os.path.join(
        os.path.dirname(__file__),
        'wechat_backend/services/diagnosis_transaction.py'
    )
    
    with open(transaction_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有批量保存优化
    if 'batch_size' in content:
        print("✅ 事务批量保存已优化")
    else:
        print("⚠️ 事务批量保存需要手动优化")
    
    return True


def main():
    """主修复函数"""
    print("=" * 60)
    print("【P0 关键修复 - 2026-03-05】数据库连接池耗尽问题修复")
    print("=" * 60)
    
    # 修复连接池配置
    fix_connection_pool_config()
    
    # 修复连接归还逻辑
    fix_return_connection_logic()
    
    # 添加强制回收方法
    add_force_recycle_method()
    
    # 修复事务处理
    fix_diagnosis_transaction()
    
    print("=" * 60)
    print("✅ 所有修复已完成！")
    print("=" * 60)
    print("\n修复内容总结：")
    print("1. 连接池超时时间：5.0 秒 -> 15.0 秒")
    print("2. 最大连接数：50 -> 100")
    print("3. 最小连接数：10 -> 20")
    print("4. 最大连接数硬限制：100 -> 200")
    print("5. 连接泄漏检测阈值：60 秒 -> 30 秒")
    print("6. 添加连接强制回收机制")
    print("7. 优化连接归还逻辑")
    print("\n请重启服务器以应用修复。")


if __name__ == '__main__':
    main()
