#!/usr/bin/env python3
"""
AI 响应数据同步脚本

问题诊断：
- ai_responses.jsonl 中有 580 条记录（50 个唯一 execution_id）
- diagnosis_reports 表中有 117 个唯一 execution_id
- diagnosis_results 表中有 72 个唯一 execution_id
- 关键问题：ai_responses 中的 execution_id 与数据库中的 execution_id 完全不重叠！

原因分析：
1. ai_responses.jsonl 中的数据是 2026-02-14 到 2026-02-20 期间的旧数据
2. diagnosis_reports 表中的数据是 2026-03-14 到 2026-03-20 期间的新数据
3. 两个数据源来自不同的系统版本/实例，execution_id 不匹配

解决方案：
1. 检查 ai_responses.jsonl 中是否有最近日期的记录
2. 如果有，将这些记录同步到 diagnosis_reports 和 diagnosis_results 表
3. 如果没有，说明 ai_responses.jsonl 是历史遗留数据，不需要同步

作者：系统架构组
日期：2026-03-20
"""

import json
import sqlite3
import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend_python', 'wechat_backend'))

from wechat_backend.logging_config import api_logger

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend_python', 'database.db')
AI_RESPONSES_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend_python', 'data', 'ai_responses', 'ai_responses.jsonl')


def load_ai_responses(file_path: str) -> List[Dict[str, Any]]:
    """加载 ai_responses.jsonl 文件"""
    responses = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                responses.append(data)
            except json.JSONDecodeError as e:
                api_logger.error(f"解析 JSON 失败：{e}")
    return responses


def group_by_execution_id(responses: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """按 execution_id 分组响应记录"""
    grouped = {}
    for resp in responses:
        exec_id = resp.get('context', {}).get('execution_id', '')
        if exec_id:
            if exec_id not in grouped:
                grouped[exec_id] = []
            grouped[exec_id].append(resp)
    return grouped


def get_existing_execution_ids(conn: sqlite3.Connection) -> set:
    """获取数据库中已存在的 execution_id"""
    cursor = conn.cursor()
    cursor.execute('SELECT execution_id FROM diagnosis_reports')
    return set(row[0] for row in cursor.fetchall())


def sync_response_to_db(conn: sqlite3.Connection, exec_id: str, responses: List[Dict[str, Any]]) -> bool:
    """
    将单个 execution_id 的所有响应同步到数据库
    
    返回：
        True: 同步成功或已存在
        False: 同步失败
    """
    cursor = conn.cursor()
    
    # 检查是否已存在
    cursor.execute('SELECT id FROM diagnosis_reports WHERE execution_id = ?', (exec_id,))
    existing = cursor.fetchone()
    
    if existing:
        api_logger.info(f"⏭️  跳过已存在的 execution_id: {exec_id}")
        return True
    
    try:
        # 从第一个响应中提取元数据
        first_resp = responses[0]
        
        # 提取业务数据
        business = first_resp.get('business', {})
        brand_name = business.get('brand', '未知品牌')
        competitor = business.get('competitor', '')
        competitor_brands = [c.strip() for c in competitor.split(',') if c.strip()] if competitor else []
        
        # 提取用户信息
        metadata = first_resp.get('metadata', {})
        user_id = metadata.get('user_id', 'anonymous')
        
        # 提取配置信息
        context = first_resp.get('context', {})
        
        # 从问题中提取自定义问题
        question_text = first_resp.get('question', {}).get('text', '')
        custom_questions = [question_text] if question_text else []
        
        # 提取平台信息
        platform_info = first_resp.get('platform', {})
        model_name = platform_info.get('model', '')
        platform_name = platform_info.get('name', '')
        
        # 提取所有使用的模型
        selected_models = list(set(
            resp.get('platform', {}).get('model', '') 
            for resp in responses 
            if resp.get('status', {}).get('success', False)
        ))
        selected_models = [m for m in selected_models if m]
        
        # 计算状态
        all_success = all(resp.get('status', {}).get('success', False) for resp in responses)
        status = 'completed' if all_success else 'failed'
        progress = 100
        stage = 'completed'
        is_completed = True
        
        # 时间戳
        timestamp = first_resp.get('timestamp', datetime.now().isoformat())
        created_at = timestamp
        completed_at = timestamp if is_completed else None
        
        # 计算 checksum
        import hashlib
        report_data = {
            'execution_id': exec_id,
            'brand_name': brand_name,
            'user_id': user_id
        }
        checksum = hashlib.sha256(json.dumps(report_data, sort_keys=True).encode()).hexdigest()
        
        # 插入 diagnosis_reports 表
        cursor.execute('''
            INSERT INTO diagnosis_reports (
                execution_id, user_id, brand_name, competitor_brands,
                selected_models, custom_questions, status, progress, stage,
                is_completed, created_at, updated_at, completed_at,
                data_schema_version, server_version, checksum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            exec_id, user_id, brand_name, json.dumps(competitor_brands),
            json.dumps(selected_models), json.dumps(custom_questions),
            status, progress, stage, is_completed,
            created_at, created_at, completed_at,
            '1.0', '2.0.0', checksum
        ))
        
        report_id = cursor.lastrowid
        
        # 插入 diagnosis_results 表（每个响应一条记录）
        for resp in responses:
            if not resp.get('status', {}).get('success', False):
                continue
                
            question_text = resp.get('question', {}).get('text', '')
            response_text = resp.get('response', {}).get('text', '')
            
            # 提取 GEO 分析数据
            geo_analysis = resp.get('metadata', {}).get('geo_analysis', {})
            if not geo_analysis:
                # 尝试从 response 中解析
                response_text_stripped = response_text.strip()
                if response_text_stripped.endswith('}'):
                    try:
                        # 查找最后一个 JSON 对象
                        json_start = response_text_stripped.rfind('{')
                        if json_start != -1:
                            geo_json = response_text_stripped[json_start:]
                            geo_analysis = json.loads(geo_json)
                    except:
                        pass
            
            geo_data = json.dumps(geo_analysis if geo_analysis else {})
            
            # 质量评分
            quality_score = resp.get('quality', {}).get('completeness', 0.8)
            quality_level = 'good' if quality_score > 0.7 else 'fair'
            quality_details = json.dumps({'completeness': quality_score})
            
            # 性能数据
            performance = resp.get('performance', {})
            latency = performance.get('latency_ms', 0) / 1000.0  # 转换为秒
            tokens_used = performance.get('tokens', {}).get('total', 0)
            
            # 提取品牌
            extracted_brand = brand_name
            
            # 插入记录
            cursor.execute('''
                INSERT INTO diagnosis_results (
                    report_id, execution_id, brand, question, model,
                    response_content, response_latency, geo_data,
                    quality_score, quality_level, quality_details,
                    status, created_at, tokens_used, platform, extracted_brand
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report_id, exec_id, brand_name, question_text,
                resp.get('platform', {}).get('model', ''),
                response_text, latency, geo_data,
                quality_score, quality_level, quality_details,
                'success', created_at, tokens_used,
                resp.get('platform', {}).get('name', ''), extracted_brand
            ))
        
        conn.commit()
        api_logger.info(f"✅ 同步成功：{exec_id}, 品牌={brand_name}, 响应数={len(responses)}")
        return True
        
    except Exception as e:
        conn.rollback()
        api_logger.error(f"❌ 同步失败：{exec_id}, 错误：{e}", exc_info=True)
        return False


def main():
    """主函数"""
    print("="*80)
    print("AI 响应数据同步脚本")
    print("="*80)
    
    # 1. 加载 ai_responses
    print("\n1. 加载 ai_responses.jsonl...")
    if not os.path.exists(AI_RESPONSES_PATH):
        print(f"❌ 文件不存在：{AI_RESPONSES_PATH}")
        return 1
    
    responses = load_ai_responses(AI_RESPONSES_PATH)
    print(f"   加载了 {len(responses)} 条响应记录")
    
    # 2. 按 execution_id 分组
    print("\n2. 按 execution_id 分组...")
    grouped = group_by_execution_id(responses)
    print(f"   共有 {len(grouped)} 个唯一 execution_id")
    
    # 3. 检查日期分布
    print("\n3. 检查日期分布...")
    dates = {}
    for resp in responses:
        date = resp.get('timestamp', '')[:10]
        if date:
            dates[date] = dates.get(date, 0) + 1
    
    print("   日期分布:")
    for date in sorted(dates.keys()):
        print(f"     {date}: {dates[date]} 条记录")
    
    # 4. 检查数据库
    print("\n4. 检查数据库...")
    conn = sqlite3.connect(DB_PATH)
    existing_ids = get_existing_execution_ids(conn)
    print(f"   数据库中已有 {len(existing_ids)} 个 execution_id")
    
    # 5. 找出需要同步的 execution_id
    print("\n5. 找出需要同步的 execution_id...")
    to_sync = set(grouped.keys()) - existing_ids
    print(f"   需要新增：{len(to_sync)} 个")
    print(f"   已存在：{len(set(grouped.keys()) & existing_ids)} 个")
    
    if not to_sync:
        print("\n✅ 无需同步 - 所有 execution_id 已存在于数据库中")
        conn.close()
        return 0
    
    # 6. 执行同步
    print("\n6. 执行同步...")
    success_count = 0
    failed_count = 0
    
    for exec_id in to_sync:
        if sync_response_to_db(conn, exec_id, grouped[exec_id]):
            success_count += 1
        else:
            failed_count += 1
    
    # 7. 统计结果
    print("\n" + "="*80)
    print("同步结果统计")
    print("="*80)
    print(f"   新增成功：{success_count} 个 execution_id")
    print(f"   同步失败：{failed_count} 个 execution_id")
    print(f"   跳过已存在：{len(set(grouped.keys()) & existing_ids)} 个 execution_id")
    
    conn.close()
    
    if failed_count > 0:
        print(f"\n⚠️  有 {failed_count} 个记录同步失败，请检查日志")
        return 1
    else:
        print("\n✅ 同步完成！")
        return 0


if __name__ == '__main__':
    sys.exit(main())
