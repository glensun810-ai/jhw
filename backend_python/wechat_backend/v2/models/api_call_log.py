"""
API 调用日志数据模型

用于记录所有对 AI 平台的请求和响应。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class APICallLog:
    """
    API 调用日志数据模型
    
    Attributes:
        execution_id: 所属诊断任务 ID
        brand: 品牌名称
        question: 问题内容
        model: AI 模型名称
        request_data: 完整的请求数据（JSON）
        request_timestamp: 请求时间
        request_headers: 请求头（脱敏后）
        response_data: 完整的响应数据（JSON，成功时）
        response_timestamp: 响应时间
        response_headers: 响应头
        status_code: HTTP 状态码
        success: 是否成功
        error_message: 错误信息（失败时）
        error_stack: 错误堆栈（可选）
        latency_ms: 响应延迟（毫秒）
        retry_count: 重试次数
        report_id: 关联的报告 ID（可为空）
        api_version: API 版本
        request_id: 请求 ID（由 AI 平台返回）
        has_sensitive_data: 是否包含敏感信息
        id: 数据库记录 ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    
    # 任务关联
    execution_id: str
    brand: str
    question: str
    model: str
    
    # 请求信息
    request_data: Dict[str, Any]
    request_timestamp: datetime
    request_headers: Optional[Dict[str, str]] = None
    
    # 响应信息（成功时）
    response_data: Optional[Dict[str, Any]] = None
    response_timestamp: Optional[datetime] = None
    response_headers: Optional[Dict[str, str]] = None
    
    # 状态信息
    status_code: Optional[int] = None
    success: bool = False
    error_message: Optional[str] = None
    error_stack: Optional[str] = None
    
    # 性能指标
    latency_ms: Optional[int] = None
    retry_count: int = 0
    
    # 元数据
    report_id: Optional[int] = None
    api_version: Optional[str] = None
    request_id: Optional[str] = None
    
    # 敏感信息标记
    has_sensitive_data: bool = False
    
    # 审计字段
    id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典（用于存储和 API 响应）
        
        Returns:
            Dict[str, Any]: 字典表示
        """
        result = {
            'id': self.id,
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'brand': self.brand,
            'question': self.question,
            'model': self.model,
            'request_data': self.request_data,
            'request_timestamp': self.request_timestamp.isoformat(),
            'success': self.success,
            'latency_ms': self.latency_ms,
            'retry_count': self.retry_count,
            'has_sensitive_data': self.has_sensitive_data,
            'created_at': self.created_at.isoformat(),
        }
        
        # 只在成功时有响应数据
        if self.success and self.response_data:
            result['response_data'] = self.response_data
            result['response_timestamp'] = self.response_timestamp.isoformat() if self.response_timestamp else None
            result['status_code'] = self.status_code
            result['request_id'] = self.request_id
        
        # 失败时记录错误信息
        if not self.success and self.error_message:
            result['error_message'] = self.error_message
            result['status_code'] = self.status_code
        
        # 可选的敏感信息标记（不返回实际敏感内容）
        if self.has_sensitive_data:
            result['sensitive_data_present'] = True
        
        return result
    
    def to_log_dict(self) -> Dict[str, Any]:
        """
        转换为结构化日志格式（用于日志记录）
        
        Returns:
            Dict[str, Any]: 日志字典
        """
        return {
            'event': 'api_call',
            'execution_id': self.execution_id,
            'report_id': self.report_id,
            'brand': self.brand,
            'model': self.model,
            'success': self.success,
            'latency_ms': self.latency_ms,
            'retry_count': self.retry_count,
            'status_code': self.status_code,
            'has_sensitive_data': self.has_sensitive_data,
        }
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'APICallLog':
        """
        从数据库行记录创建对象
        
        Args:
            row: 数据库行记录
        
        Returns:
            APICallLog: API 调用日志对象
        """
        return cls(
            id=row['id'],
            execution_id=row['execution_id'],
            report_id=row['report_id'],
            brand=row['brand'],
            question=row['question'],
            model=row['model'],
            request_data=json.loads(row['request_data']) if row['request_data'] else {},
            request_timestamp=datetime.fromisoformat(row['request_timestamp']) if row['request_timestamp'] else None,
            request_headers=json.loads(row['request_headers']) if row.get('request_headers') else None,
            response_data=json.loads(row['response_data']) if row.get('response_data') else None,
            response_timestamp=datetime.fromisoformat(row['response_timestamp']) if row.get('response_timestamp') else None,
            response_headers=json.loads(row['response_headers']) if row.get('response_headers') else None,
            status_code=row['status_code'],
            success=bool(row['success']),
            error_message=row['error_message'],
            error_stack=row['error_stack'],
            latency_ms=row['latency_ms'],
            retry_count=row['retry_count'],
            api_version=row['api_version'],
            request_id=row['request_id'],
            has_sensitive_data=bool(row['has_sensitive_data']),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None,
        )
