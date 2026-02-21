#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修复 realtime_persistence.py 添加输入验证和连接管理

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/realtime_persistence.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加输入验证引用
old_imports = '''from .database import SafeDatabaseQuery, save_test_record
from .logging_config import api_logger'''

new_imports = '''from .database import SafeDatabaseQuery, save_test_record
from .logging_config import api_logger
from .security.input_validator import (
    validate_execution_id,
    validate_brand_name,
    validate_model_name,
    validate_question,
    validate_response
)'''

content = content.replace(old_imports, new_imports)

# 2. 修改 save_task_result 方法添加输入验证
old_save_task = '''    def save_task_result(self, task_data: Dict[str, Any]) -> bool:
        """
        保存单个任务结果
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            是否保存成功
        """
        # 生成任务键 (避免重复保存)
        task_key = self._get_task_key(task_data)
        
        # 检查是否已保存
        if task_key in self.saved_tasks:
            api_logger.info(f"Task already saved: {task_key}")
            return False
        
        try:
            # 提取数据
            brand_name = task_data.get('brand', task_data.get('brand_name', ''))
            ai_model = task_data.get('aiModel', task_data.get('model', task_data.get('ai_model', '')))
            question = task_data.get('question', task_data.get('question_text', ''))
            response = task_data.get('response', task_data.get('content', ''))
            status = task_data.get('status', 'success')'''

new_save_task = '''    def save_task_result(self, task_data: Dict[str, Any]) -> bool:
        """
        保存单个任务结果
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            是否保存成功
        """
        # 生成任务键 (避免重复保存)
        task_key = self._get_task_key(task_data)
        
        # 检查是否已保存
        if task_key in self.saved_tasks:
            api_logger.info(f"Task already saved: {task_key}")
            return False
        
        try:
            #【修复 1】输入验证
            brand_name = validate_brand_name(
                task_data.get('brand', task_data.get('brand_name', ''))
            )
            ai_model = validate_model_name(
                task_data.get('aiModel', task_data.get('model', task_data.get('ai_model', '')))
            )
            question = validate_question(
                task_data.get('question', task_data.get('question_text', ''))
            )
            response = validate_response(
                task_data.get('response', task_data.get('content', ''))
            )
            status = task_data.get('status', 'success')'''

content = content.replace(old_save_task, new_save_task)

# 3. 修改保存逻辑使用上下文管理器
old_save_logic = '''            # 保存到数据库
            record_id = save_test_record(
                user_openid=self.user_openid,
                brand_name=brand_name,
                ai_models_used=[ai_model],
                questions_used=[question],
                overall_score=0,  # 单个测试不计算总分
                total_tests=1,
                results_summary={
                    'individual_test': True,
                    'execution_id': self.execution_id,
                    'success': status == 'success',
                    'task_key': task_key
                },
                detailed_results=[single_test_result]
            )
            
            # 标记为已保存
            self.saved_tasks.add(task_key)
            
            api_logger.info(f"Saved task result (ID: {record_id}): {brand_name}/{ai_model}/{question}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save task result: {e}")
            return False'''

new_save_logic = '''            #【修复 2】使用上下文管理器确保连接关闭
            with SafeDatabaseQuery(self.db_path) as safe_query:
                # 保存到数据库
                record_id = save_test_record(
                    user_openid=self.user_openid,
                    brand_name=brand_name,
                    ai_models_used=[ai_model],
                    questions_used=[question],
                    overall_score=0,  # 单个测试不计算总分
                    total_tests=1,
                    results_summary={
                        'individual_test': True,
                        'execution_id': self.execution_id,
                        'success': status == 'success',
                        'task_key': task_key
                    },
                    detailed_results=[single_test_result]
                )
            
            # 标记为已保存
            self.saved_tasks.add(task_key)
            
            api_logger.info(f"Saved task result (ID: {record_id}): {brand_name}/{ai_model}/{question}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save task result: {e}")
            return False'''

content = content.replace(old_save_logic, new_save_logic)

# 4. 修改 save_aggregated_results 方法添加输入验证和连接管理
old_save_agg = '''    def save_aggregated_results(self, aggregated_results: Dict[str, Any]) -> bool:
        """
        保存聚合结果
        
        Args:
            aggregated_results: 聚合结果字典
            
        Returns:
            是否保存成功
        """
        try:
            # 提取关键数据
            main_brand = aggregated_results.get('main_brand', '')
            summary = aggregated_results.get('summary', {})
            detailed_results = aggregated_results.get('detailed_results', [])
            
            # 计算总体评分
            health_score = summary.get('healthScore', 0)
            sov = summary.get('sov', 0)
            avg_sentiment = summary.get('avgSentiment', 0)
            success_rate = summary.get('successRate', 0)'''

new_save_agg = '''    def save_aggregated_results(self, aggregated_results: Dict[str, Any]) -> bool:
        """
        保存聚合结果
        
        Args:
            aggregated_results: 聚合结果字典
            
        Returns:
            是否保存成功
        """
        try:
            #【修复 1】输入验证
            main_brand = validate_brand_name(aggregated_results.get('main_brand', ''))
            summary = aggregated_results.get('summary', {})
            detailed_results = aggregated_results.get('detailed_results', [])
            
            # 计算总体评分
            health_score = float(summary.get('healthScore', 0))
            sov = float(summary.get('sov', 0))
            avg_sentiment = float(summary.get('avgSentiment', 0))
            success_rate = float(summary.get('successRate', 0))
            
            # 验证数据范围
            if not (0 <= health_score <= 100):
                raise ValueError(f"Invalid health_score: {health_score}")
            if not (0 <= sov <= 100):
                raise ValueError(f"Invalid sov: {sov}")
            if not (0 <= avg_sentiment <= 1):
                raise ValueError(f"Invalid avg_sentiment: {avg_sentiment}")
            if not (0 <= success_rate <= 100):
                raise ValueError(f"Invalid success_rate: {success_rate}")'''

content = content.replace(old_save_agg, new_save_agg)

# 5. 修改 save_aggregated_results 保存逻辑使用上下文管理器
old_save_agg_logic = '''            # 保存到专门的聚合表
            safe_query = SafeDatabaseQuery(self.db_path)
            
            # 检查是否已存在
            existing = safe_query.execute_query(
                'SELECT id FROM aggregated_results WHERE execution_id = ?',
                (self.execution_id,)
            )
            
            if existing:
                # 更新现有记录
                safe_query.execute_query('''
                    UPDATE aggregated_results
                    SET health_score = ?, sov = ?, avg_sentiment = ?, 
                        success_rate = ?, total_tests = ?, total_mentions = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE execution_id = ?
                ''', (
                    health_score, sov, avg_sentiment, 
                    success_rate, summary.get('totalTests', 0), 
                    summary.get('totalMentions', 0),
                    self.execution_id
                ))
                api_logger.info(f"Updated aggregated results for execution: {self.execution_id}")
            else:
                # 插入新记录
                safe_query.execute_query('''
                    INSERT INTO aggregated_results
                    (execution_id, main_brand, health_score, sov, avg_sentiment, 
                     success_rate, total_tests, total_mentions, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    self.execution_id, main_brand, health_score, sov, avg_sentiment,
                    success_rate, summary.get('totalTests', 0), summary.get('totalMentions', 0)
                ))
                api_logger.info(f"Inserted aggregated results for execution: {self.execution_id}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save aggregated results: {e}")
            return False'''

new_save_agg_logic = '''            #【修复 2】使用上下文管理器确保连接关闭
            with SafeDatabaseQuery(self.db_path) as safe_query:
                # 检查是否已存在
                existing = safe_query.execute_query(
                    'SELECT id FROM aggregated_results WHERE execution_id = ?',
                    (validate_execution_id(self.execution_id),)
                )
                
                if existing:
                    # 更新现有记录
                    safe_query.execute_query('''
                        UPDATE aggregated_results
                        SET health_score = ?, sov = ?, avg_sentiment = ?, 
                            success_rate = ?, total_tests = ?, total_mentions = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE execution_id = ?
                    ''', (
                        health_score, sov, avg_sentiment, 
                        success_rate, summary.get('totalTests', 0), 
                        summary.get('totalMentions', 0),
                        self.execution_id
                    ))
                    api_logger.info(f"Updated aggregated results for execution: {self.execution_id}")
                else:
                    # 插入新记录
                    safe_query.execute_query('''
                        INSERT INTO aggregated_results
                        (execution_id, main_brand, health_score, sov, avg_sentiment, 
                         success_rate, total_tests, total_mentions, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        validate_execution_id(self.execution_id), main_brand, 
                        health_score, sov, avg_sentiment,
                        success_rate, summary.get('totalTests', 0), 
                        summary.get('totalMentions', 0)
                    ))
                    api_logger.info(f"Inserted aggregated results for execution: {self.execution_id}")
            
            return True
            
        except Exception as e:
            api_logger.error(f"Failed to save aggregated results: {e}")
            return False'''

content = content.replace(old_save_agg_logic, new_save_agg_logic)

# 保存文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ realtime_persistence.py 已修复：添加输入验证和连接管理')
