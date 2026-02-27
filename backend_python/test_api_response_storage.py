#!/usr/bin/env python3
"""
测试脚本：验证 API 响应存储完整性

验证 Migration 004 后，系统是否正确存储完整的 API 响应数据。

符合重构规范：
- 规则 4.1.1: 测试覆盖率要求
- 规则 4.2.1: 测试文件命名
- 规则 4.5.1: 使用测试数据

使用方法:
    python3 test_api_response_storage.py

作者：系统架构组
日期：2026-02-27
版本：v2.0.0
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from wechat_backend.diagnosis_report_repository import DiagnosisReportRepository
from wechat_backend.diagnosis_report_storage import DiagnosisResultRepository
from wechat_backend.v2.models.diagnosis_result import DiagnosisResult

# 数据库路径
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'database.db'
)


class TestAPIResponseStorage:
    """API 响应存储完整性测试"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.test_execution_id = f"test_api_storage_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_results = []
        
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def setup(self):
        """测试准备"""
        print("=" * 60)
        print("测试准备")
        print("=" * 60)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 检查表结构
        cursor.execute("PRAGMA table_info(diagnosis_results)")
        columns = [col['name'] for col in cursor.fetchall()]
        
        required_columns = [
            'raw_response', 'response_metadata',
            'tokens_used', 'prompt_tokens', 'completion_tokens', 'cached_tokens',
            'finish_reason', 'request_id', 'model_version', 'reasoning_content',
            'api_endpoint', 'service_tier', 'retry_count', 'is_fallback',
            'updated_at'
        ]
        
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            print(f"❌ 缺少字段：{missing_columns}")
            print("⚠️  请先执行 Migration 004")
            conn.close()
            return False
        
        print("✅ 所有必需字段已存在")
        conn.close()
        return True
    
    def test_sample_data_insert(self):
        """测试 1: 插入示例数据"""
        print()
        print("=" * 60)
        print("测试 1: 插入示例数据")
        print("=" * 60)
        
        # 创建测试数据
        sample_result = {
            'brand': '测试品牌 A',
            'question': '测试问题 1',
            'model': 'test-model-v1',
            'response': {
                'content': '这是测试回答内容',
                'latency': 1.5,
                'metadata': {
                    'id': 'test-request-123',
                    'model': 'test-model-v1',
                    'usage': {
                        'prompt_tokens': 100,
                        'completion_tokens': 200,
                        'total_tokens': 300,
                        'prompt_tokens_details': {'cached_tokens': 50}
                    },
                    'choices': [{
                        'message': {
                            'content': '这是测试回答内容',
                            'reasoning_content': '这是推理过程'
                        },
                        'finish_reason': 'stop'
                    }],
                    'api_endpoint': 'https://api.test.com/v1/chat',
                    'service_tier': 'default'
                }
            },
            'geo_data': {
                'brand_mentioned': True,
                'rank': 1,
                'sentiment': 0.9
            },
            'quality_score': 0.95,
            'quality_level': 'high',
            'quality_details': {'completeness': 0.9, 'accuracy': 0.95},
            'status': 'success',
            'error': None,
            'retry_count': 0,
            'is_fallback': False
        }
        
        try:
            # 使用 Repository 保存
            storage = DiagnosisResultRepository()
            
            # 先创建测试报告
            report_id = self._create_test_report()
            if not report_id:
                print("❌ 创建测试报告失败")
                return False
            
            # 保存诊断结果
            result_id = storage.add_result(report_id, self.test_execution_id, sample_result)
            
            if result_id:
                print(f"✅ 数据插入成功，result_id: {result_id}")
                self.test_results.append(('insert', result_id))
                return True
            else:
                print("❌ 数据插入失败")
                return False
                
        except Exception as e:
            print(f"❌ 插入异常：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_data_retrieval(self):
        """测试 2: 检索数据验证"""
        print()
        print("=" * 60)
        print("测试 2: 检索数据验证")
        print("=" * 60)
        
        if not self.test_results:
            print("⚠️  无测试数据，跳过")
            return False
        
        _, result_id = self.test_results[0]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM diagnosis_results
            WHERE id = ?
        ''', (result_id,))
        
        row = cursor.fetchone()
        
        if not row:
            print("❌ 未找到测试数据")
            conn.close()
            return False
        
        # 验证字段值
        checks = [
            ('tokens_used', 300),
            ('prompt_tokens', 100),
            ('completion_tokens', 200),
            ('cached_tokens', 50),
            ('finish_reason', 'stop'),
            ('request_id', 'test-request-123'),
            ('model_version', 'test-model-v1'),
            ('reasoning_content', '这是推理过程'),
            ('api_endpoint', 'https://api.test.com/v1/chat'),
            ('service_tier', 'default'),
            ('retry_count', 0),
            ('is_fallback', 0),
        ]
        
        all_passed = True
        for field, expected in checks:
            actual = row[field]
            if actual == expected:
                print(f"✅ {field}: {actual}")
            else:
                print(f"❌ {field}: 期望 {expected}, 实际 {actual}")
                all_passed = False
        
        conn.close()
        return all_passed
    
    def test_model_conversion(self):
        """测试 3: 数据模型转换"""
        print()
        print("=" * 60)
        print("测试 3: 数据模型转换")
        print("=" * 60)
        
        if not self.test_results:
            print("⚠️  无测试数据，跳过")
            return False
        
        _, result_id = self.test_results[0]
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM diagnosis_results
            WHERE id = ?
        ''', (result_id,))
        
        row = dict(cursor.fetchone())
        conn.close()
        
        try:
            # 从数据库行创建模型
            model = DiagnosisResult.from_db_row(row)
            
            # 验证模型属性
            checks = [
                ('tokens_used', 300),
                ('prompt_tokens', 100),
                ('completion_tokens', 200),
                ('cached_tokens', 50),
                ('finish_reason', 'stop'),
                ('request_id', 'test-request-123'),
                ('model_version', 'test-model-v1'),
                ('reasoning_content', '这是推理过程'),
            ]
            
            all_passed = True
            for field, expected in checks:
                actual = getattr(model, field, None)
                if actual == expected:
                    print(f"✅ model.{field}: {actual}")
                else:
                    print(f"❌ model.{field}: 期望 {expected}, 实际 {actual}")
                    all_passed = False
            
            # 测试 to_dict
            model_dict = model.to_dict()
            if 'tokens_used' in model_dict:
                print(f"✅ to_dict() 包含 tokens_used")
            else:
                print(f"❌ to_dict() 缺少 tokens_used")
                all_passed = False
            
            return all_passed
            
        except Exception as e:
            print(f"❌ 模型转换异常：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_repository_query(self):
        """测试 4: Repository 查询"""
        print()
        print("=" * 60)
        print("测试 4: Repository 查询")
        print("=" * 60)
        
        try:
            storage = DiagnosisResultRepository()
            results = storage.get_results_by_execution_id(self.test_execution_id)
            
            if results:
                print(f"✅ 查询到 {len(results)} 条记录")
                
                result = results[0]
                if result.get('tokens_used') == 300:
                    print(f"✅ tokens_used: {result['tokens_used']}")
                else:
                    print(f"❌ tokens_used: {result.get('tokens_used')}")
                    return False
                
                return True
            else:
                print("⚠️  未查询到数据")
                return False
                
        except Exception as e:
            print(f"❌ 查询异常：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup(self):
        """清理测试数据"""
        print()
        print("=" * 60)
        print("清理测试数据")
        print("=" * 60)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 删除测试报告
        cursor.execute('''
            DELETE FROM diagnosis_reports
            WHERE execution_id = ?
        ''', (self.test_execution_id,))
        
        # 删除测试结果
        cursor.execute('''
            DELETE FROM diagnosis_results
            WHERE execution_id = ?
        ''', (self.test_execution_id,))
        
        conn.commit()
        conn.close()
        
        print(f"✅ 已清理测试数据：{self.test_execution_id}")
    
    def _create_test_report(self):
        """创建测试报告"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        try:
            cursor.execute('''
                INSERT INTO diagnosis_reports (
                    execution_id, user_id, brand_name, competitor_brands,
                    selected_models, custom_questions,
                    status, progress, stage, is_completed,
                    created_at, updated_at, data_schema_version, server_version, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.test_execution_id,
                'test_user',
                '测试品牌',
                '[]',
                '[{"name": "test-model", "checked": true}]',
                '["测试问题"]',
                'processing',
                0,
                'init',
                0,
                now,
                now,
                '2.0',
                '2.0.0',
                'test_checksum'
            ))
            
            report_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return report_id
            
        except Exception as e:
            print(f"❌ 创建测试报告失败：{e}")
            conn.close()
            return None
    
    def run_all_tests(self):
        """运行所有测试"""
        print()
        print("=" * 60)
        print("API 响应存储完整性测试")
        print("=" * 60)
        print(f"测试执行 ID: {self.test_execution_id}")
        print()
        
        # 准备
        if not self.setup():
            return False
        
        # 运行测试
        results = []
        
        results.append(('插入示例数据', self.test_sample_data_insert()))
        results.append(('检索数据验证', self.test_data_retrieval()))
        results.append(('模型转换', self.test_model_conversion()))
        results.append(('Repository 查询', self.test_repository_query()))
        
        # 清理
        self.cleanup()
        
        # 汇总结果
        print()
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{status}: {name}")
        
        print()
        print(f"总计：{passed}/{total} 通过")
        
        if passed == total:
            print()
            print("=" * 60)
            print("✅ 所有测试通过！API 响应存储功能正常。")
            print("=" * 60)
            return True
        else:
            print()
            print("=" * 60)
            print(f"⚠️  有 {total - passed} 项测试未通过，请检查。")
            print("=" * 60)
            return False


def main():
    """主函数"""
    test = TestAPIResponseStorage()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
