"""
NxM 执行引擎 - 熔断器模块

功能：
- 跟踪每个模型的连续失败次数
- 连续 3 次失败后自动熔断
- 熔断后不再请求该模型
- 状态持久化存储
"""

import json
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from wechat_backend.logging_config import api_logger

# 熔断器持久化存储路径
CIRCUIT_BREAKER_STORE_PATH = Path(__file__).parent.parent / "data" / "circuit_breaker_store.json"


class ModelCircuitBreaker:
    """
    模型熔断器 - 增强版
    
    功能：
    - 跟踪每个模型的连续失败次数
    - 连续 3 次失败后自动熔断
    - 熔断后不再请求该模型
    - 状态持久化存储
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300, persist: bool = True):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.persist = persist

        self.model_failures: Dict[str, int] = {}
        self.model_suspended: Dict[str, bool] = {}
        self.model_last_failure: Dict[str, datetime] = {}
        self._lock = threading.Lock()

        if self.persist:
            self._load_from_storage()

    def _load_from_storage(self):
        """从持久化存储加载状态"""
        try:
            if CIRCUIT_BREAKER_STORE_PATH.exists():
                with open(CIRCUIT_BREAKER_STORE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.model_failures = data.get('model_failures', {})
                self.model_suspended = {
                    k: v for k, v in data.get('model_suspended', {}).items()
                    if v
                }

                for model_name, timestamp_str in data.get('model_last_failure', {}).items():
                    try:
                        self.model_last_failure[model_name] = datetime.fromisoformat(timestamp_str)
                    except Exception as e:
                        api_logger.error(f"[CircuitBreaker] Error parsing timestamp for {model_name}: {e}", exc_info=True)
                        # 时间戳解析失败，跳过该模型

                self._check_recovery()
                api_logger.info(f"[CircuitBreaker] 加载状态：{len(self.model_suspended)} 个模型处于熔断状态")

        except Exception as e:
            api_logger.error(f"[CircuitBreaker] 加载状态失败：{e}")

    def _save_to_storage(self):
        """保存状态到持久化存储"""
        try:
            CIRCUIT_BREAKER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'model_failures': self.model_failures,
                'model_suspended': self.model_suspended,
                'model_last_failure': {
                    k: v.isoformat() for k, v in self.model_last_failure.items()
                }
            }

            with open(CIRCUIT_BREAKER_STORE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            api_logger.error(f"[CircuitBreaker] 保存状态失败：{e}")

    def _check_recovery(self):
        """检查是否有模型应该恢复"""
        now = datetime.now()
        recovered = []

        for model_name, suspended in self.model_suspended.items():
            if suspended:
                last_failure = self.model_last_failure.get(model_name)
                if last_failure and (now - last_failure).total_seconds() > self.recovery_timeout:
                    self.model_suspended[model_name] = False
                    self.model_failures[model_name] = 0
                    recovered.append(model_name)

        if recovered:
            api_logger.info(f"[CircuitBreaker] 恢复模型：{recovered}")
            if self.persist:
                self._save_to_storage()

    def is_available(self, model_name: str) -> bool:
        """检查模型是否可用"""
        with self._lock:
            self._check_recovery()
            return not self.model_suspended.get(model_name, False)

    def record_success(self, model_name: str):
        """记录成功"""
        with self._lock:
            if model_name in self.model_failures:
                self.model_failures[model_name] = 0

            if model_name in self.model_suspended:
                self.model_suspended[model_name] = False

            if self.persist:
                self._save_to_storage()

    def record_failure(self, model_name: str):
        """记录失败"""
        with self._lock:
            self.model_failures[model_name] = self.model_failures.get(model_name, 0) + 1
            self.model_last_failure[model_name] = datetime.now()

            if self.model_failures[model_name] >= self.failure_threshold:
                self.model_suspended[model_name] = True
                api_logger.warning(f"[CircuitBreaker] 模型 {model_name} 已熔断")

            if self.persist:
                self._save_to_storage()

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态"""
        return {
            'model_failures': self.model_failures.copy(),
            'model_suspended': self.model_suspended.copy(),
            'model_last_failure': {
                k: v.isoformat() for k, v in self.model_last_failure.items()
            }
        }


# 全局熔断器实例
_circuit_breaker: Optional[ModelCircuitBreaker] = None


def get_circuit_breaker() -> ModelCircuitBreaker:
    """获取全局熔断器实例"""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = ModelCircuitBreaker(failure_threshold=3, recovery_timeout=300, persist=True)
    return _circuit_breaker


def reset_circuit_breaker():
    """重置熔断器（用于测试）"""
    global _circuit_breaker
    _circuit_breaker = None
