#!/usr/bin/env python3
"""
AI响应日志记录模块 V2 - 增强版
用于保存AI搜索平台的完整反馈结果，支持模型训练、性能分析和问题排查
"""

import json
import os
import platform
import socket
import sys
import time
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid

# 默认日志文件路径
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "data" / "ai_responses"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "ai_responses.jsonl"


class AIResponseLogger:
    """
    AI响应记录器 - 增强版
    记录每次AI调用的完整信息，用于训练、分析和问题排查
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
        
        # 系统信息（只获取一次）
        self.system_info = self._get_system_info()
        
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return {
            "hostname": socket.gethostname(),
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    
    def _calculate_text_stats(self, text: str) -> Dict[str, Any]:
        """计算文本统计信息"""
        if not text:
            return {"length": 0, "lines": 0, "words": 0, "chars_no_spaces": 0}
        
        # 中文字符统计
        chinese_chars = len([c for c in text if '\u4e00' <= c <= '\u9fff'])
        # 英文单词统计（简单分词）
        english_words = len([w for w in text.split() if w.isalpha()])
        
        return {
            "length": len(text),
            "lines": text.count('\n') + 1,
            "words": len(text.split()),
            "chars_no_spaces": len(text.replace(' ', '').replace('\n', '')),
            "chinese_chars": chinese_chars,
            "english_words": english_words,
            "has_code_blocks": '```' in text,
            "has_markdown": any(md in text for md in ['**', '*', '#', '[', ']'])
        }
    
    def log_response(
        self,
        # 核心字段
        question: str,
        response: str,
        platform: str,
        model: str,
        
        # 业务字段
        brand: Optional[str] = None,
        competitor: Optional[str] = None,
        industry: Optional[str] = None,
        question_category: Optional[str] = None,  # 问题分类：品牌认知、产品对比等
        
        # 性能字段
        latency_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        
        # 质量字段
        success: bool = True,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,  # 错误类型分类
        response_quality_score: Optional[float] = None,  # 响应质量评分（0-1）
        
        # 网络/系统字段
        http_status_code: Optional[int] = None,
        retry_count: Optional[int] = None,  # 重试次数
        circuit_breaker_open: Optional[bool] = None,  # 是否触发熔断
        
        # 请求配置字段
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        
        # 上下文字段
        execution_id: Optional[str] = None,
        question_index: Optional[int] = None,
        total_questions: Optional[int] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        
        # 原始数据（用于调试）
        raw_request: Optional[Dict] = None,  # 原始请求体
        raw_response: Optional[Dict] = None,  # 原始响应体
        
        # 扩展字段
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录一次AI响应 - 完整版
        
        所有参数都是可选的，但建议尽可能填写以获得最完整的数据
        """
        # 生成唯一记录ID
        record_id = str(uuid.uuid4())
        
        # 构建完整记录
        record = {
            # 基础标识
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time(),
            "version": "2.0",  # 记录格式版本
            
            # 核心内容
            "question": {
                "text": question,
                "stats": self._calculate_text_stats(question)
            },
            "response": {
                "text": response,
                "stats": self._calculate_text_stats(response)
            },
            
            # 平台信息
            "platform": {
                "name": platform,
                "model": model,
                "api_version": metadata.get("api_version") if metadata else None
            },
            
            # 业务信息
            "business": {
                "brand": brand,
                "competitor": competitor,
                "industry": industry,
                "question_category": question_category
            },
            
            # 性能指标
            "performance": {
                "latency_ms": latency_ms,
                "tokens": {
                    "total": tokens_used,
                    "prompt": prompt_tokens,
                    "completion": completion_tokens
                },
                "throughput": round(tokens_used * 1000 / latency_ms, 2) if tokens_used and latency_ms else None
            },
            
            # 执行状态
            "status": {
                "success": success,
                "error_message": error_message,
                "error_type": error_type,
                "http_status_code": http_status_code
            },
            
            # 可靠性指标
            "reliability": {
                "retry_count": retry_count or 0,
                "circuit_breaker_open": circuit_breaker_open or False
            },
            
            # 请求配置
            "request_config": {
                "temperature": temperature,
                "max_tokens": max_tokens,
                "timeout_seconds": timeout_seconds
            },
            
            # 上下文信息
            "context": {
                "execution_id": execution_id,
                "session_id": session_id,
                "user_id": user_id,
                "question_index": question_index,
                "total_questions": total_questions
            },
            
            # 系统信息
            "system": self.system_info,
            
            # 质量评估
            "quality": {
                "score": response_quality_score,
                "has_structured_data": self._has_structured_data(response),
                "completeness": self._assess_completeness(response)
            },
            
            # 原始数据（调试用，可选）
            "raw": {
                "request": raw_request,
                "response": raw_response
            } if raw_request or raw_response else None,
            
            # 扩展元数据
            "metadata": metadata or {}
        }
        
        # 清理None值，保持数据整洁
        record = self._clean_none_values(record)
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            # 记录失败不应影响主流程
            print(f"[AIResponseLogger] 警告：写入日志失败: {e}")
            
        return record
    
    def _has_structured_data(self, text: str) -> bool:
        """检测响应是否包含结构化数据"""
        if not text:
            return False
        indicators = ['###', '##', '1.', '2.', '- ', '* ', '|', '```', '【']
        return any(ind in text for ind in indicators)
    
    def _assess_completeness(self, text: str) -> Optional[float]:
        """评估响应完整性（简单启发式）"""
        if not text:
            return 0.0
        
        score = 1.0
        
        # 检查是否以标点符号结尾（可能不完整）
        if text and text[-1] not in '。！？.!?':
            score -= 0.1
        
        # 检查长度
        if len(text) < 50:
            score -= 0.3
        elif len(text) < 100:
            score -= 0.1
        
        # 检查是否有结论性内容
        conclusion_words = ['总结', '结论', '建议', '因此', '综上所述', '总之', 'in conclusion']
        if not any(w in text.lower() for w in conclusion_words):
            score -= 0.1
        
        return max(0.0, round(score, 2))
    
    def _clean_none_values(self, obj):
        """递归清理字典中的None值"""
        if isinstance(obj, dict):
            return {k: self._clean_none_values(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._clean_none_values(item) for item in obj if item is not None]
        return obj
    
    def get_recent_responses(
        self,
        limit: int = 100,
        platform: Optional[str] = None,
        brand: Optional[str] = None,
        success_only: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict]:
        """
        获取最近的响应记录 - 增强版
        
        Args:
            limit: 返回记录数量限制
            platform: 按平台筛选
            brand: 按品牌筛选
            success_only: 只返回成功的记录
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
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
                        if platform and record.get('platform', {}).get('name') != platform:
                            continue
                        if brand and record.get('business', {}).get('brand') != brand:
                            continue
                        if success_only and not record.get('status', {}).get('success', True):
                            continue
                        if start_time and record.get('timestamp', '') < start_time:
                            continue
                        if end_time and record.get('timestamp', '') > end_time:
                            continue
                            
                        responses.append(record)
                    except json.JSONDecodeError:
                        continue
                        
                    if len(responses) >= limit:
                        break
                        
        except Exception as e:
            print(f"[AIResponseLogger] 警告：读取日志失败: {e}")
            
        return responses
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取日志统计信息 - 增强版
        
        Args:
            days: 统计最近几天的数据
        """
        from datetime import timedelta
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        stats = {
            "period_days": days,
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0,
            "platforms": {},
            "brands": set(),
            "models": set(),
            "performance": {
                "avg_latency_ms": 0,
                "total_tokens": 0,
                "latency_samples": []
            },
            "errors": {},
            "question_categories": {}
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
                        
                        # 只统计时间范围内的数据
                        if record.get('timestamp', '') < cutoff_time:
                            continue
                        
                        stats["total_records"] += 1
                        
                        # 成功/失败统计
                        if record.get("status", {}).get("success", True):
                            stats["successful_records"] += 1
                        else:
                            stats["failed_records"] += 1
                            error_type = record.get("status", {}).get("error_type", "unknown")
                            stats["errors"][error_type] = stats["errors"].get(error_type, 0) + 1
                            
                        # 平台统计
                        platform = record.get("platform", {}).get("name")
                        if platform:
                            stats["platforms"][platform] = stats["platforms"].get(platform, 0) + 1
                        
                        # 模型统计
                        model = record.get("platform", {}).get("model")
                        if model:
                            stats["models"].add(model)
                            
                        # 品牌统计
                        brand = record.get("business", {}).get("brand")
                        if brand:
                            stats["brands"].add(brand)
                        
                        # 问题分类统计
                        category = record.get("business", {}).get("question_category")
                        if category:
                            stats["question_categories"][category] = stats["question_categories"].get(category, 0) + 1
                        
                        # 性能统计
                        latency = record.get("performance", {}).get("latency_ms")
                        if latency:
                            stats["performance"]["latency_samples"].append(latency)
                        
                        tokens = record.get("performance", {}).get("tokens", {}).get("total")
                        if tokens:
                            stats["performance"]["total_tokens"] += tokens
                            
                    except json.JSONDecodeError:
                        continue
                        
            # 计算平均延迟
            if stats["performance"]["latency_samples"]:
                stats["performance"]["avg_latency_ms"] = round(
                    sum(stats["performance"]["latency_samples"]) / len(stats["performance"]["latency_samples"]), 2
                )
                del stats["performance"]["latency_samples"]
                        
        except Exception as e:
            print(f"[AIResponseLogger] 警告：统计日志失败: {e}")
            
        # 转换set为list以便JSON序列化
        stats["models"] = list(stats["models"])
        stats["brands"] = list(stats["brands"])
        stats["log_file"] = str(self.log_file)
        
        return stats


# 全局单例实例
_default_logger = None


def get_logger(log_file: Optional[str] = None) -> AIResponseLogger:
    """获取全局AI响应记录器实例"""
    global _default_logger
    if _default_logger is None:
        _default_logger = AIResponseLogger(log_file)
    return _default_logger


def log_ai_response(**kwargs) -> Dict[str, Any]:
    """便捷函数：记录AI响应（使用全局记录器）"""
    logger = get_logger()
    return logger.log_response(**kwargs)
