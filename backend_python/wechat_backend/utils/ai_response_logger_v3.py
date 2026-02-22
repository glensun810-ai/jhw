#!/usr/bin/env python3
"""
AI 响应日志记录模块 V3 - 日志轮转增强版
用于保存 AI 搜索平台的完整反馈结果，支持日志轮转、备份和自动清理

增强特性：
- 追加模式写入（不覆盖已有内容）✅
- 自动日志轮转（当文件达到指定大小）
- 自动备份（gzip 压缩）
- 自动清理（保留最近 N 个文件）
- 线程安全
"""

import json
import os
import gzip
import shutil
import platform
import socket
import sys
import time
import traceback
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid

# 默认日志文件路径
DEFAULT_LOG_DIR = Path(__file__).parent.parent / "data" / "ai_responses"
DEFAULT_LOG_FILE = DEFAULT_LOG_DIR / "ai_responses.jsonl"

# 日志轮转配置
LOG_ROTATION_CONFIG = {
    'max_file_size_mb': 10,      # 单个文件最大 10MB
    'max_backup_count': 10,      # 最多保留 10 个备份文件
    'backup_compression': True,  # 启用 gzip 压缩
}

# 【任务 1】全局文件锁，用于保护 JSONL 文件写入
_file_lock = threading.Lock()
# 轮转锁（独立于写入锁，避免死锁）
_rotation_lock = threading.Lock()


class AIResponseLogger:
    """
    AI 响应记录器 - V3 日志轮转增强版
    记录每次 AI 调用的完整信息，支持日志轮转、备份和自动清理
    """

    def __init__(
        self, 
        log_file: Optional[str] = None,
        max_file_size_mb: int = None,
        max_backup_count: int = None,
        enable_compression: bool = None
    ):
        """
        初始化记录器

        Args:
            log_file: 日志文件路径，默认为 data/ai_responses/ai_responses.jsonl
            max_file_size_mb: 单个文件最大大小 (MB)，默认 10MB
            max_backup_count: 最多保留备份文件数，默认 10 个
            enable_compression: 是否启用 gzip 压缩备份，默认 True
        """
        if log_file:
            self.log_file = Path(log_file)
        else:
            self.log_file = DEFAULT_LOG_FILE

        # 确保日志目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # 加载轮转配置
        self.max_file_size = (max_file_size_mb or LOG_ROTATION_CONFIG['max_file_size_mb']) * 1024 * 1024
        self.max_backup_count = max_backup_count or LOG_ROTATION_CONFIG['max_backup_count']
        self.enable_compression = enable_compression if enable_compression is not None else LOG_ROTATION_CONFIG['backup_compression']

        # 系统信息（只获取一次）
        self.system_info = self._get_system_info()
        
        # 检查并执行日志轮转
        self._check_and_rotate()
        
        print(f"[AIResponseLogger V3] 初始化完成，日志文件：{self.log_file}")
        print(f"  - 最大文件大小：{self.max_file_size / 1024 / 1024:.1f}MB")
        print(f"  - 最大备份数量：{self.max_backup_count}")
        print(f"  - 压缩备份：{'是' if self.enable_compression else '否'}")

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

    def _check_and_rotate(self):
        """检查是否需要日志轮转"""
        if not self.log_file.exists():
            return
        
        try:
            file_size = self.log_file.stat().st_size
            if file_size >= self.max_file_size:
                self._rotate_log()
        except Exception as e:
            print(f"[AIResponseLogger] 检查日志轮转失败：{e}")

    def _rotate_log(self):
        """执行日志轮转"""
        with _rotation_lock:  # 确保同一时间只有一个线程在执行轮转
            try:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_name = f"ai_responses_{timestamp}.jsonl"
                backup_path = self.log_file.parent / backup_name
                
                # 移动当前日志文件到备份
                shutil.move(str(self.log_file), str(backup_path))
                print(f"[AIResponseLogger] 日志轮转：{self.log_file.name} → {backup_name}")
                
                # 压缩备份（如果启用）
                if self.enable_compression:
                    compressed_path = self._compress_backup(backup_path)
                    if compressed_path:
                        backup_path = compressed_path
                
                # 清理旧备份
                self._cleanup_old_backups()
                
                print(f"[AIResponseLogger] 日志轮转完成")
                
            except Exception as e:
                print(f"[AIResponseLogger] 日志轮转失败：{e}")

    def _compress_backup(self, backup_path: Path) -> Optional[Path]:
        """压缩备份文件"""
        try:
            compressed_path = backup_path.with_suffix('.jsonl.gz')
            with open(backup_path, 'rb') as f_in:
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 删除未压缩文件
            backup_path.unlink()
            
            # 计算压缩率
            original_size = backup_path.stat().st_size if backup_path.exists() else 0
            compressed_size = compressed_path.stat().st_size
            compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
            
            print(f"[AIResponseLogger] 压缩备份：{compressed_path.name} (压缩率：{compression_ratio:.1f}%)")
            return compressed_path
            
        except Exception as e:
            print(f"[AIResponseLogger] 压缩备份失败：{e}")
            return None

    def _cleanup_old_backups(self):
        """清理旧备份文件"""
        try:
            # 获取所有备份文件（包括压缩和未压缩的）
            backup_files = []
            for pattern in ['ai_responses_*.jsonl', 'ai_responses_*.jsonl.gz']:
                backup_files.extend(self.log_file.parent.glob(pattern))
            
            # 按修改时间排序（最新的在前）
            backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            
            # 删除超出数量的旧文件
            if len(backup_files) > self.max_backup_count:
                files_to_delete = backup_files[self.max_backup_count:]
                for file_path in files_to_delete:
                    file_path.unlink()
                    print(f"[AIResponseLogger] 清理旧备份：{file_path.name}")
            
            # 统计当前备份情况
            current_count = len(backup_files[:self.max_backup_count])
            total_size = sum(f.stat().st_size for f in backup_files[:self.max_backup_count])
            print(f"[AIResponseLogger] 当前备份：{current_count}/{self.max_backup_count} 文件，总计 {total_size / 1024 / 1024:.2f}MB")
            
        except Exception as e:
            print(f"[AIResponseLogger] 清理旧备份失败：{e}")

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
        platform_name: str,
        model: str,

        # 业务字段
        brand: Optional[str] = None,
        competitor: Optional[str] = None,
        industry: Optional[str] = None,
        question_category: Optional[str] = None,

        # 性能字段
        latency_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,

        # 质量字段
        success: bool = True,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
        response_quality_score: Optional[float] = None,

        # 网络/系统字段
        http_status_code: Optional[int] = None,
        retry_count: Optional[int] = None,
        circuit_breaker_open: Optional[bool] = None,

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
        raw_request: Optional[Dict] = None,
        raw_response: Optional[Dict] = None,

        # 扩展字段
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        记录一次 AI 响应 - V3 完整版
        所有参数都是可选的，但建议尽可能填写以获得最完整的数据
        """
        # 生成唯一记录 ID
        record_id = str(uuid.uuid4())

        # 构建完整记录
        record = {
            # 基础标识
            "record_id": record_id,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time(),
            "version": "3.0",  # V3 版本标识

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
                "name": platform_name,
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

        # 清理 None 值
        record = self._clean_none_values(record)

        # 检查并执行日志轮转（写入前检查）
        self._check_and_rotate()

        # 线程安全的文件写入 - 使用追加模式（不覆盖已有内容）
        try:
            with _file_lock:  # 线程安全锁
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    f.flush()  # 确保立即写入磁盘
                    os.fsync(f.fileno())  # 强制同步到磁盘
        except Exception as e:
            # 记录失败不应影响主流程
            print(f"[AIResponseLogger] 警告：写入日志失败：{e}")

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

        # 检查是否以标点符号结尾
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
        """递归清理字典中的 None 值和不可序列化的对象"""
        if isinstance(obj, dict):
            return {k: self._clean_none_values(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [self._clean_none_values(item) for item in item in obj if item is not None]
        elif hasattr(obj, 'value'):
            return obj.value
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return obj

    def get_stats(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        try:
            if not self.log_file.exists():
                return {"error": "日志文件不存在"}

            # 统计当前文件
            current_size = self.log_file.stat().st_size
            with open(self.log_file, 'r', encoding='utf-8') as f:
                line_count = sum(1 for _ in f)

            # 统计备份文件
            backup_files = []
            for pattern in ['ai_responses_*.jsonl', 'ai_responses_*.jsonl.gz']:
                backup_files.extend(self.log_file.parent.glob(pattern))
            
            total_backup_size = sum(f.stat().st_size for f in backup_files)
            total_backup_count = len(backup_files)

            return {
                "current_file": str(self.log_file),
                "current_size_mb": round(current_size / 1024 / 1024, 2),
                "current_records": line_count,
                "backup_count": total_backup_count,
                "backup_size_mb": round(total_backup_size / 1024 / 1024, 2),
                "total_size_mb": round((current_size + total_backup_size) / 1024 / 1024, 2),
                "max_file_size_mb": round(self.max_file_size / 1024 / 1024, 2),
                "max_backup_count": self.max_backup_count
            }

        except Exception as e:
            return {"error": f"统计失败：{e}"}


# 全局 logger 实例
_default_logger: Optional[AIResponseLogger] = None


def get_logger(log_file: Optional[str] = None) -> AIResponseLogger:
    """获取全局 logger 实例"""
    global _default_logger
    if _default_logger is None:
        _default_logger = AIResponseLogger(log_file)
    return _default_logger


def log_ai_response(**kwargs) -> Dict[str, Any]:
    """便捷函数：记录 AI 响应"""
    logger = get_logger()
    return logger.log_response(**kwargs)


def get_log_stats() -> Dict[str, Any]:
    """获取日志统计信息"""
    logger = get_logger()
    return logger.get_stats()


# 演示用法
if __name__ == "__main__":
    print("=" * 60)
    print("AI Response Logger V3 - 日志轮转增强版演示")
    print("=" * 60)
    
    # 创建 logger（使用小文件限制来演示轮转）
    logger = AIResponseLogger(
        max_file_size_mb=1,  # 1MB 触发轮转（演示用）
        max_backup_count=5
    )
    
    # 记录一条测试日志
    record = logger.log_response(
        question="什么是人工智能？",
        response="人工智能（AI）是计算机科学的一个分支...",
        platform_name="deepseek",
        model="deepseek-chat",
        brand="测试品牌",
        latency_ms=1500,
        success=True
    )
    
    print(f"\n✅ 记录成功：{record['record_id'][:8]}...")
    
    # 显示统计信息
    stats = logger.get_stats()
    print(f"\n📊 日志统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
