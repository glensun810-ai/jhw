"""
统一响应格式中间件 - P0 架构级修复

所有 API 响应必须通过此中间件包装，确保格式一致性。

使用示例:
    from wechat_backend.middleware.response_formatter import StandardizedResponse
    
    @api_bp.route('/example', methods=['GET'])
    def get_example():
        data = {"key": "value"}
        return StandardizedResponse.success(
            data=data,
            message='获取成功',
            metadata={'version': '1.0'}
        )
    
    @api_bp.route('/error', methods=['GET'])
    def get_error():
        return StandardizedResponse.error(
            ErrorCode.DATA_NOT_FOUND,
            detail={'resource': 'report'}
        )

作者：系统架构组
日期：2026-03-18
版本：1.0.0
"""

from datetime import datetime
from flask import jsonify
from typing import Any, Dict, Optional

from wechat_backend.error_codes import ErrorCode
from wechat_backend.logging_config import api_logger


class StandardizedResponse:
    """
    统一响应格式类
    
    核心职责:
    1. 统一成功响应格式：{success, data, message, metadata, timestamp}
    2. 统一错误响应格式：{success, error: {code, message, detail}}
    3. 空数据自动拦截，防止空响应流向客户端
    4. 自动记录审计日志
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        http_status: int = 200
    ) -> tuple:
        """
        成功响应
        
        Args:
            data: 响应数据（不能为空字典或 None）
            message: 可选的成功消息
            metadata: 可选的元数据（分页、版本等）
            http_status: HTTP 状态码（默认 200）
        
        Returns:
            tuple: (jsonify_response, http_status)
            
        Response Format:
            {
                "success": True,
                "data": {...},
                "message": "操作成功",
                "metadata": {...},
                "timestamp": "2026-03-18T10:00:00Z"
            }
        """
        # 【架构级修复 - 第 1 层】数据为空时抛出明确错误，而非返回空响应
        if data is None:
            api_logger.warning("⚠️ [统一响应] 数据为 None，返回明确错误")
            return StandardizedResponse.error(
                ErrorCode.DATA_NOT_FOUND,
                http_status=404
            )
        
        if isinstance(data, dict) and len(data) == 0:
            api_logger.warning("⚠️ [统一响应] 数据为空字典，返回明确错误")
            return StandardizedResponse.error(
                ErrorCode.DATA_NOT_FOUND,
                http_status=404
            )
        
        # 构建标准响应
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加可选字段
        if message:
            response["message"] = message
        
        if metadata:
            response["metadata"] = metadata
        
        api_logger.debug(f"✅ [统一响应] 成功响应：{response.get('message', 'OK')}")
        return jsonify(response), http_status
    
    @staticmethod
    def error(
        error_code: ErrorCode,
        detail: Optional[Dict[str, Any]] = None,
        http_status: Optional[int] = None,
        custom_message: Optional[str] = None
    ) -> tuple:
        """
        错误响应
        
        Args:
            error_code: 错误码枚举
            detail: 详细错误信息（字典）
            http_status: HTTP 状态码（可选，默认使用 error_code 中的状态码）
            custom_message: 自定义错误消息（可选，覆盖 error_code 的默认消息）
        
        Returns:
            tuple: (jsonify_response, http_status)
            
        Response Format:
            {
                "success": False,
                "error": {
                    "code": "DATA_NOT_FOUND",
                    "message": "数据不存在",
                    "detail": {...}
                },
                "timestamp": "2026-03-18T10:00:00Z"
            }
        """
        response = {
            "success": False,
            "error": {
                "code": error_code.code,
                "message": custom_message or error_code.message
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # 添加详细错误信息
        if detail:
            response["error"]["detail"] = detail
        
        # 记录错误日志
        api_logger.warning(
            f"❌ [统一响应] 错误响应：{error_code.code} - {response['error']['message']}"
        )
        
        return jsonify(response), http_status or error_code.http_status
    
    @staticmethod
    def partial_success(
        data: Any,
        warnings: list = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple:
        """
        部分成功响应（用于数据不完整但仍有返回价值的场景）
        
        Args:
            data: 响应数据
            warnings: 警告列表
            message: 成功消息
            metadata: 元数据
        
        Returns:
            tuple: (jsonify_response, http_status)
            
        Response Format:
            {
                "success": True,
                "partial": True,
                "data": {...},
                "warnings": ["数据不完整"],
                "message": "部分成功",
                "timestamp": "..."
            }
        """
        response = {
            "success": True,
            "partial": True,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if warnings:
            response["warnings"] = warnings
        
        if message:
            response["message"] = message
        
        if metadata:
            response["metadata"] = metadata
        
        api_logger.warning(f"⚠️ [统一响应] 部分成功响应：{len(warnings or [])} 个警告")
        return jsonify(response), 207  # 207 Multi-Status
