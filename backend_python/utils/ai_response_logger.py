#!/usr/bin/env python3
"""
AI响应日志记录模块
用于保存AI搜索平台的真实反馈结果，供后续模型训练使用
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# 默认日志文件路径
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "data" / "ai_responses"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "ai_responses.jsonl"


class AIResponseLogger:
    """
    AI响应记录器
    记录每次AI调用的完整信息，包括问题、答案、平台、模型等
    """
    
    def __init__(self, log_file: Optional[str] = None):
        """
        初始化记录器
        
        Args:
            log_file: 日志文件路径，默认为 data/ai_responses/ai_responses.jsonl
        """
        if log_file:
            self.log_file = Path(log_file)
        else:
            self.log_file = DEFAULT_LOG_FILE
            
        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
    def log_response(
        self,
        question: str,
        response: str,
        platform: str,
        model: str,
        brand: Optional[str] = None,
        competitor: Optional[str] = None,
        latency_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录一次AI响应
        
        Args:
            question: 问题内容
            response: AI回答内容
            platform: AI平台名称（如：豆包、DeepSeek等）
            model: 具体模型ID
            brand: 品牌名称（可选）
            competitor: 竞品名称（可选）
            latency_ms: 响应延迟（毫秒，可选）
            tokens_used: 使用的token数（可选）
            success: 是否成功
            error_message: 错误信息（失败时）
            metadata: 额外元数据（可选）
            
        Returns:
            记录的数据字典
        """
        # 构建记录数据
        record = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
            "platform": platform,
            "model": model,
            "success": success
        }
        
        # 添加可选字段
        if brand:
            record["brand"] = brand
        if competitor:
            record["competitor"] = competitor
        if latency_ms is not None:
            record["latency_ms"] = latency_ms
        if tokens_used is not None:
            record["tokens_used"] = tokens_used
        if error_message:
            record["error_message"] = error_message
        if metadata:
            record["metadata"] = metadata
            
        # 写入日志文件（JSON Lines格式，便于追加和解析）
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            # 记录失败不应影响主流程
            print(f"[AIResponseLogger] 警告：写入日志失败: {e}")
            
        return record
    
    def log_mvp_response(
        self,
        brand: str,
        question: str,
        response: str,
        platform: str,
        model: str,
        latency_ms: int,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        专门用于MVP场景的记录方法
        
        Args:
            brand: 品牌名称
            question: 问题内容
            response: AI回答内容
            platform: AI平台名称
            model: 模型ID
            latency_ms: 响应延迟（毫秒）
            success: 是否成功
            error_message: 错误信息
            
        Returns:
            记录的数据字典
        """
        return self.log_response(
            question=question,
            response=response,
            platform=platform,
            model=model,
            brand=brand,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            metadata={"source": "mvp_brand_test"}
        )
    
    def get_recent_responses(
        self,
        limit: int = 100,
        platform: Optional[str] = None,
        brand: Optional[str] = None
    ) -> list:
        """
        获取最近的响应记录
        
        Args:
            limit: 返回记录数量限制
            platform: 按平台筛选（可选）
            brand: 按品牌筛选（可选）
            
        Returns:
            记录列表
        """
        responses = []
        
        if not self.log_file.exists():
            return responses
            
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # 应用筛选条件
                        if platform and record.get('platform') != platform:
                            continue
                        if brand and record.get('brand') != brand:
                            continue
                        responses.append(record)
                    except json.JSONDecodeError:
                        continue
                        
                    if len(responses) >= limit:
                        break
                        
        except Exception as e:
            print(f"[AIResponseLogger] 警告：读取日志失败: {e}")
            
        return responses
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取日志统计信息
        
        Returns:
            统计信息字典
        """
        stats = {
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0,
            "platforms": {},
            "brands": set()
        }
        
        if not self.log_file.exists():
            return stats
            
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        stats["total_records"] += 1
                        
                        if record.get("success", True):
                            stats["successful_records"] += 1
                        else:
                            stats["failed_records"] += 1
                            
                        platform = record.get("platform")
                        if platform:
                            stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1
                            
                        brand = record.get("brand")
                        if brand:
                            stats["brands"].add(brand)
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            print(f"[AIResponseLogger] 警告：统计日志失败: {e}")
            
        # 转换set为list以便JSON序列化
        stats["brands"] = list(stats["brands"])
        stats["log_file"] = str(self.log_file)
        
        return stats


# 全局单例实例
_default_logger = None


def get_logger(log_file: Optional[str] = None) -> AIResponseLogger:
    """
    获取全局AI响应记录器实例
    
    Args:
        log_file: 可选的自定义日志文件路径
        
    Returns:
        AIResponseLogger实例
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = AIResponseLogger(log_file)
    return _default_logger


def log_ai_response(
    question: str,
    response: str,
    platform: str,
    model: str,
    **kwargs
) -> Dict[str, Any]:
    """
    便捷函数：记录AI响应（使用全局记录器）
    
    Args:
        question: 问题内容
        response: AI回答内容
        platform: AI平台名称
        model: 模型ID
        **kwargs: 其他可选参数
        
    Returns:
        记录的数据字典
    """
    logger = get_logger()
    return logger.log_response(
        question=question,
        response=response,
        platform=platform,
        model=model,
        **kwargs
    )
