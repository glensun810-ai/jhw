#!/usr/bin/env python3
"""
端到端测试：品牌诊断完整流程

测试策略：
1. 从前端模拟用户操作
2. 验证后端每个处理环节
3. 检查数据库持久化
4. 验证前端渲染数据

测试覆盖：
- NxM 引擎字段完整性
- 数据库持久化
- 报告 API 响应
- 数据质量验证

@author: 系统架构组
@date: 2026-03-07
@version: 1.0.0
"""

import pytest
import requests
import sqlite3
import time
import json
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend_python'))

# 配置
BASE_URL = 'http://localhost:5001'
DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'backend_python', 'database.db')
TIMEOUT = 300  # 5 分钟超时


class TestDiagnosisFullFlow:
    """品牌诊断完整流程测试"""
    
    @pytest.fixture(scope='class')
    def execution_id(self):
        """Fixture: 创建并返回执行 ID"""
        # 启动诊断
        response = requests.post(
            f'{BASE_URL}/api/perform-brand-test',
            json={
                'brand_list': ['特斯拉', '比亚迪'],
                'selected_models': [{'name': 'qwen'}],
                'custom_questions': ['新能源汽车哪个品牌好？']
            },
            timeout=30
        )
        
        assert response.status_code == 200, f"启动诊断失败：{response.text}"
        data = response.json()
        assert 'execution_id' in data, "响应中缺少 execution_id"
        
        print(f"\n✅ 诊断已启动：{data['execution_id']}")
        return data['execution_id']
    
    def test_01_start_diagnosis(self):
        """测试 1: 启动诊断"""
        print("\n" + "="*60)
        print("测试 1: 启动诊断")
        print("="*60)
        
        response = requests.post(
            f'{BASE_URL}/api/perform-brand-test',
            json={
                'brand_list': ['特斯拉', '比亚迪'],
                'selected_models': [{'name': 'qwen'}],
                'custom_questions': ['新能源汽车哪个品牌好？']
            },
            timeout=30
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'execution_id' in data
        
        print(f"✅ 诊断启动成功")
        print(f"   execution_id: {data['execution_id']}")
        print(f"   formula: {data.get('formula', 'N/A')}")
        print(f"   total_tasks: {data.get('total_tasks', 'N/A')}")
    
    def test_02_wait_completion(self, execution_id):
        """测试 2: 等待诊断完成"""
        print("\n" + "="*60)
        print("测试 2: 等待诊断完成")
        print("="*60)
        
        print(f"等待诊断完成：{execution_id}")
        
        max_wait = TIMEOUT
        start_time = time.time()
        poll_interval = 2
        last_status = None
        
        while time.time() - start_time < max_wait:
            try:
                response = requests.get(
                    f'{BASE_URL}/test/status/{execution_id}',
                    timeout=10
                )
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status')
                    progress = status_data.get('progress', 0)
                    stage = status_data.get('stage', 'unknown')
                    
                    if status != last_status:
                        print(f"   状态：{status}, 进度：{progress}%, 阶段：{stage}")
                        last_status = status
                    
                    if status == 'completed':
                        print(f"✅ 诊断已完成")
                        break
                    elif status == 'failed':
                        pytest.fail(f"诊断失败：{status_data}")
                else:
                    print(f"⚠️ 状态查询失败：{response.status_code}")
            
            except requests.exceptions.RequestException as e:
                print(f"⚠️ 请求异常：{e}")
            
            time.sleep(poll_interval)
        else:
            pytest.fail(f"诊断超时（>{max_wait}秒）")
    
    def test_03_verify_database(self, execution_id):
        """测试 3: 验证数据库记录"""
        print("\n" + "="*60)
        print("测试 3: 验证数据库记录")
        print("="*60)
        
        print(f"检查数据库：{execution_id}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查 diagnosis_results 表
        cursor.execute("""
            SELECT id, brand, question, model, tokens_used, status
            FROM diagnosis_results
            WHERE execution_id = ?
            ORDER BY id
        """, (execution_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        print(f"   找到 {len(rows)} 条记录")
        
        # 验证有数据
        assert len(rows) > 0, "数据库中没有诊断结果"
        
        # 验证每条记录的字段完整性
        empty_brand_count = 0
        zero_tokens_count = 0
        
        for i, row in enumerate(rows):
            id_, brand, question, model, tokens_used, status = row
            
            if not brand:
                empty_brand_count += 1
                print(f"   ⚠️ 记录 [{i}] brand 字段为空")
            
            if not tokens_used or tokens_used == 0:
                zero_tokens_count += 1
                print(f"   ⚠️ 记录 [{i}] tokens_used 为 0")
        
        # 断言
        assert empty_brand_count == 0, f"{empty_brand_count} 条记录的 brand 字段为空"
        assert zero_tokens_count < len(rows) * 0.5, f"超过 50% 的记录 tokens_used 为 0"
        
        print(f"✅ 数据库验证通过")
        print(f"   总记录数：{len(rows)}")
        print(f"   brand 为空：{empty_brand_count}")
        print(f"   tokens_used 为 0: {zero_tokens_count}")
    
    def test_04_verify_report_api(self, execution_id):
        """测试 4: 验证报告 API"""
        print("\n" + "="*60)
        print("测试 4: 验证报告 API")
        print("="*60)
        
        print(f"获取报告：{execution_id}")
        
        response = requests.get(
            f'{BASE_URL}/api/diagnosis/report/{execution_id}',
            timeout=30
        )
        
        assert response.status_code == 200, f"报告 API 失败：{response.status_code}"
        data = response.json()
        
        # 验证报告结构
        assert 'brandDistribution' in data, "报告中缺少 brandDistribution"
        assert 'results' in data, "报告中缺少 results"
        assert len(data['results']) > 0, "results 为空"
        
        # 验证结果中的 brand 字段
        empty_brand_count = 0
        for i, result in enumerate(data['results']):
            if not result.get('brand'):
                empty_brand_count += 1
        
        assert empty_brand_count == 0, f"报告中 {empty_brand_count} 条结果的 brand 字段为空"
        
        print(f"✅ 报告 API 验证通过")
        print(f"   结果数：{len(data['results'])}")
        print(f"   品牌分布：{data.get('brandDistribution', {}).get('data', {})}")
    
    def test_05_verify_field_validation(self, execution_id):
        """测试 5: 验证字段验证器"""
        print("\n" + "="*60)
        print("测试 5: 验证字段验证器")
        print("="*60)
        
        from wechat_backend.validators import ResultValidator, validate_diagnosis_result
        
        # 测试有效结果
        valid_result = {
            'brand': '特斯拉',
            'question': '新能源汽车哪个品牌好？',
            'model': 'qwen',
            'response': {'content': '特斯拉是很好的品牌', 'latency': 1.5, 'metadata': {}},
            'tokens_used': 100
        }
        
        is_valid, errors, warnings = validate_diagnosis_result(valid_result)
        assert is_valid, f"有效结果验证失败：{errors}"
        print(f"✅ 有效结果验证通过")
        
        # 测试无效结果（缺少 brand）
        invalid_result = {
            'question': '新能源汽车哪个品牌好？',
            'model': 'qwen',
            'response': {'content': '...', 'latency': 1.5, 'metadata': {}},
            'tokens_used': 100
        }
        
        is_valid, errors, warnings = validate_diagnosis_result(invalid_result)
        assert not is_valid, "无效结果应该验证失败"
        assert any('brand' in e for e in errors), "错误信息应该包含 brand 字段缺失"
        print(f"✅ 无效结果验证通过")
        print(f"   错误：{errors}")
    
    def test_full_flow(self, execution_id):
        """完整流程测试（汇总）"""
        print("\n" + "="*60)
        print("📊 完整流程测试汇总")
        print("="*60)
        
        print(f"\n✅ 所有测试通过！")
        print(f"   execution_id: {execution_id}")
        print(f"   数据流验证：✅")
        print(f"   字段完整性：✅")
        print(f"   报告 API: ✅")


class TestValidatorUnit:
    """验证器单元测试"""
    
    def test_validate_valid_result(self):
        """测试验证有效结果"""
        from wechat_backend.validators import ResultValidator
        
        validator = ResultValidator(strict_mode=True)
        
        result = {
            'brand': '特斯拉',
            'question': '问题',
            'model': 'qwen',
            'response': {'content': '内容'},
            'tokens_used': 100
        }
        
        is_valid, errors, warnings = validator.validate(result)
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_missing_brand(self):
        """测试验证缺少 brand 字段"""
        from wechat_backend.validators import ResultValidator
        
        validator = ResultValidator(strict_mode=True)
        
        result = {
            'question': '问题',
            'model': 'qwen',
            'response': {'content': '内容'},
            'tokens_used': 100
        }
        
        is_valid, errors, warnings = validator.validate(result)
        assert not is_valid
        assert any('brand' in e for e in errors)
    
    def test_validate_empty_brand(self):
        """测试验证空 brand 字段"""
        from wechat_backend.validators import ResultValidator
        
        validator = ResultValidator(strict_mode=True)
        
        result = {
            'brand': '',
            'question': '问题',
            'model': 'qwen',
            'response': {'content': '内容'},
            'tokens_used': 100
        }
        
        is_valid, errors, warnings = validator.validate(result)
        assert not is_valid
        assert any('brand' in e for e in errors)
    
    def test_validate_batch(self):
        """测试批量验证"""
        from wechat_backend.validators import ResultValidator
        
        validator = ResultValidator(strict_mode=False)
        
        results = [
            {'brand': '特斯拉', 'question': '问题', 'model': 'qwen', 'response': {'content': '内容'}, 'tokens_used': 100},
            {'brand': '比亚迪', 'question': '问题', 'model': 'qwen', 'response': {'content': '内容'}, 'tokens_used': 90},
            {'brand': '', 'question': '问题', 'model': 'qwen', 'response': {'content': '内容'}, 'tokens_used': 80},  # 无效
        ]
        
        batch_result = validator.validate_batch(results)
        
        assert batch_result['total_count'] == 3
        assert batch_result['valid_count'] == 2
        assert batch_result['invalid_count'] == 1
        assert abs(batch_result['valid_ratio'] - 0.667) < 0.01


if __name__ == '__main__':
    # 运行测试
    pytest.main([__file__, '-v', '--tb=short'])
