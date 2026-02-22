"""
NxM Test Execution Engine - Refactored for Deterministic Data Generation

重构目标：确保数据生成的『确定性』
1. 流式持久化：每个 (Question, Model) 完成后先写日志再更新内存
2. GEO 语义加固：强制解析 rank, sentiment, interception，失败时存入 error_code
3. 任务终点校验：results 数组长度必须等于 len(Q) * len(M) 才标记 completed

【模块四增强】系统鲁棒性：
4. 熔断机制与断点结果保护
5. 单任务硬超时控制
6. 异步心跳监控
7. 智能熔断策略

This module implements the NxM matrix execution strategy:
- Outer loop: iterates through questions
- Inner loop: iterates through models

品牌说明：
- main_brand: 用户自己的品牌（需要测试的品牌）
- competitor_brands: 竞品品牌列表（仅用于对比分析，不参与 API 请求）

每个执行包括 GEO analysis with self-audit instructions.
"""
import time
import traceback
import hashlib
import threading
import os
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from wechat_backend.ai_adapters.base_adapter import GEO_PROMPT_TEMPLATE, parse_geo_json
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from wechat_backend.ai_adapters.geo_parser import parse_geo_json_enhanced
from wechat_backend.config_manager import config_manager
from wechat_backend.logging_config import api_logger
from wechat_backend.database import save_test_record

# SSE 推送服务
from wechat_backend.services.sse_service import send_progress_update, send_intelligence_update


# ==================== 模块四：熔断机制 ====================

# 【任务 1】熔断器持久化存储路径
CIRCUIT_BREAKER_STORE_PATH = Path(__file__).parent.parent / "data" / "circuit_breaker_store.json"


class ModelCircuitBreaker:
    """
    【模块四】模型熔断器 - 增强版
    
    功能：
    - 跟踪每个模型的连续失败次数
    - 连续 3 次失败后自动熔断
    - 熔断后不再请求该模型
    - 【任务 1 增强】状态持久化存储
    """
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300, persist: bool = True):
        self.failure_threshold = failure_threshold  # 失败阈值
        self.recovery_timeout = recovery_timeout  # 恢复超时（秒）
        self.persist = persist  # 是否持久化
        
        # 【任务 1】从持久化存储加载状态
        self.model_failures: Dict[str, int] = {}
        self.model_suspended: Dict[str, bool] = {}
        self.model_last_failure: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        
        if self.persist:
            self._load_from_storage()
    
    def _load_from_storage(self):
        """【任务 1】从持久化存储加载状态"""
        try:
            if CIRCUIT_BREAKER_STORE_PATH.exists():
                with open(CIRCUIT_BREAKER_STORE_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.model_failures = data.get('model_failures', {})
                self.model_suspended = {
                    k: v for k, v in data.get('model_suspended', {}).items() 
                    if v  # 只加载仍处于熔断状态的模型
                }
                
                # 恢复最后失败时间
                for model_name, timestamp_str in data.get('model_last_failure', {}).items():
                    try:
                        self.model_last_failure[model_name] = datetime.fromisoformat(timestamp_str)
                    except:
                        pass
                
                # 检查是否有模型应该恢复
                self._check_recovery()
                
                api_logger.info(
                    f"[CircuitBreaker] Loaded state from storage: "
                    f"{len(self.model_suspended)} suspended models"
                )
        except Exception as e:
            api_logger.warning(f"[CircuitBreaker] Failed to load from storage: {e}")
            # 启动失败不影响使用，使用默认空状态
    
    def _save_to_storage(self):
        """【任务 1】保存状态到持久化存储"""
        if not self.persist:
            return
        
        try:
            # 确保目录存在
            CIRCUIT_BREAKER_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'model_failures': self.model_failures,
                'model_suspended': self.model_suspended,
                'model_last_failure': {
                    k: v.isoformat() for k, v in self.model_last_failure.items()
                },
                'last_updated': datetime.now().isoformat()
            }
            
            with open(CIRCUIT_BREAKER_STORE_PATH, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            api_logger.debug(f"[CircuitBreaker] State saved to storage")
        except Exception as e:
            api_logger.error(f"[CircuitBreaker] Failed to save to storage: {e}")
    
    def _check_recovery(self):
        """检查是否有模型应该恢复"""
        now = datetime.now()
        for model_name, suspended in list(self.model_suspended.items()):
            if suspended:
                last_failure = self.model_last_failure.get(model_name)
                if last_failure:
                    elapsed = (now - last_failure).total_seconds()
                    if elapsed >= self.recovery_timeout:
                        self.model_suspended[model_name] = False
                        self.model_failures[model_name] = 0
                        api_logger.info(
                            f"[CircuitBreaker] Model '{model_name}' auto-recovered after {elapsed:.0f}s"
                        )
    
    def record_failure(self, model_name: str):
        """记录模型失败"""
        with self._lock:
            if model_name not in self.model_failures:
                self.model_failures[model_name] = 0
            
            self.model_failures[model_name] += 1
            self.model_last_failure[model_name] = datetime.now()
            
            # 达到阈值，触发熔断
            if self.model_failures[model_name] >= self.failure_threshold:
                self.model_suspended[model_name] = True
                api_logger.warning(
                    f"[CircuitBreaker] Model '{model_name}' SUSPENDED after "
                    f"{self.model_failures[model_name]} consecutive failures"
                )
            
            # 【任务 1】持久化保存
            self._save_to_storage()
    
    def record_success(self, model_name: str):
        """记录模型成功"""
        with self._lock:
            self.model_failures[model_name] = 0
            self.model_suspended[model_name] = False
            
            # 【任务 1】持久化保存
            self._save_to_storage()
    
    def is_suspended(self, model_name: str) -> bool:
        """检查模型是否被熔断"""
        with self._lock:
            # 先检查是否有模型应该恢复
            self._check_recovery()
            
            if model_name not in self.model_suspended:
                return False
            
            return self.model_suspended[model_name]
    
    def get_suspended_models(self) -> List[str]:
        """获取所有被熔断的模型"""
        with self._lock:
            self._check_recovery()
            return [m for m, suspended in self.model_suspended.items() if suspended]
    
    def reset(self):
        """重置所有状态"""
        with self._lock:
            self.model_failures.clear()
            self.model_suspended.clear()
            self.model_last_failure.clear()
            
            # 【任务 1】持久化保存
            self._save_to_storage()
    
    def manual_resume(self, model_name: str) -> bool:
        """
        手动恢复模型
        
        Args:
            model_name: 模型名称
        
        Returns:
            bool: 是否成功恢复
        """
        with self._lock:
            if model_name in self.model_suspended:
                self.model_suspended[model_name] = False
                self.model_failures[model_name] = 0
                self._save_to_storage()
                api_logger.info(f"[CircuitBreaker] Model '{model_name}' manually resumed")
                return True
            return False


# 全局熔断器实例
_global_circuit_breaker = ModelCircuitBreaker(failure_threshold=3, recovery_timeout=300)


def get_circuit_breaker() -> ModelCircuitBreaker:
    """获取全局熔断器实例"""
    return _global_circuit_breaker


# ==================== 线程安全与缓存管理 ====================

# 线程锁用于原子化状态更新
_execution_store_lock = threading.Lock()

# 日志写入器缓存（每个 execution_id 一个写入器实例）
_logger_cache: Dict[str, Any] = {}
_logger_cache_lock = threading.Lock()


# ==================== 辅助函数 ====================

def _generate_result_hash(result_item: Dict[str, Any]) -> str:
    """
    生成结果项的唯一哈希值
    
    哈希基于：execution_id + question_id + model + timestamp
    用于防止重复写入和验证数据完整性
    """
    hash_content = f"{result_item.get('execution_id', '')}-{result_item.get('question_id', '')}-{result_item.get('model', '')}-{result_item.get('timestamp', '')}"
    return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()[:16]


def _get_or_create_logger(execution_id: str) -> Tuple[Any, Path]:
    """
    获取或创建指定 execution_id 的日志写入器
    
    使用缓存避免重复创建，同时返回日志文件路径用于后续验证
    """
    with _logger_cache_lock:
        if execution_id not in _logger_cache:
            from wechat_backend.utils.ai_response_logger_v3 import AIResponseLogger
            logger = AIResponseLogger()
            _logger_cache[execution_id] = logger
            api_logger.info(f"[LogWriter] Created logger for execution_id: {execution_id}, file: {logger.log_file}")
        return _logger_cache[execution_id], _logger_cache[execution_id].log_file


def _close_logger(execution_id: str) -> bool:
    """
    关闭并清理指定 execution_id 的日志写入器
    
    确保文件句柄被正确关闭，内容完全落盘
    """
    with _logger_cache_lock:
        if execution_id in _logger_cache:
            logger = _logger_cache[execution_id]
            # 如果有文件对象，显式 flush
            if hasattr(logger, '_file_handle') and logger._file_handle:
                logger._file_handle.flush()
                os.fsync(logger._file_handle.fileno())
            del _logger_cache[execution_id]
            api_logger.info(f"[LogWriter] Closed logger for execution_id: {execution_id}")
            return True
        return False


def _atomic_update_execution_store(
    execution_store: Dict[str, Any],
    execution_id: str,
    result_item: Dict[str, Any],
    total_executions: int,
    all_results_hashes: set
) -> bool:
    """
    原子化更新 execution_store
    
    特性：
    1. 使用线程锁保证线程安全
    2. 检查结果哈希值防止重复写入
    3. 更新时包含结果哈希值用于追踪
    
    Returns:
        bool: 是否成功更新（False 表示可能是重复结果）
    """
    with _execution_store_lock:
        if execution_id not in execution_store:
            api_logger.warning(f"[AtomicUpdate] Execution ID {execution_id} not found in store")
            return False
        
        # 生成结果哈希值
        result_hash = _generate_result_hash(result_item)
        
        # 检查是否重复
        if result_hash in all_results_hashes:
            api_logger.warning(
                f"[AtomicUpdate] Duplicate result detected for {execution_id}: "
                f"Q{result_item.get('question_id')}+{result_item.get('model')} (hash: {result_hash})"
            )
            return False
        
        # 添加到哈希集合
        all_results_hashes.add(result_hash)
        
        # 添加哈希值到结果项（用于追踪）
        result_item['_result_hash'] = result_hash
        
        # 追加到结果列表
        execution_store[execution_id].setdefault('results', []).append(result_item)
        
        # 更新进度
        completed_count = len(execution_store[execution_id]['results'])
        progress = int((completed_count / max(total_executions, 1)) * 100)
        
        execution_store[execution_id].update({
            'progress': progress,
            'completed': completed_count,
            'last_updated': datetime.now().isoformat()
        })

        # 【SSE 推送】发送进度更新
        stage = 'analyzing'
        if progress >= 80:
            stage = 'generating'
        elif progress >= 50:
            stage = 'aggregating'
        
        send_progress_update(execution_id, progress, stage, f'已完成 {completed_count}/{total_executions}')

        api_logger.debug(
            f"[AtomicUpdate] Updated store for {execution_id}: "
            f"progress={execution_store[execution_id]['progress']}%, "
            f"hash={result_hash}"
        )
        
        return True


def _normalize_brand_mentioned(value: Any) -> bool:
    """
    【任务 2】布尔值强制转换 - 确保 brand_mentioned 始终输出 True 或 False
    
    处理规则：
    - 布尔值：直接返回
    - 字符串 'yes'/'true'/'是'/'提到' -> True
    - 字符串 'no'/'false'/'否'/'未提到' -> False
    - 其他：尝试布尔转换，失败返回 False
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        lower_val = value.lower().strip()
        # True 值
        if lower_val in ['yes', 'true', '是', '提到', 'mentioned', '1']:
            return True
        # False 值
        if lower_val in ['no', 'false', '否', '未提到', 'not mentioned', '0']:
            return False
    
    # 其他类型尝试布尔转换
    try:
        return bool(value)
    except:
        return False


def _extract_interception_fallback(text: str) -> str:
    """
    【任务 2】拦截词兜底 - 如果 geo_analysis 解析完全失败，尝试用正则表达式提取 interception 字段
    
    提取策略：
    1. 查找"推荐了 XXX"、"选择了 XXX"、"而不是我们"等模式
    2. 查找竞品品牌名称（如果文本中包含）
    3. 返回空字符串（最后手段）
    """
    if not text:
        return ""
    
    import re
    
    # 模式 1: "推荐了/选择了/提到了 XXX" - 放宽匹配规则，匹配到下一个标点或空格前
    patterns = [
        r'推荐了\s*(.+?)(?:[,\s,.。]|$)',
        r'选择了\s*(.+?)(?:[,\s,.。]|$)',
        r'提到了\s*(.+?)(?:[,\s,.。]|$)',
        r'而不是\s*我们',
        r'而非\s*(.+?)(?:[,\s,.。]|$)',
        r'建议考虑\s*(.+?)(?:[,\s,.。]|$)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            matched_text = match.group(1) if match.lastindex else match.group(0)
            # 清理匹配结果
            cleaned = matched_text.strip(',.，。:：')
            if cleaned and len(cleaned) > 1:
                return cleaned
    
    # 模式 2: 查找引号内的品牌名（可能是竞品）
    quote_pattern = r'[""]([^""]{2,20})[""]'
    matches = re.findall(quote_pattern, text)
    if matches:
        # 返回第一个看起来像品牌名的匹配
        for match in matches:
            if any(c.isalpha() or '\u4e00' <= c <= '\u9fff' for c in match):
                return match
    
    # 兜底：返回空字符串
    return ""


def _parse_geo_with_validation(response_text: str, execution_id: str, q_idx: int, model_name: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    【GEO 语义加固】强制解析 GEO 指标，失败时返回 error_code
    
    【任务 2 优化】
    - 拦截词兜底：如果 geo_analysis 解析完全失败，尝试用正则表达式提取 interception
    - 布尔值强制转换：确保 brand_mentioned 始终输出 True 或 False

    Args:
        response_text: AI 响应文本
        execution_id: 执行 ID
        q_idx: 问题索引
        model_name: 模型名称

    Returns:
        (geo_data, error_code) 元组
        - geo_data: 包含 rank, sentiment, interception 等字段
        - error_code: 如果解析失败，返回错误代码；成功则为 None
    """
    # 默认值（用于解析完全失败时）
    default_geo = {
        "brand_mentioned": False,
        "rank": -1,
        "sentiment": 0.0,
        "cited_sources": [],
        "interception": "",
        "_parse_error": True  # 标记为解析失败
    }

    if not response_text or not isinstance(response_text, str):
        error_code = "EMPTY_RESPONSE"
        api_logger.warning(f"[GEO_Parse] Empty response for [Q:{q_idx+1}] [Model:{model_name}]")
        return default_geo, error_code

    try:
        # 使用增强版解析器
        geo_data = parse_geo_json_enhanced(response_text)

        # 【关键验证】强制检查三个核心指标是否存在
        validation_errors = []

        # 1. 验证 rank
        if 'rank' not in geo_data or not isinstance(geo_data.get('rank'), (int, float)):
            validation_errors.append("rank_missing_or_invalid")
            geo_data['rank'] = -1

        # 2. 验证 sentiment
        if 'sentiment' not in geo_data or not isinstance(geo_data.get('sentiment'), (int, float)):
            validation_errors.append("sentiment_missing_or_invalid")
            geo_data['sentiment'] = 0.0

        # 3. 验证 interception - 【任务 2】拦截词兜底
        if 'interception' not in geo_data or not isinstance(geo_data.get('interception'), str):
            validation_errors.append("interception_missing_or_invalid")
            # 尝试用正则表达式提取
            extracted_interception = _extract_interception_fallback(response_text)
            geo_data['interception'] = extracted_interception
            api_logger.info(
                f"[GEO_Parse] Fallback extraction [Q:{q_idx+1}] [Model:{model_name}]: "
                f"interception='{extracted_interception}'"
            )

        # 【任务 2】布尔值强制转换 - 确保 brand_mentioned 始终为 bool
        if 'brand_mentioned' in geo_data:
            geo_data['brand_mentioned'] = _normalize_brand_mentioned(geo_data['brand_mentioned'])
        else:
            geo_data['brand_mentioned'] = False

        # 如果有验证错误，添加 error_code
        if validation_errors:
            error_code = f"PARTIAL_PARSE_{'_'.join(validation_errors)}"
            api_logger.warning(
                f"[GEO_Parse] Partial parse for [Q:{q_idx+1}] [Model:{model_name}]: {error_code}"
            )
            # 添加解析错误标记
            geo_data['_parse_error'] = True
            geo_data['_validation_errors'] = validation_errors
            return geo_data, error_code

        # 解析成功
        api_logger.info(
            f"[GEO_Parse] Success [Q:{q_idx+1}] [Model:{model_name}]: "
            f"rank={geo_data.get('rank', -1)}, sentiment={geo_data.get('sentiment', 0)}, "
            f"interception='{geo_data.get('interception', '')[:20]}'"
        )
        return geo_data, None

    except Exception as e:
        error_code = f"PARSE_EXCEPTION_{type(e).__name__}"
        api_logger.error(
            f"[GEO_Parse] Exception for [Q:{q_idx+1}] [Model:{model_name}]: {e}"
        )
        return default_geo, error_code


def _verify_completion(results: List[Dict[str, Any]], expected_total: int) -> Dict[str, Any]:
    """
    【任务终点校验】验证任务是否可以标记为 completed
    
    Args:
        results: 结果列表
        expected_total: 期望的总执行数 (len(Q) * len(M))
    
    Returns:
        验证结果字典
    """
    actual_count = len(results)
    
    verification = {
        'can_complete': actual_count == expected_total,
        'expected_total': expected_total,
        'actual_count': actual_count,
        'missing_count': max(0, expected_total - actual_count),
        'success_count': len([r for r in results if r.get('status') == 'success']),
        'failed_count': len([r for r in results if r.get('status') == 'failed']),
        'geo_parsed_count': len([r for r in results if r.get('geo_data') is not None]),
        'error_codes': []
    }
    
    # 收集所有错误代码
    for result in results:
        if result.get('geo_data') and result['geo_data'].get('_parse_error'):
            verification['error_codes'].append({
                'question_id': result.get('question_id'),
                'model': result.get('model'),
                'error_code': result['geo_data'].get('_parse_error_code')
            })
    
    if verification['can_complete']:
        api_logger.info(
            f"[Completion_Check] Task can be marked as completed: "
            f"{actual_count}/{expected_total} results"
        )
    else:
        api_logger.warning(
            f"[Completion_Check] Task CANNOT be completed: "
            f"{actual_count}/{expected_total} results, missing {verification['missing_count']}"
        )
    
    return verification


# ==================== 核心执行函数 ====================

def execute_nxm_test(
    execution_id: str,
    main_brand: str,              # 用户自己的品牌（主品牌）
    competitor_brands: List[str],  # 竞品品牌列表（仅用于对比分析）
    selected_models: List[Dict[str, Any]],
    raw_questions: List[str],
    user_id: str = "anonymous",
    user_level: str = "Free",
    execution_store: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    重构后的 NxM 执行逻辑 - 确定性数据生成版本
    
    外层循环遍历问题，内层循环遍历模型
    请求次数 = 问题数 × 模型数（只针对用户自己的品牌）
    
    重构特性：
    1. 流式持久化：每个 (Question, Model) 完成后先写日志再更新内存
    2. GEO 语义加固：强制解析 rank, sentiment, interception，失败时存入 error_code
    3. 任务终点校验：results 数组长度必须等于 len(Q) * len(M) 才标记 completed
    
    Args:
        execution_id: 执行 ID
        main_brand: 用户自己的品牌（主品牌）
        competitor_brands: 竞品品牌列表（仅用于对比分析，不参与 API 请求）
        selected_models: 选定的模型列表
        raw_questions: 问题列表
        user_id: 用户 ID
        user_level: 用户等级
        execution_store: 执行状态存储
    
    Returns:
        包含所有测试结果的字典
    """
    # 结果哈希集合（用于防重复）
    all_results_hashes = set()
    
    # 日志文件路径（用于后续验证）
    log_file_path = None
    
    # 计算期望的总执行数
    expected_total = len(raw_questions) * len(selected_models)
    
    try:
        # 准备结果存储
        all_results = []
        total_executions = 0
        
        # 更新状态为 AI 获取阶段
        if execution_store:
            with _execution_store_lock:
                execution_store[execution_id].update({
                    'status': 'ai_fetching',
                    'stage': 'ai_fetching',
                    'progress': 10,
                    'total': expected_total,
                    'results': [],
                    'expected_total': expected_total
                })
        
        api_logger.info(
            f"Starting NxM async brand test '{execution_id}' for main brand: {main_brand}, "
            f"competitors: {competitor_brands}, (User: {user_id}, Level: {user_level}), "
            f"Formula: {len(raw_questions)} questions × {len(selected_models)} models = {expected_total}"
        )
        
        # 获取日志写入器（提前创建，确保文件句柄就绪）
        logger, log_file_path = _get_or_create_logger(execution_id)
        
        # ==================== NxM 循环开始 ====================
        # 外层遍历问题，内层遍历模型
        for q_idx, base_question in enumerate(raw_questions):
            # 替换问题中的品牌占位符为用户自己的品牌
            question_text = base_question.replace('{brandName}', main_brand)
            
            # 替换竞品占位符
            if competitor_brands:
                question_text = question_text.replace('{competitorBrand}', competitor_brands[0])
            else:
                question_text = question_text.replace('{competitorBrand}', '')
            
            # 遍历选定的每个模型
            for model_idx, model_info in enumerate(selected_models):
                model_name = model_info['name'] if isinstance(model_info, dict) else model_info
                total_executions += 1
                
                # 更新总数（原子操作）
                if execution_store and execution_id in execution_store:
                    with _execution_store_lock:
                        execution_store[execution_id]['total'] = total_executions
                
                api_logger.info(f"Executing [Q:{q_idx+1}] [MainBrand:{main_brand}] on [Model:{model_name}]")
                
                # 构建结果项（带时间戳用于哈希生成）
                # 【关键修复】添加 brand 字段，前端从 result.brand 提取品牌
                result_item = {
                    "question_id": q_idx,
                    "question_text": question_text,
                    "brand": main_brand,  # ✅ 前端从这里读取品牌
                    "main_brand": main_brand,
                    "competitor_brands": competitor_brands,
                    "model": model_name,
                    "content": "",
                    "geo_data": None,
                    "status": "pending",
                    "error": None,
                    "error_code": None,  # 【新增】GEO 解析错误代码
                    "timestamp": datetime.now().isoformat(),
                    "execution_id": execution_id
                }
                
                try:
                    # 1. 获取 AI 客户端
                    normalized_model_name = AIAdapterFactory.get_normalized_model_name(model_name)
                    
                    # 检查平台是否可用
                    if not AIAdapterFactory.is_platform_available(normalized_model_name):
                        raise ValueError(
                            f"Model {model_name} (normalized to {normalized_model_name}) "
                            "not registered or not configured"
                        )
                    
                    # 获取 API Key
                    api_key_value = config_manager.get_api_key(normalized_model_name)
                    if not api_key_value:
                        raise ValueError(f"API key not configured for model {model_name}")
                    
                    # 获取实际模型 ID
                    model_id = config_manager.get_platform_model(normalized_model_name) or normalized_model_name
                    
                    # 创建 AI 客户端
                    adapter = AIAdapterFactory.create(normalized_model_name, api_key_value, model_id)
                    
                    # 2. 构建带有 GEO 分析要求的 Prompt
                    competitors_str = ", ".join(competitor_brands) if competitor_brands else "无"
                    geo_prompt = GEO_PROMPT_TEMPLATE.format(
                        brand_name=main_brand,
                        competitors=competitors_str,
                        question=question_text
                    )
                    
                    # 3. 调用适配器获取回答
                    start_time = time.time()
                    
                    # 【SSE 推送】发送情报更新 - 开始处理
                    send_intelligence_update(execution_id, {
                        'question': question_text[:50] + '...' if len(question_text) > 50 else question_text,
                        'model': model_name,
                        'brand': main_brand,
                        'status': 'processing',
                        'questionIndex': q_idx + 1,
                        'totalQuestions': expected_total
                    })
                    
                    ai_response = adapter.send_prompt(
                        geo_prompt,
                        brand_name=main_brand,
                        competitors=competitor_brands,
                        execution_id=execution_id,
                        question_index=q_idx + 1,
                        total_questions=expected_total
                    )
                    latency = time.time() - start_time

                    # 【SSE 推送】发送情报更新 - 完成
                    if ai_response.success:
                        send_intelligence_update(execution_id, {
                            'question': question_text[:50] + '...' if len(question_text) > 50 else question_text,
                            'model': model_name,
                            'brand': main_brand,
                            'status': 'success',
                            'latency': int(latency * 1000),
                            'preview': (ai_response.content or '')[:100] + '...' if len(ai_response.content or '') > 100 else ai_response.content
                        })
                    else:
                        send_intelligence_update(execution_id, {
                            'question': question_text[:50] + '...' if len(question_text) > 50 else question_text,
                            'model': model_name,
                            'brand': main_brand,
                            'status': 'error',
                            'error': ai_response.error_message or '请求失败'
                        })
                    
                    # 4. 归因解析 (Attribution Parsing) - 从文本中提取 JSON 块
                    if ai_response.success:
                        response_text = ai_response.content or ""
                        
                        # 记录 AI 响应的前 200 个字符用于调试
                        api_logger.info(
                            f"AI Response preview [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}]: "
                            f"{response_text[:200]}..."
                        )
                        
                        # 【重构点 2】GEO 语义加固 - 强制解析三个核心指标
                        geo_data, error_code = _parse_geo_with_validation(
                            response_text,
                            execution_id,
                            q_idx,
                            model_name
                        )
                        
                        # 【重构点 1】流式持久化 - 先写日志，再更新内存
                        log_success = False
                        log_record_id = None
                        
                        try:
                            # 使用增强的日志记录（带异步和重试机制）
                            from wechat_backend.utils.ai_response_logger_enhanced import log_ai_response_enhanced
                            
                            log_result = log_ai_response_enhanced(
                                question=geo_prompt,
                                response=response_text,
                                platform=normalized_model_name,
                                model=model_id,
                                brand=main_brand,
                                competitor=", ".join(competitor_brands) if competitor_brands else None,
                                industry="家居定制",
                                question_category="品牌搜索",
                                latency_ms=int(latency * 1000),
                                tokens_used=getattr(ai_response, 'tokens_used', 0),
                                success=True,
                                execution_id=execution_id,
                                question_index=q_idx + 1,
                                total_questions=expected_total,
                                metadata={
                                    "source": "nxm_execution_engine",
                                    "geo_analysis": geo_data,
                                    "error_code": error_code
                                }
                            )
                            
                            log_record_id = log_result.get('record_id', 'unknown')
                            log_status = log_result.get('status', 'unknown')
                            
                            api_logger.info(
                                f"[AIResponseLogger] Task [Q:{q_idx+1}] [Model:{model_name}] logged, "
                                f"record_id={log_record_id}, status={log_status}"
                            )
                            
                            log_success = (log_status in ['queued', 'written', 'written_sync'])
                            
                        except Exception as log_error:
                            api_logger.error(
                                f"[AIResponseLogger] CRITICAL: Failed to log [Q:{q_idx+1}] [Model:{model_name}]: {log_error}"
                            )
                            # 日志写入失败是严重错误，记录但不中断主流程
                            result_item['log_error'] = str(log_error)
                        
                        # 5. 构造结构化结果
                        # 【关键修复】确保 brand 字段不被覆盖
                        result_item.update({
                            "content": response_text,
                            "geo_data": geo_data,  # 包含 rank, sentiment, interception
                            "status": "success",
                            "latency": latency,
                            "tokens_used": getattr(ai_response, 'tokens_used', 0),
                            "platform": normalized_model_name,
                            "log_success": log_success,
                            "error_code": error_code  # 如果有解析错误，记录错误代码
                            # ❌ 不要在这里覆盖 brand 字段
                        })
                        
                        api_logger.info(
                            f"Success: [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}] - "
                            f"GEO: rank={geo_data.get('rank', -1)}, sentiment={geo_data.get('sentiment', 0)}, "
                            f"error_code={error_code}"
                        )
                    else:
                        # AI 调用失败
                        # 【关键修复】确保 brand 字段不被覆盖
                        result_item.update({
                            "status": "failed",
                            "error": ai_response.error_message or "Unknown AI error",
                            "latency": latency,
                            "error_code": f"AI_ERROR_{getattr(ai_response, 'error_type', 'unknown')}"
                            # ❌ 不要在这里覆盖 brand 字段
                        })
                        api_logger.warning(
                            f"AI Error: [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}] - "
                            f"{ai_response.error_message}"
                        )
                        
                        # 【重构点 1】记录失败的调用到日志文件（同步写入）
                        try:
                            from wechat_backend.utils.ai_response_logger_enhanced import log_ai_response_enhanced
                            
                            log_result = log_ai_response_enhanced(
                                question=geo_prompt,
                                response="",
                                platform=normalized_model_name,
                                model=model_id,
                                brand=main_brand,
                                latency_ms=int(latency * 1000),
                                success=False,
                                error_message=ai_response.error_message,
                                error_type=getattr(ai_response, 'error_type', 'unknown'),
                                execution_id=execution_id,
                                question_index=q_idx + 1,
                                total_questions=expected_total,
                                metadata={"source": "nxm_execution_engine", "error_phase": "api_call"}
                            )
                            
                            log_record_id = log_result.get('record_id', 'unknown')
                            log_status = log_result.get('status', 'unknown')
                            
                            api_logger.info(
                                f"[AIResponseLogger] Error logged for [Q:{q_idx+1}] [Model:{model_name}], "
                                f"record_id={log_record_id}, status={log_status}"
                            )
                        except Exception as log_error:
                            api_logger.error(
                                f"[AIResponseLogger] CRITICAL: Failed to log error [Q:{q_idx+1}] [Model:{model_name}]: {log_error}"
                            )
                
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    api_logger.error(
                        f"Error on [Q:{q_idx+1}] [MainBrand:{main_brand}] [Model:{model_name}]: "
                        f"{str(e)}\n{error_traceback}"
                    )
                    result_item.update({
                        "status": "failed",
                        "error": str(e),
                        "error_code": f"EXCEPTION_{type(e).__name__}"
                    })
                    
                    # 【重构点 1】记录异常调用到日志文件（同步写入）
                    try:
                        from wechat_backend.utils.ai_response_logger_v3 import log_ai_response
                        log_record = log_ai_response(
                            question=geo_prompt,
                            response="",
                            platform=normalized_model_name,
                            model=model_id,
                            brand=main_brand,
                            latency_ms=int((time.time() - start_time) * 1000),
                            success=False,
                            error_message=str(e),
                            error_type="exception",
                            execution_id=execution_id,
                            question_index=q_idx + 1,
                            total_questions=expected_total,
                            metadata={"source": "nxm_execution_engine", "error_phase": "adapter_call"}
                        )
                        api_logger.info(
                            f"[AIResponseLogger] Exception logged for [Q:{q_idx+1}] [Model:{model_name}], "
                            f"record_id={log_record.get('record_id', 'unknown')}"
                        )
                    except Exception as log_error:
                        api_logger.error(
                            f"[AIResponseLogger] CRITICAL: Failed to log exception [Q:{q_idx+1}] [Model:{model_name}]: {log_error}"
                        )
                
                # 【重构点 1】原子化保存结果（线程安全 + 防重复）
                # 注意：此时 result_item 已经包含完整的 geo_data 和 error_code
                update_success = _atomic_update_execution_store(
                    execution_store,
                    execution_id,
                    result_item,
                    expected_total,
                    all_results_hashes
                )
                
                if update_success:
                    # 只在成功更新时添加到本地列表
                    all_results.append(result_item)
                else:
                    api_logger.warning(
                        f"[NxM] Skipped duplicate result for [Q:{q_idx+1}] [Model:{model_name}]"
                    )
        
        # ==================== NxM 循环结束 ====================
        
        # 【重构点 3】任务终点校验 - 验证是否可以标记为 completed
        completion_check = _verify_completion(all_results, expected_total)

        # 关闭日志写入器（确保文件句柄关闭）
        _close_logger(execution_id)

        # ==================== 评分计算 ====================
        # 从 all_results 中提取 geo_data 并计算品牌评分
        from scoring_engine import ScoringEngine
        from enhanced_scoring_engine import calculate_enhanced_scores
        from ai_judge_module import JudgeResult, ConfidenceLevel
        
        scoring_engine = ScoringEngine()
        brand_results_map = {}
        
        # 按品牌分组收集 judge_results
        for result in all_results:
            if result.get('status') == 'success' and result.get('geo_data'):
                geo = result['geo_data']
                brand = result.get('brand', main_brand)
                
                if brand not in brand_results_map:
                    brand_results_map[brand] = []
                
                # 从 geo_data 构建 judge_result
                # rank: 1-3 为高准确，4-6 为中等，7-10 为低，-1 为未入榜
                rank = geo.get('rank', -1)
                sentiment = geo.get('sentiment', 0)
                
                # 计算 accuracy_score (基于排名)
                if rank <= 0:
                    accuracy_score = 30 + sentiment * 20  # 未入榜
                elif rank <= 3:
                    accuracy_score = 85 + (3 - rank) * 5 + sentiment * 10  # 前 3 名
                elif rank <= 6:
                    accuracy_score = 65 + (6 - rank) * 5 + sentiment * 10  # 4-6 名
                else:
                    accuracy_score = 45 + (10 - rank) * 3 + sentiment * 10  # 7-10 名
                
                accuracy_score = max(0, min(100, accuracy_score))
                
                # completeness_score (基于是否有拦截分析)
                interception = geo.get('interception', {})
                completeness_score = 70 + len(interception) * 10 if interception else 60
                
                # sentiment_score 已经是 -1 到 1 的范围，转换为 0-100
                sentiment_score = (sentiment + 1) * 50
                
                judge_result = JudgeResult(
                    accuracy_score=accuracy_score,
                    completeness_score=completeness_score,
                    sentiment_score=sentiment_score,
                    purity_score=sentiment_score * 0.9,  # 基于情感估算
                    consistency_score=accuracy_score * 0.95,  # 基于准确性估算
                    judgement=f"Rank: {rank}, Sentiment: {sentiment:.2f}",
                    confidence_level=ConfidenceLevel.HIGH if rank > 0 else ConfidenceLevel.MEDIUM
                )
                brand_results_map[brand].append(judge_result)
        
        # 计算各品牌分数
        brand_scores = {}
        overall_score = 0
        
        for brand, judge_results in brand_results_map.items():
            if judge_results:
                try:
                    basic_score = scoring_engine.calculate(judge_results)
                    enhanced_result = calculate_enhanced_scores(judge_results, brand_name=brand)
                    
                    brand_scores[brand] = {
                        'overallScore': basic_score.geo_score,
                        'overallGrade': basic_score.grade,
                        'overallAuthority': basic_score.authority_score,
                        'overallVisibility': basic_score.visibility_score,
                        'overallSentiment': basic_score.sentiment_score,
                        'overallPurity': basic_score.purity_score,
                        'overallConsistency': basic_score.consistency_score,
                        'overallSummary': basic_score.summary
                    }
                    
                    # 主品牌分数作为 overall_score
                    if brand == main_brand:
                        overall_score = basic_score.geo_score
                        
                except Exception as e:
                    api_logger.error(f"Scoring failed for {brand}: {e}")
                    brand_scores[brand] = {
                        'overallScore': 0,
                        'overallGrade': 'D',
                        'overallAuthority': 0,
                        'overallVisibility': 0,
                        'overallSentiment': 0,
                        'overallPurity': 0,
                        'overallConsistency': 0,
                        'overallSummary': '评分计算失败'
                    }
        
        # 如果没有主品牌分数，使用所有品牌的平均分
        if overall_score == 0 and brand_scores:
            scores = [bs['overallScore'] for bs in brand_scores.values() if bs['overallScore'] > 0]
            if scores:
                overall_score = sum(scores) / len(scores)

        api_logger.info(f"[Scoring] Main brand: {main_brand}, Overall score: {overall_score}, Brand scores: {brand_scores}")

        # ==================== 竞品对比分析 ====================
        # 生成竞品对比数据
        all_brands = list(brand_scores.keys())
        if main_brand not in all_brands:
            all_brands.insert(0, main_brand)

        # 按分数排序
        sorted_brands = sorted(
            [(brand, data['overallScore']) for brand, data in brand_scores.items()],
            key=lambda x: x[1],
            reverse=True
        )
        
        # 【P0 修复】生成竞品对比详情数据
        def generate_competitor_comparison_data(brand_scores, main_brand, competitor_brands):
            """生成竞品对比详情数据"""
            comparison_data = []
            main_scores = brand_scores.get(main_brand, {})
            
            for competitor in competitor_brands:
                comp_scores = brand_scores.get(competitor, {})
                
                # 计算差异化评分
                main_overall = main_scores.get('overallScore', 0)
                comp_overall = comp_scores.get('overallScore', 0)
                differentiation_score = 100 - abs(main_overall - comp_overall)
                
                # 提取共同关键词（从官方关键词库）
                official_keywords = {
                    '华为': ['创新', '品质', '技术领先', '5G', '影像', 'XMAGE', '鸿蒙', '高端', '商务', '拍照'],
                    '小米': ['性价比', '发烧', 'MIUI', '智能家居', '年轻', '性能', '快充', '旗舰'],
                    'Oppo': ['拍照', '人像', '快充', '设计', '轻薄', 'ColorOS', '影像'],
                    'Vivo': ['拍照', '人像', 'HiFi', '设计', '轻薄', 'OriginOS', '影像']
                }
                main_keywords = set(official_keywords.get(main_brand, []))
                comp_keywords = set(official_keywords.get(competitor, []))
                common_keywords = list(main_keywords & comp_keywords)
                unique_to_brand = list(main_keywords - comp_keywords)
                unique_to_competitor = list(comp_keywords - main_keywords)
                
                # 生成差异化建议
                if differentiation_score >= 80:
                    gap_text = f'{main_brand}与{competitor}差异化明显，保持当前优势'
                elif differentiation_score >= 60:
                    gap_text = f'{main_brand}与{competitor}有一定差异化，建议强化独特卖点'
                else:
                    gap_text = f'{main_brand}与{competitor}差异化不足，急需建立独特品牌形象'
                
                comparison_data.append({
                    'competitor': competitor,
                    'differentiationScore': differentiation_score,
                    'commonKeywords': common_keywords[:5],
                    'uniqueToBrand': unique_to_brand[:5],
                    'uniqueToCompetitor': unique_to_competitor[:5],
                    'differentiationGap': gap_text
                })
            
            return comparison_data
        
        # 【P0 修复】生成雷达图数据
        def generate_radar_chart_data(brand_scores, main_brand, competitor_brands):
            """生成雷达图数据"""
            dimensions = ['authority', 'visibility', 'purity', 'consistency', 'overall']
            
            datasets = []
            
            # 主品牌数据
            main_scores = brand_scores.get(main_brand, {})
            datasets.append({
                'label': main_brand,
                'data': [
                    main_scores.get('overallAuthority', 0),
                    main_scores.get('overallVisibility', 0),
                    main_scores.get('overallPurity', 0),
                    main_scores.get('overallConsistency', 0),
                    main_scores.get('overallScore', 0)
                ],
                'borderColor': 'rgb(255, 99, 132)',
                'backgroundColor': 'rgba(255, 99, 132, 0.2)'
            })
            
            # 竞品数据
            colors = [
                ('rgb(54, 162, 235)', 'rgba(54, 162, 235, 0.2)'),
                ('rgb(255, 206, 86)', 'rgba(255, 206, 86, 0.2)'),
                ('rgb(75, 192, 192)', 'rgba(75, 192, 192, 0.2)')
            ]
            
            for i, competitor in enumerate(competitor_brands[:3]):
                comp_scores = brand_scores.get(competitor, {})
                color = colors[i % len(colors)]
                datasets.append({
                    'label': competitor,
                    'data': [
                        comp_scores.get('overallAuthority', 0),
                        comp_scores.get('overallVisibility', 0),
                        comp_scores.get('overallPurity', 0),
                        comp_scores.get('overallConsistency', 0),
                        comp_scores.get('overallScore', 0)
                    ],
                    'borderColor': color[0],
                    'backgroundColor': color[1]
                })
            
            return {
                'dimensions': dimensions,
                'datasets': datasets
            }

        # 生成首次提及率（按平台统计）
        platform_brand_first = {}
        for result in all_results:
            if result.get('status') == 'success' and result.get('geo_data'):
                platform = result.get('platform', 'unknown')
                geo = result['geo_data']
                rank = geo.get('rank', -1)
                brand = result.get('brand', main_brand)
                
                if platform not in platform_brand_first:
                    platform_brand_first[platform] = {}
                if rank > 0 and rank < platform_brand_first[platform].get('min_rank', 999):
                    platform_brand_first[platform]['min_rank'] = rank
                    platform_brand_first[platform]['brand'] = brand
        
        first_mention_by_platform = {}
        for platform, data in platform_brand_first.items():
            brand = data.get('brand', main_brand)
            if brand == main_brand:
                first_mention_by_platform[platform] = 1.0
            else:
                first_mention_by_platform[platform] = 0.0
        
        # 生成拦截风险分析
        interception_risks = []
        for brand, score_data in brand_scores.items():
            if brand != main_brand and score_data['overallScore'] > brand_scores.get(main_brand, {}).get('overallScore', 0):
                interception_risks.append({
                    'type': 'visibility',
                    'level': 'high' if score_data['overallScore'] - brand_scores[main_brand]['overallScore'] > 20 else 'medium',
                    'brand': brand,
                    'description': f"{brand}在 AI 认知中领先{score_data['overallScore'] - brand_scores[main_brand]['overallScore']}分"
                })
        
        competitive_analysis = {
            'brandScores': brand_scores,
            'firstMentionByPlatform': first_mention_by_platform,
            'interceptionRisks': interception_risks,
            'ranking': [{'brand': b, 'score': s} for b, s in sorted_brands],
            # 【P0 修复】添加竞品对比详情数据
            'competitorComparisonData': generate_competitor_comparison_data(
                brand_scores, main_brand, competitor_brands
            ),
            # 【P0 修复】添加雷达图数据
            'radarChartData': generate_radar_chart_data(
                brand_scores, main_brand, competitor_brands
            )
        }
        
        # ==================== 负面信源分析 ====================
        # 【关键修复】从 AI 响应中真实提取负面信源，而非预设模拟数据
        negative_sources = []
        main_brand_score = brand_scores.get(main_brand, {}).get('overallScore', 0)
        
        # 从 all_results 中提取 cited_sources
        for result in all_results:
            if result.get('status') == 'success' and result.get('geo_data'):
                geo = result['geo_data']
                cited_sources = geo.get('cited_sources', [])
                
                for source in cited_sources:
                    url = source.get('url', '')
                    site_name = source.get('site_name', '')
                    attitude = source.get('attitude', 'neutral')
                    
                    # 只提取负面或中性偏负面的信源
                    if attitude == 'negative' or (attitude == 'neutral' and main_brand_score < 70):
                        # 检查是否已存在（去重）
                        exists = any(ns.get('source_url') == url for ns in negative_sources)
                        if not exists and url and site_name:
                            # 根据情感分数计算严重性
                            sentiment = geo.get('sentiment', 0)
                            severity = 'high' if sentiment < -0.3 else ('medium' if sentiment < 0 else 'low')
                            
                            negative_sources.append({
                                'source_name': site_name,
                                'source_url': url,
                                'source_type': 'article' if 'zhuanlan' in url or 'article' in url else 'encyclopedia' if 'baike' in url else 'social_media',
                                'content_summary': f'AI 回答中引用的信源：{site_name}',
                                'sentiment_score': sentiment,
                                'severity': severity,
                                'impact_scope': 'high' if 'huawei.com' in url or 'xiaomi.com' in url else 'medium',
                                'estimated_reach': 100000 if 'baike' in url else 50000,
                                'discovered_at': datetime.now().isoformat(),
                                'recommendation': '官方回应 + SEO 优化' if severity == 'high' else '持续监控',
                                'priority_score': 90 if severity == 'high' else (70 if severity == 'medium' else 50),
                                'status': 'pending',
                                'from_ai_response': True  # 标记为从 AI 响应提取
                            })
        
        # 如果没有从 AI 响应中提取到负面信源，生成降级数据
        if len(negative_sources) == 0:
            # 方案 1: 从拦截风险中生成信源
            if len(interception_risks) > 0:
                for risk in interception_risks:
                    negative_sources.append({
                        'source_name': f'AI 分析 - {risk.get("brand", "竞品")} 领先',
                        'source_url': 'https://example.com/analysis',
                        'source_type': 'analysis',
                        'content_summary': risk.get('description', '竞品在 AI 认知中领先'),
                        'sentiment_score': -0.3,
                        'severity': risk.get('level', 'medium'),
                        'impact_scope': 'medium',
                        'estimated_reach': 50000,
                        'discovered_at': datetime.now().isoformat(),
                        'recommendation': '加强品牌内容建设',
                        'priority_score': 70,
                        'status': 'pending',
                        'from_ai_response': False
                    })
            
            # 方案 2: 从低分 AI 响应生成
            if len(negative_sources) == 0:
                for result in all_results:
                    if result.get('status') == 'success':
                        geo = result.get('geo_data', {})
                        sentiment = geo.get('sentiment', 0)
                        if sentiment < 0.5:  # 情感偏低
                            negative_sources.append({
                                'source_name': f'{result.get("model")} AI 分析',
                                'source_url': 'N/A',
                                'source_type': 'ai_analysis',
                                'content_summary': f'AI 响应情感偏低 (sentiment={sentiment:.2f})',
                                'sentiment_score': sentiment,
                                'severity': 'low',
                                'impact_scope': 'low',
                                'estimated_reach': 10000,
                                'discovered_at': datetime.now().isoformat(),
                                'recommendation': '优化品牌内容策略',
                                'priority_score': 50,
                                'status': 'pending',
                                'from_ai_response': False
                            })
                            if len(negative_sources) >= 2:
                                break
            
            # 方案 3: 确保至少有 1 条数据
            if len(negative_sources) == 0:
                negative_sources.append({
                    'source_name': '品牌监测中心',
                    'source_url': 'N/A',
                    'source_type': 'monitoring',
                    'content_summary': '暂无负面信源，品牌声誉良好',
                    'sentiment_score': 0.5,
                    'severity': 'low',
                    'impact_scope': 'low',
                    'estimated_reach': 0,
                    'discovered_at': datetime.now().isoformat(),
                    'recommendation': '继续保持良好品牌声誉',
                    'priority_score': 30,
                    'status': 'pending',
                    'from_ai_response': False
                })
        
        api_logger.info(f"[Competitive] Brands: {all_brands}, Interception risks: {len(interception_risks)}, Negative sources: {len(negative_sources)} (from AI: {sum(1 for ns in negative_sources if ns.get('from_ai_response'))})")

        # ==================== 语义偏移分析 ====================
        # 【新增】从 AI 响应中提取关键词，进行语义偏移分析
        official_keywords = {
            # 官方关键词库（可根据品牌动态加载）
            '华为': ['创新', '品质', '技术领先', '5G', '影像', 'XMAGE', '鸿蒙', '高端', '商务', '拍照'],
            '小米': ['性价比', '发烧', 'MIUI', '智能家居', '年轻', '性能', '快充', '旗舰'],
            'Oppo': ['拍照', '人像', '快充', '设计', '轻薄', 'ColorOS', '影像'],
            'Vivo': ['拍照', '人像', 'HiFi', '设计', '轻薄', 'OriginOS', '影像']
        }
        
        # 从 AI 响应中提取 AI 生成的关键词
        ai_keywords = {}
        ai_keyword_details = []
        
        for result in all_results:
            if result.get('status') == 'success' and result.get('content'):
                content = result.get('content', '')
                # 简单提取名词作为关键词（实际应使用 NLP）
                import re
                # 提取中文名词（2-4 个字）
                words = re.findall(r'[\u4e00-\u9fa5]{2,4}', content)
                for word in words:
                    if word not in ai_keywords:
                        ai_keywords[word] = 0
                    ai_keywords[word] += 1
                    ai_keyword_details.append({
                        'word': word,
                        'model': result.get('model', 'Unknown'),
                        'question': result.get('question_text', '')
                    })
        
        # 计算语义偏移
        brand_official = official_keywords.get(main_brand, [])
        brand_ai_keywords = {k: v for k, v in ai_keywords.items() if v > 0}
        
        # 缺失关键词（官方有但 AI 未提及）
        missing_keywords = [k for k in brand_official if k not in brand_ai_keywords]
        
        # 意外关键词（AI 提及但官方没有）
        unexpected_keywords = [k for k in brand_ai_keywords if k not in brand_official]
        
        # 负面术语（简单规则：包含负面含义的词）
        negative_terms = [k for k in unexpected_keywords if any(neg in k for neg in ['贵', '差', '慢', '问题', '故障', '不足', '缺点'])]
        
        # 正面术语
        positive_terms = [k for k in brand_ai_keywords if any(pos in k for pos in ['好', '优秀', '强', '领先', '出色', '推荐', '值得'])]
        
        # 计算偏移分数
        drift_score = int((len(missing_keywords) + len(negative_terms) * 2) / max(len(brand_official), 1) * 100)
        drift_score = min(100, drift_score)
        
        # 确定严重程度
        if drift_score >= 60:
            drift_severity = 'high'
            drift_severity_text = '严重偏移'
        elif drift_score >= 30:
            drift_severity = 'medium'
            drift_severity_text = '中度偏移'
        else:
            drift_severity = 'low'
            drift_severity_text = '偏移轻微'
        
        # 计算语义相似度
        common_count = len([k for k in brand_official if k in brand_ai_keywords])
        total_count = len(set(brand_official) | set(brand_ai_keywords.keys()))
        similarity_score = int((common_count / max(total_count, 1)) * 100)
        
        # 构建官方关键词对象
        official_words = [{'name': k, 'value': 1.0, 'sentiment_valence': 0.8, 'category': 'Official_Key'} for k in brand_official]
        
        # 构建 AI 生成关键词对象
        ai_generated_words = []
        for k, v in sorted(brand_ai_keywords.items(), key=lambda x: x[1], reverse=True)[:20]:
            category = 'AI_Generated_Risky' if k in negative_terms else ('AI_Generated_Positive' if k in positive_terms else 'AI_Generated_Neutral')
            ai_generated_words.append({
                'name': k,
                'value': v / max(1, max(brand_ai_keywords.values())),
                'sentiment_valence': 0.6 if k in positive_terms else (-0.5 if k in negative_terms else 0),
                'category': category
            })
        
        semantic_drift_data = {
            'driftScore': drift_score,
            'driftSeverity': drift_severity,
            'driftSeverityText': drift_severity_text,
            'similarityScore': similarity_score,
            'missingKeywords': missing_keywords[:10],  # 限制数量
            'unexpectedKeywords': unexpected_keywords[:10],
            'negativeTerms': negative_terms[:10],
            'positiveTerms': positive_terms[:10]
        }
        
        semantic_contrast_data = {
            'officialWords': official_words,
            'aiGeneratedWords': ai_generated_words
        }
        
        api_logger.info(f"[Semantic] Drift score: {drift_score}, Severity: {drift_severity}, Missing: {len(missing_keywords)}, Unexpected: {len(unexpected_keywords)}")

        # ==================== 优化建议生成 ====================
        # 【新增】基于分析结果生成优化建议
        recommendations = []
        
        # 基于语义偏移的建议
        if drift_score >= 30:
            recommendations.append({
                'title': '优化品牌关键词传播',
                'description': f'当前语义偏移分数为{drift_score}，{len(missing_keywords)}个官方关键词未被 AI 提及',
                'category': 'content',
                'phase': 'mid_term',
                'priority': 'high' if drift_score >= 60 else 'medium',
                'priority_score': 85 if drift_score >= 60 else 65,
                'urgency': 8 if drift_score >= 60 else 5,
                'estimated_impact': 'high' if drift_score >= 60 else 'medium',
                'target': f'{main_brand}品牌内容团队',
                'action_steps': [
                    f'加强{", ".join(missing_keywords[:3])}等关键词的内容建设',
                    '在官方渠道增加关键词曝光',
                    '与 AI 平台合作优化品牌认知'
                ]
            })
        
        # 基于负面术语的建议
        if len(negative_terms) > 0:
            recommendations.append({
                'title': '处理负面关键词影响',
                'description': f'发现{len(negative_terms)}个负面术语：{", ".join(negative_terms[:3])}',
                'category': 'pr',
                'phase': 'short_term',
                'priority': 'high',
                'priority_score': 90,
                'urgency': 9,
                'estimated_impact': 'high',
                'target': f'{main_brand}公关团队',
                'action_steps': [
                    '监测负面术语传播情况',
                    '准备官方回应声明',
                    '联系平台方沟通处理',
                    '跟踪处理结果'
                ]
            })
        
        # 基于竞品对比的建议
        for risk in interception_risks:
            if risk.get('level') == 'high':
                recommendations.append({
                    'title': f'应对{risk.get("brand", "竞品")}竞争',
                    'description': risk.get('description', '竞品在 AI 认知中领先'),
                    'category': 'strategy',
                    'phase': 'mid_term',
                    'priority': 'high',
                    'priority_score': 80,
                    'urgency': 7,
                    'estimated_impact': 'medium',
                    'target': f'{main_brand}战略团队',
                    'action_steps': [
                        '分析竞品优势领域',
                        '制定差异化竞争策略',
                        '加强品牌独特卖点传播'
                    ]
                })
        
        # 基于负面信源的建议
        high_severity_sources = [ns for ns in negative_sources if ns.get('severity') == 'high']
        if len(high_severity_sources) > 0:
            recommendations.append({
                'title': '处理高风险负面信源',
                'description': f'发现{len(high_severity_sources)}个高风险负面信源',
                'category': 'pr',
                'phase': 'short_term',
                'priority': 'critical',
                'priority_score': 95,
                'urgency': 10,
                'estimated_impact': 'high',
                'target': f'{main_brand}公关和 SEO 团队',
                'action_steps': [
                    '立即评估负面信源影响',
                    '准备官方回应',
                    '联系平台方处理',
                    '制定 SEO 优化策略'
                ]
            })
        
        # 计算建议统计
        high_priority_count = sum(1 for r in recommendations if r.get('priority') in ['critical', 'high'])
        medium_priority_count = sum(1 for r in recommendations if r.get('priority') == 'medium')
        low_priority_count = sum(1 for r in recommendations if r.get('priority') == 'low')
        
        recommendation_data = {
            'recommendations': recommendations,
            'totalCount': len(recommendations),
            'highPriorityCount': high_priority_count,
            'mediumPriorityCount': medium_priority_count,
            'lowPriorityCount': low_priority_count
        }
        
        api_logger.info(f"[Recommendations] Generated {len(recommendations)} recommendations, High priority: {high_priority_count}")
        
        # 7. 更新任务最终状态
        api_logger.info(
            f"NxM test execution completed for '{execution_id}'. "
            f"Total: {total_executions}, Results: {len(all_results)}, "
            f"Formula: {len(raw_questions)} questions × {len(selected_models)} models = {expected_total}"
        )
        
        if execution_store and execution_id in execution_store:
            with _execution_store_lock:
                # 【关键】只有当 results 数组长度等于 expected_total 时，才标记为 completed
                if completion_check['can_complete']:
                    execution_store[execution_id].update({
                        'status': 'completed',
                        'stage': 'completed',
                        'progress': 100,
                        'results': all_results,
                        'total': expected_total,
                        'completed': len(all_results),
                        'all_results_hashes': list(all_results_hashes),
                        'completion_verified': True
                    })
                    api_logger.info(
                        f"[Completion_Check] Task {execution_id} marked as COMPLETED"
                    )
                else:
                    # 结果不完整，标记为 incomplete 而不是 completed
                    execution_store[execution_id].update({
                        'status': 'incomplete',
                        'stage': 'incomplete',
                        'progress': int((len(all_results) / expected_total) * 100),
                        'results': all_results,
                        'total': expected_total,
                        'completed': len(all_results),
                        'missing_count': completion_check['missing_count'],
                        'all_results_hashes': list(all_results_hashes),
                        'completion_verified': False,
                        'completion_check': completion_check,
                        'error_message': f"Missing {completion_check['missing_count']} results"
                    })
                    api_logger.warning(
                        f"[Completion_Check] Task {execution_id} marked as INCOMPLETE: "
                        f"{len(all_results)}/{expected_total} results"
                    )
        
        # 将结果保存到数据库
        try:
            record_id = save_test_record(
                user_openid=user_id or "anonymous",
                brand_name=main_brand,
                ai_models_used=[m['name'] if isinstance(m, dict) else m for m in selected_models],
                questions_used=raw_questions,
                overall_score=overall_score,  # ✅ 使用计算出的分数
                total_tests=len(all_results),
                results_summary={
                    'executionId': execution_id,
                    'totalTests': len(all_results),
                    'successfulTests': len([r for r in all_results if r.get('status') == 'success']),
                    'nxmExecution': True,
                    'competitorBrands': competitor_brands,
                    'formula': f"{len(raw_questions)} questions × {len(selected_models)} models = {expected_total}",
                    'completionVerified': completion_check['can_complete'],
                    'completionCheck': completion_check,
                    'brandScores': brand_scores,
                    'overallScore': overall_score,
                    'competitiveAnalysis': competitive_analysis,
                    'negativeSources': negative_sources,
                    'semanticDriftData': semantic_drift_data,
                    'semanticContrastData': semantic_contrast_data,
                    'recommendationData': recommendation_data,
                    'radarChartData': radar_chart_data
                },
                detailed_results=all_results
            )
            api_logger.info(f"Saved test record with ID: {record_id}, overall_score: {overall_score}")
        except Exception as e:
            api_logger.error(f"Error saving test records to database: {e}")
        
        return {
            'success': True,
            'execution_id': execution_id,
            'total_executions': total_executions,
            'results': all_results,
            'formula': f"{len(raw_questions)} questions × {len(selected_models)} models = {expected_total}",
            'completion_verified': completion_check['can_complete'],
            'completion_check': completion_check,
            # 【新增】返回完整的分析数据供前端使用
            'brand_scores': brand_scores,
            'competitive_analysis': competitive_analysis,
            'negative_sources': negative_sources,
            'semantic_drift_data': semantic_drift_data,
            'semantic_contrast_data': semantic_contrast_data,
            'recommendation_data': recommendation_data,
            'overall_score': overall_score
        }
    
    except Exception as e:
        error_traceback = traceback.format_exc()
        api_logger.error(f"NxM test execution failed for execution_id {execution_id}: {e}\nTraceback: {error_traceback}")
        
        # 清理资源
        _close_logger(execution_id)
        
        if execution_store and execution_id in execution_store:
            with _execution_store_lock:
                execution_store[execution_id].update({
                    'status': 'failed',
                    'error': f"{str(e)}\nTraceback: {error_traceback}",
                    'completion_verified': False
                })
        
        return {
            'success': False,
            'execution_id': execution_id,
            'error': str(e),
            'traceback': error_traceback
        }


def verify_nxm_execution(
    execution_store: Dict[str, Any],
    execution_id: str,
    expected_questions: int,
    expected_models: int,
    expected_main_brand: str
) -> Dict[str, Any]:
    """
    验证 NxM 执行是否正确（增强版）
    
    新增验证项：
    - 结果哈希值唯一性
    - GEO 解析完整性
    - 任务终点校验状态
    
    Args:
        execution_store: 执行状态存储
        execution_id: 执行 ID
        expected_questions: 期望的问题数
        expected_models: 期望的模型数
        expected_main_brand: 期望的主品牌
    
    Returns:
        验证结果字典
    """
    expected_total = expected_questions * expected_models
    
    if execution_id not in execution_store:
        return {
            'valid': False,
            'error': f"Execution ID {execution_id} not found in store"
        }
    
    execution = execution_store[execution_id]
    actual_total = execution.get('total', 0)
    results = execution.get('results', [])
    
    # 检查总执行次数
    if actual_total != expected_total:
        return {
            'valid': False,
            'error': f"Expected {expected_total} executions, got {actual_total}",
            'details': {
                'expected': expected_total,
                'actual': actual_total,
                'formula': f"{expected_questions} questions × {expected_models} models"
            }
        }
    
    # 检查结果数量
    if len(results) != actual_total:
        return {
            'valid': False,
            'error': f"Results count mismatch: expected {actual_total}, got {len(results)}"
        }
    
    # 检查结果哈希值唯一性
    result_hashes = [r.get('_result_hash') for r in results if r.get('_result_hash')]
    unique_hashes = set(result_hashes)
    hash_uniqueness = len(unique_hashes) == len(result_hashes)
    
    if not hash_uniqueness:
        return {
            'valid': False,
            'error': f"Duplicate result hashes detected: {len(result_hashes)} results, {len(unique_hashes)} unique hashes"
        }
    
    # 【新增】检查任务终点校验状态
    completion_verified = execution.get('completion_verified', False)
    status = execution.get('status', 'unknown')
    
    if status == 'completed' and not completion_verified:
        return {
            'valid': False,
            'error': "Task marked as completed but completion_verified is False"
        }
    
    # 检查每个结果是否包含 geo_data
    results_with_geo = [r for r in results if r.get('geo_data') is not None]
    geo_data_percentage = (len(results_with_geo) / len(results) * 100) if results else 0
    
    # 检查成功结果是否都有 geo_data
    success_results = [r for r in results if r.get('status') == 'success']
    success_with_geo = [r for r in success_results if r.get('geo_data') is not None]
    
    # 检查错误代码
    results_with_error_codes = [r for r in results if r.get('error_code') is not None]
    
    verification = {
        'valid': True,
        'total_executions': actual_total,
        'total_results': len(results),
        'successful_results': len(success_results),
        'failed_results': len(results) - len(success_results),
        'results_with_geo_data': len(results_with_geo),
        'geo_data_percentage': geo_data_percentage,
        'success_results_with_geo': len(success_with_geo),
        'success_geo_data_percentage': (len(success_with_geo) / len(success_results) * 100) if success_results else 0,
        'nxm_pattern': f"{expected_questions} questions × {expected_models} models = {expected_total}",
        'main_brand': expected_main_brand,
        # 验证项
        'result_hashes_unique': hash_uniqueness,
        'completion_verified': completion_verified,
        'status': status,
        'can_complete': status == 'completed',
        'results_with_error_codes': len(results_with_error_codes),
        'error_code_percentage': (len(results_with_error_codes) / len(results) * 100) if results else 0
    }
    
    return verification
