#!/usr/bin/env python3
"""
AI响应日志记录模块 - 增强版
用于保存AI搜索平台的完整反馈结果，支持多用户区分、大数据量处理和数据生命周期管理
"""

import json
import os
import platform
import socket
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import uuid
import gzip
import shutil
from concurrent.futures import ThreadPoolExecutor
import threading
from collections import defaultdict

# 默认日志目录结构
DEFAULT_LOG_BASE_DIR = Path(__file__).parent.parent / "data" / "ai_responses_enhanced"
USER_LOG_DIR = DEFAULT_LOG_BASE_DIR / "users"
SYSTEM_LOG_DIR = DEFAULT_LOG_BASE_DIR / "system"
ARCHIVE_LOG_DIR = DEFAULT_LOG_BASE_DIR / "archive"

# 确保目录存在
for directory in [DEFAULT_LOG_BASE_DIR, USER_LOG_DIR, SYSTEM_LOG_DIR, ARCHIVE_LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


class EnhancedAIResponseLogger:
    """
    增强版AI响应记录器
    支持多用户区分、数据分区、压缩和生命周期管理
    """
    
    def __init__(self, base_log_dir: Optional[str] = None):
        """
        初始化记录器
        
        Args:
            base_log_dir: 基础日志目录路径
        """
        if base_log_dir:
            self.base_log_dir = Path(base_log_dir)
        else:
            self.base_log_dir = DEFAULT_LOG_BASE_DIR
            
        # 子目录
        self.user_log_dir = self.base_log_dir / "users"
        self.system_log_dir = self.base_log_dir / "system"
        self.archive_log_dir = self.base_log_dir / "archive"
        
        # 确保目录存在
        for directory in [self.user_log_dir, self.system_log_dir, self.archive_log_dir]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # 系统信息（只获取一次）
        self.system_info = self._get_system_info()
        
        # 数据清理配置
        self.max_file_size_mb = 100  # 单文件最大100MB
        self.retention_days = 30     # 默认保留30天
        self.compression_enabled = True  # 启用压缩
        
        # 并发控制
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.write_lock = threading.Lock()
    
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
    
    def _get_user_log_file(self, user_id: str) -> Path:
        """获取用户的日志文件路径"""
        # 根据用户ID和日期创建分区
        today = datetime.now().strftime("%Y-%m-%d")
        user_dir = self.user_log_dir / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / f"ai_responses_{today}.jsonl"
    
    def _get_system_log_file(self) -> Path:
        """获取系统日志文件路径"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.system_log_dir / f"system_ai_responses_{today}.jsonl"
    
    def _rotate_if_needed(self, log_file: Path) -> Path:
        """如果文件过大，则进行轮转"""
        if log_file.exists() and log_file.stat().st_size > self.max_file_size_mb * 1024 * 1024:
            # 生成新文件名（带序号）
            base_name = log_file.stem
            suffix = log_file.suffix
            dir_path = log_file.parent
            
            # 查找下一个可用的序号
            counter = 1
            while True:
                new_filename = f"{base_name}_{counter}{suffix}"
                new_file_path = dir_path / new_filename
                if not new_file_path.exists():
                    return new_file_path
                counter += 1
        return log_file
    
    def _compress_file(self, file_path: Path):
        """压缩文件"""
        if not self.compression_enabled:
            return
            
        try:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            with open(file_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除原文件
            file_path.unlink()
            print(f"[EnhancedAIResponseLogger] Compressed: {file_path.name} -> {compressed_path.name}")
        except Exception as e:
            print(f"[EnhancedAIResponseLogger] Compression failed for {file_path}: {e}")
    
    def _should_compress_file(self, file_path: Path) -> bool:
        """判断是否应该压缩文件"""
        if not self.compression_enabled:
            return False
            
        # 如果文件存在超过1天，进行压缩
        if file_path.exists():
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            return (datetime.now() - mtime).days >= 1
        return False
    
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
        user_id: Optional[str] = None,  # 新增：用户ID
        
        # 原始数据（用于调试）
        raw_request: Optional[Dict] = None,  # 原始请求体
        raw_response: Optional[Dict] = None,  # 原始响应体
        
        # 扩展字段
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录一次AI响应 - 增强版
        支持多用户区分和数据分区
        """
        # 生成唯一记录ID
        record_id = str(uuid.uuid4())
        
        # 构建完整记录
        record = {
            # 基础标识
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time(),
            "version": "3.0",  # 增强版格式
            
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
                "user_id": user_id,  # 新增：用户ID
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
        
        # 确定日志文件路径
        if user_id and user_id != 'anonymous':
            log_file = self._get_user_log_file(user_id)
        else:
            log_file = self._get_system_log_file()
        
        # 轮转文件（如果需要）
        log_file = self._rotate_if_needed(log_file)
        
        # 写入日志文件
        try:
            with self.write_lock:  # 线程安全写入
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
        except Exception as e:
            # 记录失败不应影响主流程
            print(f"[EnhancedAIResponseLogger] 警告：写入日志失败: {e}")
            
        # 异步压缩旧文件
        self.executor.submit(self._async_compress_old_files)
        
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
    
    def _async_compress_old_files(self):
        """异步压缩旧文件"""
        try:
            # 遍历用户日志目录
            for user_dir in self.user_log_dir.iterdir():
                if user_dir.is_dir():
                    for log_file in user_dir.glob("*.jsonl"):
                        if self._should_compress_file(log_file):
                            self._compress_file(log_file)
            
            # 遍历系统日志目录
            for log_file in self.system_log_dir.glob("*.jsonl"):
                if self._should_compress_file(log_file):
                    self._compress_file(log_file)
        except Exception as e:
            print(f"[EnhancedAIResponseLogger] 异步压缩文件失败: {e}")
    
    def get_user_responses(
        self,
        user_id: str,
        limit: int = 100,
        platform: Optional[str] = None,
        brand: Optional[str] = None,
        success_only: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days_back: int = 7  # 查询最近几天的数据
    ) -> List[Dict]:
        """
        获取特定用户的响应记录
        
        Args:
            user_id: 用户ID
            limit: 返回记录数量限制
            platform: 按平台筛选
            brand: 按品牌筛选
            success_only: 只返回成功的记录
            start_time: 开始时间（ISO格式）
            end_time: 结束时间（ISO格式）
            days_back: 查询最近几天的数据
        """
        responses = []
        
        # 确定查询的时间范围
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        # 查找用户目录下的所有日志文件
        user_dir = self.user_log_dir / user_id
        if not user_dir.exists():
            return responses
        
        # 获取所有相关的日志文件（包括压缩文件）
        log_files = []
        for log_file in user_dir.glob("*.jsonl"):
            # 检查日期是否在范围内
            date_part = log_file.stem.split('_')[-1]  # 获取日期部分
            try:
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                if file_date >= cutoff_date:
                    log_files.append(log_file)
            except ValueError:
                continue  # 如果不是日期格式，跳过
        
        # 也包括压缩的文件
        for log_file in user_dir.glob("*.jsonl.gz"):
            date_part = log_file.stem.split('_')[-1]  # 获取日期部分
            try:
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                if file_date >= cutoff_date:
                    log_files.append(log_file)
            except ValueError:
                continue  # 如果不是日期格式，跳过
        
        # 按修改时间排序，最新的在前
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files:
            try:
                # 根据文件扩展名决定如何打开
                if log_file.suffix == '.gz':
                    import gzip
                    file_handle = gzip.open(log_file, 'rt', encoding='utf-8')
                else:
                    file_handle = open(log_file, 'r', encoding='utf-8')
                
                with file_handle as f:
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
                            return responses
                            
            except Exception as e:
                print(f"[EnhancedAIResponseLogger] 读取日志文件失败 {log_file}: {e}")
                continue
        
        return responses
    
    def get_system_responses(
        self,
        limit: int = 100,
        platform: Optional[str] = None,
        success_only: bool = False,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        days_back: int = 7
    ) -> List[Dict]:
        """
        获取系统级别的响应记录（匿名用户）
        """
        responses = []
        
        # 确定查询的时间范围
        cutoff_date = (datetime.now() - timedelta(days=days_back)).date()
        
        # 查找系统日志目录下的所有日志文件
        log_files = []
        for log_file in self.system_log_dir.glob("*.jsonl"):
            # 检查日期是否在范围内
            date_part = log_file.stem.split('_')[-1]  # 获取日期部分
            try:
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                if file_date >= cutoff_date:
                    log_files.append(log_file)
            except ValueError:
                continue  # 如果不是日期格式，跳过
        
        # 也包括压缩的文件
        for log_file in self.system_log_dir.glob("*.jsonl.gz"):
            date_part = log_file.stem.split('_')[-1]  # 获取日期部分
            try:
                file_date = datetime.strptime(date_part, "%Y-%m-%d").date()
                if file_date >= cutoff_date:
                    log_files.append(log_file)
            except ValueError:
                continue  # 如果不是日期格式，跳过
        
        # 按修改时间排序，最新的在前
        log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for log_file in log_files:
            try:
                # 根据文件扩展名决定如何打开
                if log_file.suffix == '.gz':
                    import gzip
                    file_handle = gzip.open(log_file, 'rt', encoding='utf-8')
                else:
                    file_handle = open(log_file, 'r', encoding='utf-8')
                
                with file_handle as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            
                            # 应用筛选条件
                            if platform and record.get('platform', {}).get('name') != platform:
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
                            return responses
                            
            except Exception as e:
                print(f"[EnhancedAIResponseLogger] 读取系统日志文件失败 {log_file}: {e}")
                continue
        
        return responses
    
    def get_all_users_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取所有用户的统计信息
        """
        stats = {
            "period_days": days,
            "total_records": 0,
            "successful_records": 0,
            "failed_records": 0,
            "active_users": set(),
            "platforms": {},
            "brands": set(),
            "performance": {
                "avg_latency_ms": 0,
                "total_tokens": 0,
                "latency_samples": []
            },
            "user_stats": {}  # 每个用户的统计
        }
        
        # 遍历所有用户目录
        for user_dir in self.user_log_dir.iterdir():
            if user_dir.is_dir():
                user_id = user_dir.name
                user_stats = self.get_user_statistics(user_id, days)
                
                # 合并到总体统计
                stats["total_records"] += user_stats["total_records"]
                stats["successful_records"] += user_stats["successful_records"]
                stats["failed_records"] += user_stats["failed_records"]
                stats["active_users"].add(user_id)
                
                # 合并平台统计
                for platform, count in user_stats["platforms"].items():
                    stats["platforms"][platform] = stats["platforms"].get(platform, 0) + count
                
                # 合并品牌统计
                stats["brands"].update(user_stats["brands"])
                
                # 合并性能统计
                stats["performance"]["total_tokens"] += user_stats["performance"]["total_tokens"]
                stats["performance"]["latency_samples"].extend(user_stats["performance"]["latency_samples"])
                
                # 保存用户统计
                stats["user_stats"][user_id] = user_stats
        
        # 计算总体平均延迟
        if stats["performance"]["latency_samples"]:
            stats["performance"]["avg_latency_ms"] = round(
                sum(stats["performance"]["latency_samples"]) / len(stats["performance"]["latency_samples"]), 2
            )
            del stats["performance"]["latency_samples"]
        
        # 转换set为list以便JSON序列化
        stats["brands"] = list(stats["brands"])
        stats["active_users"] = list(stats["active_users"])
        
        return stats
    
    def get_user_statistics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """
        获取特定用户的统计信息
        """
        from datetime import timedelta
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        stats = {
            "user_id": user_id,
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
        
        # 查找用户目录下的所有日志文件
        user_dir = self.user_log_dir / user_id
        if not user_dir.exists():
            return stats
        
        # 获取所有相关的日志文件（包括压缩文件）
        log_files = list(user_dir.glob("*.jsonl")) + list(user_dir.glob("*.jsonl.gz"))
        
        for log_file in log_files:
            try:
                # 根据文件扩展名决定如何打开
                if log_file.suffix == '.gz':
                    import gzip
                    file_handle = gzip.open(log_file, 'rt', encoding='utf-8')
                else:
                    file_handle = open(log_file, 'r', encoding='utf-8')
                
                with file_handle as f:
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
                            
            except Exception as e:
                print(f"[EnhancedAIResponseLogger] 统计用户日志失败 {log_file}: {e}")
                continue
        
        # 计算平均延迟
        if stats["performance"]["latency_samples"]:
            stats["performance"]["avg_latency_ms"] = round(
                sum(stats["performance"]["latency_samples"]) / len(stats["performance"]["latency_samples"]), 2
            )
            del stats["performance"]["latency_samples"]
        
        # 转换set为list以便JSON序列化
        stats["models"] = list(stats["models"])
        stats["brands"] = list(stats["brands"])
        
        return stats
    
    def cleanup_old_logs(self, retention_days: int = 30):
        """
        清理旧的日志文件
        """
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        # 清理用户日志
        for user_dir in self.user_log_dir.iterdir():
            if user_dir.is_dir():
                for log_file in user_dir.glob("*"):
                    if log_file.stat().st_mtime < cutoff_time.timestamp():
                        log_file.unlink()
                        print(f"[EnhancedAIResponseLogger] 删除旧日志: {log_file}")
        
        # 清理系统日志
        for log_file in self.system_log_dir.glob("*"):
            if log_file.stat().st_mtime < cutoff_time.timestamp():
                log_file.unlink()
                print(f"[EnhancedAIResponseLogger] 删除旧系统日志: {log_file}")


# 全局单例实例
_default_enhanced_logger = None


def get_enhanced_logger(log_dir: Optional[str] = None) -> EnhancedAIResponseLogger:
    """获取全局增强版AI响应记录器实例"""
    global _default_enhanced_logger
    if _default_enhanced_logger is None:
        _default_enhanced_logger = EnhancedAIResponseLogger(log_dir)
    return _default_enhanced_logger


def log_enhanced_response(**kwargs) -> Dict[str, Any]:
    """便捷函数：记录AI响应（使用增强版记录器）"""
    logger = get_enhanced_logger()
    return logger.log_response(**kwargs)