"""
SQLCipher 评估脚本 (SQLCipher Evaluation Script)

功能:
1. 测试 SQLCipher 安装
2. 性能基准测试
3. 加密/解密测试
4. 兼容性测试
5. 生成评估报告

评估指标:
- 加密性能影响
- 查询性能影响
- 文件大小变化
- 兼容性
"""

import os
import sys
import time
import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sqlcipher_evaluation')


class SQLCipherEvaluator:
    """SQLCipher 评估器"""
    
    def __init__(self, test_db_path: str = 'data/test_encrypted.db'):
        """
        初始化评估器
        
        Args:
            test_db_path: 测试数据库路径
        """
        self.test_db_path = Path(test_db_path)
        self.results: Dict[str, Any] = {
            'evaluation_time': datetime.now().isoformat(),
            'tests': [],
            'summary': {}
        }
    
    def check_sqlcipher_installed(self) -> bool:
        """检查 SQLCipher 是否安装"""
        logger.info("Checking if SQLCipher is installed...")
        
        try:
            # 尝试导入 sqlcipher3
            import sqlcipher3
            logger.info("✅ SQLCipher (sqlcipher3) is installed")
            
            self.results['tests'].append({
                'name': 'SQLCipher Installation',
                'status': 'PASS',
                'details': 'sqlcipher3 module found'
            })
            
            return True
        except ImportError:
            logger.warning("⚠️  SQLCipher (sqlcipher3) is NOT installed")
            
            self.results['tests'].append({
                'name': 'SQLCipher Installation',
                'status': 'FAIL',
                'details': 'sqlcipher3 module not found'
            })
            
            return False
    
    def test_encryption(self) -> Dict[str, Any]:
        """测试加密功能"""
        logger.info("Testing encryption functionality...")
        
        try:
            import sqlcipher3
            
            # 创建加密数据库
            conn = sqlcipher3.connect(str(self.test_db_path))
            conn.execute("PRAGMA key = 'test_password_123'")
            
            # 创建测试表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS test_data (
                    id INTEGER PRIMARY KEY,
                    sensitive_data TEXT
                )
            """)
            
            # 插入测试数据
            conn.execute(
                "INSERT INTO test_data (sensitive_data) VALUES (?)",
                ('This is sensitive data',)
            )
            conn.commit()
            
            # 验证数据加密
            # 尝试用错误密码读取
            try:
                wrong_conn = sqlcipher3.connect(str(self.test_db_path))
                wrong_conn.execute("PRAGMA key = 'wrong_password'")
                wrong_conn.execute("SELECT * FROM test_data")
                logger.error("❌ Encryption test failed: Could read with wrong password")
                
                self.results['tests'].append({
                    'name': 'Encryption Test',
                    'status': 'FAIL',
                    'details': 'Could read with wrong password'
                })
                
                return {'status': 'FAIL'}
            except:
                logger.info("✅ Encryption test passed: Cannot read with wrong password")
            
            # 用正确密码读取
            conn.execute("SELECT * FROM test_data")
            conn.close()
            
            logger.info("✅ Encryption functionality test passed")
            
            self.results['tests'].append({
                'name': 'Encryption Test',
                'status': 'PASS',
                'details': 'Encryption/decryption working correctly'
            })
            
            return {'status': 'PASS'}
            
        except Exception as e:
            logger.error(f"❌ Encryption test failed: {e}")
            
            self.results['tests'].append({
                'name': 'Encryption Test',
                'status': 'FAIL',
                'details': str(e)
            })
            
            return {'status': 'FAIL'}
    
    def benchmark_performance(self) -> Dict[str, Any]:
        """性能基准测试"""
        logger.info("Running performance benchmarks...")
        
        try:
            import sqlcipher3
            
            # 测试参数
            num_records = 1000
            test_iterations = 3
            
            # 1. 普通 SQLite 基准测试
            logger.info("Running SQLite baseline benchmark...")
            sqlite_times = []
            
            for i in range(test_iterations):
                sqlite_db = Path('data/test_benchmark_sqlite.db')
                start = time.time()
                
                conn = sqlite3.connect(str(sqlite_db))
                conn.execute("CREATE TABLE IF NOT EXISTS benchmark (id INTEGER, data TEXT)")
                
                for j in range(num_records):
                    conn.execute(
                        "INSERT INTO benchmark VALUES (?, ?)",
                        (j, f"Test data {j}")
                    )
                
                conn.commit()
                conn.close()
                
                elapsed = time.time() - start
                sqlite_times.append(elapsed)
                
                # 清理
                sqlite_db.unlink()
            
            avg_sqlite_time = sum(sqlite_times) / len(sqlite_times)
            logger.info(f"SQLite average time: {avg_sqlite_time:.3f}s")
            
            # 2. SQLCipher 基准测试
            logger.info("Running SQLCipher benchmark...")
            sqlcipher_times = []
            
            for i in range(test_iterations):
                sqlcipher_db = Path('data/test_benchmark_sqlcipher.db')
                start = time.time()
                
                conn = sqlcipher3.connect(str(sqlcipher_db))
                conn.execute("PRAGMA key = 'benchmark_password_123'")
                conn.execute("CREATE TABLE IF NOT EXISTS benchmark (id INTEGER, data TEXT)")
                
                for j in range(num_records):
                    conn.execute(
                        "INSERT INTO benchmark VALUES (?, ?)",
                        (j, f"Test data {j}")
                    )
                
                conn.commit()
                conn.close()
                
                elapsed = time.time() - start
                sqlcipher_times.append(elapsed)
                
                # 清理
                sqlcipher_db.unlink()
            
            avg_sqlcipher_time = sum(sqlcipher_times) / len(sqlcipher_times)
            logger.info(f"SQLCipher average time: {avg_sqlcipher_time:.3f}s")
            
            # 计算性能影响
            overhead = ((avg_sqlcipher_time - avg_sqlite_time) / avg_sqlite_time) * 100
            
            logger.info(f"Performance overhead: {overhead:.1f}%")
            
            self.results['tests'].append({
                'name': 'Performance Benchmark',
                'status': 'PASS',
                'details': {
                    'sqlite_avg_time': f"{avg_sqlite_time:.3f}s",
                    'sqlcipher_avg_time': f"{avg_sqlcipher_time:.3f}s",
                    'overhead': f"{overhead:.1f}%"
                }
            })
            
            # 评估性能影响
            if overhead < 10:
                logger.info("✅ Performance impact: LOW (<10%)")
                status = 'PASS'
            elif overhead < 20:
                logger.info("⚠️  Performance impact: MEDIUM (10-20%)")
                status = 'PASS'
            else:
                logger.info("❌ Performance impact: HIGH (>20%)")
                status = 'WARNING'
            
            return {
                'status': status,
                'overhead': overhead,
                'sqlite_time': avg_sqlite_time,
                'sqlcipher_time': avg_sqlcipher_time
            }
            
        except Exception as e:
            logger.error(f"❌ Benchmark failed: {e}")
            
            self.results['tests'].append({
                'name': 'Performance Benchmark',
                'status': 'FAIL',
                'details': str(e)
            })
            
            return {'status': 'FAIL'}
    
    def test_compatibility(self) -> Dict[str, Any]:
        """兼容性测试"""
        logger.info("Running compatibility tests...")
        
        try:
            import sqlcipher3
            
            # 测试 1: 基本 SQL 操作
            logger.info("Testing basic SQL operations...")
            
            conn = sqlcipher3.connect(str(self.test_db_path))
            conn.execute("PRAGMA key = 'test_password_123'")
            
            # CREATE
            conn.execute("CREATE TABLE IF NOT EXISTS compat_test (id INTEGER, name TEXT)")
            
            # INSERT
            conn.execute("INSERT INTO compat_test VALUES (?, ?)", (1, 'Test'))
            
            # UPDATE
            conn.execute("UPDATE compat_test SET name = ? WHERE id = ?", ('Updated', 1))
            
            # DELETE
            conn.execute("DELETE FROM compat_test WHERE id = ?", (1,))
            
            # SELECT
            conn.execute("SELECT * FROM compat_test")
            
            # JOIN
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compat_test2 (id INTEGER, value TEXT)
            """)
            conn.execute("""
                SELECT * FROM compat_test 
                LEFT JOIN compat_test2 ON compat_test.id = compat_test2.id
            """)
            
            conn.close()
            
            logger.info("✅ Compatibility test passed")
            
            self.results['tests'].append({
                'name': 'Compatibility Test',
                'status': 'PASS',
                'details': 'All basic SQL operations working'
            })
            
            return {'status': 'PASS'}
            
        except Exception as e:
            logger.error(f"❌ Compatibility test failed: {e}")
            
            self.results['tests'].append({
                'name': 'Compatibility Test',
                'status': 'FAIL',
                'details': str(e)
            })
            
            return {'status': 'FAIL'}
    
    def run_full_evaluation(self) -> Dict[str, Any]:
        """运行完整评估"""
        logger.info("=" * 60)
        logger.info("Starting SQLCipher Full Evaluation")
        logger.info("=" * 60)
        
        # 1. 检查安装
        if not self.check_sqlcipher_installed():
            logger.warning("SQLCipher not installed, skipping further tests")
            self.results['summary'] = {
                'status': 'FAIL',
                'recommendation': 'Install SQLCipher first: pip install sqlcipher3'
            }
            return self.results
        
        # 2. 测试加密
        encryption_result = self.test_encryption()
        
        # 3. 性能基准测试
        performance_result = self.benchmark_performance()
        
        # 4. 兼容性测试
        compatibility_result = self.test_compatibility()
        
        # 生成总结
        all_passed = (
            encryption_result.get('status') == 'PASS' and
            performance_result.get('status') in ['PASS', 'WARNING'] and
            compatibility_result.get('status') == 'PASS'
        )
        
        self.results['summary'] = {
            'status': 'PASS' if all_passed else 'FAIL',
            'recommendation': self._generate_recommendation(performance_result),
            'next_steps': self._generate_next_steps()
        }
        
        # 保存评估报告
        self._save_report()
        
        logger.info("=" * 60)
        logger.info(f"Evaluation Complete: {self.results['summary']['status']}")
        logger.info("=" * 60)
        
        return self.results
    
    def _generate_recommendation(self, performance_result: Dict[str, Any]) -> str:
        """生成推荐建议"""
        overhead = performance_result.get('overhead', 0)
        
        if overhead < 10:
            return "RECOMMENDED: Low performance impact, safe to use"
        elif overhead < 20:
            return "ACCEPTABLE: Medium performance impact, consider use case"
        else:
            return "CAUTION: High performance impact, evaluate alternatives"
    
    def _generate_next_steps(self) -> List[str]:
        """生成下一步建议"""
        return [
            "Review performance benchmark results",
            "Test with production-like data volume",
            "Implement key management system",
            "Set up key rotation policy",
            "Create backup and recovery procedures"
        ]
    
    def _save_report(self):
        """保存评估报告"""
        report_path = Path('data/sqlcipher_evaluation_report.json')
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(report_path, 'w') as f:
            import json
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Evaluation report saved: {report_path}")


def main():
    """主函数"""
    evaluator = SQLCipherEvaluator()
    results = evaluator.run_full_evaluation()
    
    # 打印总结
    print("\n" + "=" * 60)
    print("📊 SQLCipher 评估总结")
    print("=" * 60)
    print(f"状态：{results['summary']['status']}")
    print(f"建议：{results['summary']['recommendation']}")
    print("\n下一步:")
    for i, step in enumerate(results['summary']['next_steps'], 1):
        print(f"  {i}. {step}")
    print("=" * 60)
    
    return 0 if results['summary']['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
