"""
数据验证模块 (Data Validation Module)

P1-5: 综合数据验证

功能:
1. 验证数据完整性
2. 验证数据范围
3. 验证数据类型
4. 验证业务规则
5. 提供详细的验证错误信息

使用示例:
    validator = DataValidator()
    
    # 验证任务数据
    validator.validate_task_data(task_data)
    
    # 验证聚合结果
    validator.validate_aggregated_results(aggregated_results)
    
    # 验证品牌排名
    validator.validate_brand_rankings(brand_rankings)
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """验证异常类"""
    def __init__(self, message: str, field: str = None, value: Any = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)
    
    def __str__(self):
        if self.field:
            return f"Validation error in '{self.field}': {self.message}"
        return self.message


class DataValidator:
    """
    数据验证器
    
    提供全面的数据验证功能，确保数据质量和一致性
    """

    # 字段最大长度限制
    MAX_LENGTHS = {
        'execution_id': 64,
        'brand_name': 100,
        'model_name': 100,
        'question': 500,
        'response': 100000,
        'error_message': 1000,
        'status_text': 500,
    }

    # 数值范围限制
    VALUE_RANGES = {
        'health_score': (0, 100),
        'sov': (0, 100),
        'avg_sentiment': (0, 1),
        'success_rate': (0, 100),
        'rank': (1, 1000),
        'responses': (0, 1000000),
        'sov_share': (0, 100),
        'avg_rank': (-1, 1000),  # -1 表示无排名
        'total_tests': (0, 100000),
        'total_mentions': (0, 1000000),
    }

    def __init__(self, strict_mode: bool = True):
        """
        初始化验证器

        Args:
            strict_mode: 严格模式 (True=拒绝所有无效数据，False=尝试修复)
        """
        self.strict_mode = strict_mode
        self._validation_count = 0
        self._error_count = 0

    def validate_task_data(self, task_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证任务数据

        Args:
            task_data: 任务数据字典

        Returns:
            (是否有效，错误消息列表)
        """
        errors = []

        # 1. 检查必填字段
        required_fields = ['brand', 'model', 'question', 'response']
        for field in required_fields:
            if field not in task_data:
                errors.append(f"Missing required field: {field}")
                self._error_count += 1

        # 2. 验证字段长度
        for field, max_length in self.MAX_LENGTHS.items():
            if field in task_data and isinstance(task_data[field], str):
                if len(task_data[field]) > max_length:
                    errors.append(f"Field '{field}' too long (max {max_length}, got {len(task_data[field])})")
                    self._error_count += 1

        # 3. 验证响应内容
        if 'response' in task_data:
            response = task_data['response']
            if not isinstance(response, str):
                errors.append("Response must be a string")
                self._error_count += 1
            elif not response.strip():
                errors.append("Response cannot be empty")
                self._error_count += 1

        # 4. 验证状态
        if 'status' in task_data:
            status = task_data['status']
            valid_statuses = ['success', 'error', 'pending', 'cancelled']
            if status not in valid_statuses:
                errors.append(f"Invalid status: {status}. Must be one of {valid_statuses}")
                self._error_count += 1

        # 5. 验证错误消息
        if 'error' in task_data and task_data['error']:
            error_msg = task_data['error']
            if len(error_msg) > self.MAX_LENGTHS['error_message']:
                errors.append(f"Error message too long (max {self.MAX_LENGTHS['error_message']})")
                self._error_count += 1

        self._validation_count += 1
        
        if errors:
            logger.warning(f"Task data validation failed with {len(errors)} error(s)")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return len(errors) == 0, errors

    def validate_aggregated_results(self, aggregated_results: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        验证聚合结果

        Args:
            aggregated_results: 聚合结果字典

        Returns:
            (是否有效，错误消息列表)
        """
        errors = []

        # 1. 验证必填字段
        if 'main_brand' not in aggregated_results:
            errors.append("Missing required field: main_brand")
            self._error_count += 1

        if 'summary' not in aggregated_results:
            errors.append("Missing required field: summary")
            self._error_count += 1
            return False, errors

        summary = aggregated_results['summary']

        # 2. 验证数值范围
        for field, (min_val, max_val) in self.VALUE_RANGES.items():
            if field in summary:
                value = summary[field]
                if not isinstance(value, (int, float)):
                    errors.append(f"Field '{field}' must be a number, got {type(value).__name__}")
                    self._error_count += 1
                elif not (min_val <= value <= max_val):
                    errors.append(f"Field '{field}' out of range [{min_val}, {max_val}]: {value}")
                    self._error_count += 1

        # 3. 验证总数
        total_tests = summary.get('totalTests', 0)
        if not isinstance(total_tests, int) or total_tests < 0:
            errors.append(f"Invalid totalTests: {total_tests}")
            self._error_count += 1

        total_mentions = summary.get('totalMentions', 0)
        if not isinstance(total_mentions, int) or total_mentions < 0:
            errors.append(f"Invalid totalMentions: {total_mentions}")
            self._error_count += 1

        # 4. 验证详细结果
        if 'detailed_results' in aggregated_results:
            detailed_results = aggregated_results['detailed_results']
            if not isinstance(detailed_results, list):
                errors.append("detailed_results must be a list")
                self._error_count += 1

        self._validation_count += 1
        
        if errors:
            logger.warning(f"Aggregated results validation failed with {len(errors)} error(s)")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return len(errors) == 0, errors

    def validate_brand_rankings(self, brand_rankings: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
        """
        验证品牌排名列表

        Args:
            brand_rankings: 品牌排名列表

        Returns:
            (是否有效，错误消息列表)
        """
        errors = []

        if not isinstance(brand_rankings, list):
            errors.append("brand_rankings must be a list")
            self._error_count += 1
            return False, errors

        if len(brand_rankings) == 0:
            errors.append("brand_rankings cannot be empty")
            self._error_count += 1

        for i, ranking in enumerate(brand_rankings):
            prefix = f"Ranking[{i}]"

            # 1. 验证必填字段
            required_fields = ['brand', 'rank', 'responses']
            for field in required_fields:
                if field not in ranking:
                    errors.append(f"{prefix}: Missing required field '{field}'")
                    self._error_count += 1

            # 2. 验证品牌名称
            if 'brand' in ranking:
                brand = ranking['brand']
                if not isinstance(brand, str) or not brand.strip():
                    errors.append(f"{prefix}: Invalid brand name")
                    self._error_count += 1
                elif len(brand) > self.MAX_LENGTHS['brand_name']:
                    errors.append(f"{prefix}: Brand name too long")
                    self._error_count += 1

            # 3. 验证排名
            if 'rank' in ranking:
                rank = ranking['rank']
                if not isinstance(rank, (int, float)) or rank < 1:
                    errors.append(f"{prefix}: Invalid rank: {rank}")
                    self._error_count += 1

            # 4. 验证响应数
            if 'responses' in ranking:
                responses = ranking['responses']
                if not isinstance(responses, (int, float)) or responses < 0:
                    errors.append(f"{prefix}: Invalid responses: {responses}")
                    self._error_count += 1

            # 5. 验证 sov_share
            if 'sov_share' in ranking:
                sov_share = ranking['sov_share']
                if not isinstance(sov_share, (int, float)) or not (0 <= sov_share <= 100):
                    errors.append(f"{prefix}: Invalid sov_share: {sov_share}")
                    self._error_count += 1

            # 6. 验证 avg_sentiment
            if 'avg_sentiment' in ranking:
                avg_sentiment = ranking['avg_sentiment']
                if not isinstance(avg_sentiment, (int, float)) or not (0 <= avg_sentiment <= 1):
                    errors.append(f"{prefix}: Invalid avg_sentiment: {avg_sentiment}")
                    self._error_count += 1

        self._validation_count += 1
        
        if errors:
            logger.warning(f"Brand rankings validation failed with {len(errors)} error(s)")
            for error in errors:
                logger.warning(f"  - {error}")
        
        return len(errors) == 0, errors

    def validate_execution_id(self, execution_id: str) -> str:
        """
        验证执行 ID

        Args:
            execution_id: 执行 ID

        Returns:
            验证后的执行 ID

        Raises:
            ValidationError: 验证失败
        """
        if not execution_id:
            raise ValidationError("Execution ID cannot be empty", "execution_id")
        
        if not isinstance(execution_id, str):
            raise ValidationError("Execution ID must be a string", "execution_id", execution_id)
        
        if len(execution_id) > self.MAX_LENGTHS['execution_id']:
            raise ValidationError(
                f"Execution ID too long (max {self.MAX_LENGTHS['execution_id']})",
                "execution_id",
                execution_id
            )
        
        # 只允许字母、数字、下划线、连字符
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', execution_id):
            raise ValidationError(
                "Execution ID contains invalid characters",
                "execution_id",
                execution_id
            )
        
        return execution_id

    def get_stats(self) -> Dict[str, Any]:
        """获取验证器统计信息"""
        return {
            'validation_count': self._validation_count,
            'error_count': self._error_count,
            'strict_mode': self.strict_mode
        }


# 全局验证器实例
_validator: Optional[DataValidator] = None


def get_validator() -> DataValidator:
    """获取全局验证器实例"""
    global _validator
    if _validator is None:
        _validator = DataValidator()
    return _validator


def validate_task_data(task_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """便捷函数：验证任务数据"""
    return get_validator().validate_task_data(task_data)


def validate_aggregated_results(aggregated_results: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """便捷函数：验证聚合结果"""
    return get_validator().validate_aggregated_results(aggregated_results)


def validate_brand_rankings(brand_rankings: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    """便捷函数：验证品牌排名"""
    return get_validator().validate_brand_rankings(brand_rankings)


if __name__ == '__main__':
    # 测试验证器
    print("Testing DataValidator...")
    
    validator = DataValidator()
    
    # 测试有效数据
    valid_task = {
        'brand': 'Test Brand',
        'model': 'Test Model',
        'question': 'Test question?',
        'response': 'Test response',
        'status': 'success'
    }
    
    is_valid, errors = validator.validate_task_data(valid_task)
    print(f"Valid task: {is_valid}, errors: {errors}")
    
    # 测试无效数据
    invalid_task = {
        'brand': '',  # 空品牌
        'model': 'Test Model',
        # 缺少 question
        'response': 'Test response',
    }
    
    is_valid, errors = validator.validate_task_data(invalid_task)
    print(f"Invalid task: {is_valid}, errors: {errors}")
    
    # 打印统计
    stats = validator.get_stats()
    print(f"Stats: {stats}")
