"""
诊断链路追踪日志工具

提供统一的日志记录函数，用于追踪诊断执行的完整链路

使用方法:
    from wechat_backend.diagnosis_trace_logger import (
        log_diagnosis_step,
        log_diagnosis_snapshot
    )
    
    # 记录诊断步骤
    log_diagnosis_step("START", execution_id, {...})
    log_diagnosis_step("AI_COMPLETE", execution_id, {...})
    
    # 记录数据快照
    log_diagnosis_snapshot("DB_SAVE", execution_id, results)
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger('wechat_backend.diagnosis_trace')


# 诊断步骤枚举
DIAGNOSIS_STEPS = {
    "START": "诊断开始",
    "PARAMS_VALIDATED": "参数验证完成",
    "REPORT_CREATED": "报告记录创建",
    "NXM_STARTED": "NxM 执行器启动",
    "AI_START": "AI 调用开始",
    "AI_COMPLETE": "AI 调用完成",
    "RESULTS_VALIDATED": "结果验证完成",
    "DB_SAVED": "数据库保存完成",
    "BACKGROUND_ANALYSIS": "后台分析开始",
    "ANALYSIS_COMPLETE": "后台分析完成",
    "REPORT_AGGREGATING": "报告聚合开始",
    "ANALYSIS_SAVED": "分析数据保存",
    "SNAPSHOT_CREATED": "快照创建完成",
    "COMPLETED": "诊断完成",
    "FAILED": "诊断失败"
}


def log_diagnosis_step(
    step: str,
    execution_id: str,
    data: Optional[Dict[str, Any]] = None,
    level: str = "info"
):
    """
    记录诊断步骤日志
    
    参数:
        step: 步骤名称（如 "START", "AI_COMPLETE"）
        execution_id: 执行 ID
        data: 附加数据
        level: 日志级别（debug/info/warning/error）
    
    示例:
        log_diagnosis_step("START", execution_id, {
            "brand": "趣车良品",
            "questions_count": 1,
            "models_count": 1
        })
    """
    step_name = DIAGNOSIS_STEPS.get(step, step)
    timestamp = datetime.now().isoformat()
    
    log_data = {
        "step": step,
        "step_name": step_name,
        "execution_id": execution_id,
        "timestamp": timestamp,
        "data": data or {}
    }
    
    log_message = f"[DIAGNOSIS-{step}] execution_id={execution_id}, data={json.dumps(data, ensure_ascii=False) if data else '{}'}"
    
    if level == "debug":
        logger.debug(log_message)
    elif level == "warning":
        logger.warning(log_message)
    elif level == "error":
        logger.error(log_message)
    else:
        logger.info(log_message)


def log_diagnosis_snapshot(
    snapshot_type: str,
    execution_id: str,
    snapshot_data: Dict[str, Any]
):
    """
    记录数据快照日志（用于关键节点数据验证）
    
    参数:
        snapshot_type: 快照类型（如 "API_INPUT", "AI_OUTPUT", "DB_RESULT"）
        execution_id: 执行 ID
        snapshot_data: 快照数据
    
    示例:
        log_diagnosis_snapshot("AI_OUTPUT", execution_id, {
            "results_count": 1,
            "first_result_brand": "趣车良品",
            "first_result_tokens": 50,
            "success_count": 1
        })
    """
    timestamp = datetime.now().isoformat()
    
    # 简化数据以便日志阅读
    simplified_data = _simplify_snapshot(snapshot_data)
    
    log_message = (
        f"[DIAGNOSIS-SNAPSHOT-{snapshot_type}] "
        f"execution_id={execution_id}, "
        f"data={json.dumps(simplified_data, ensure_ascii=False)}"
    )
    
    logger.info(log_message)


def _simplify_snapshot(data: Dict[str, Any], max_depth: int = 3, max_str_len: int = 100) -> Dict[str, Any]:
    """
    简化快照数据，便于日志阅读
    
    规则:
    1. 截断过长的字符串
    2. 限制嵌套深度
    3. 限制列表长度
    """
    if not isinstance(data, dict):
        return data
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and len(value) > max_str_len:
            result[key] = value[:max_str_len] + "..."
        elif isinstance(value, dict) and max_depth > 0:
            result[key] = _simplify_snapshot(value, max_depth - 1, max_str_len)
        elif isinstance(value, list) and len(value) > 10:
            result[key] = value[:10] + [..., f"... ({len(value) - 10} more items)"]
        else:
            result[key] = value
    
    return result


def log_diagnosis_error(
    step: str,
    execution_id: str,
    error: Exception,
    context: Optional[Dict[str, Any]] = None
):
    """
    记录诊断错误日志
    
    参数:
        step: 错误发生的步骤
        execution_id: 执行 ID
        error: 异常对象
        context: 上下文数据
    """
    error_data = {
        "step": step,
        "execution_id": execution_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context or {}
    }
    
    logger.error(
        f"[DIAGNOSIS-ERROR] execution_id={execution_id}, "
        f"step={step}, "
        f"error={type(error).__name__}: {str(error)}, "
        f"context={json.dumps(context, ensure_ascii=False) if context else '{}'}",
        exc_info=True
    )


def log_diagnosis_validation(
    validation_type: str,
    execution_id: str,
    passed: bool,
    details: Dict[str, Any]
):
    """
    记录验证日志
    
    参数:
        validation_type: 验证类型（如 "BRAND_FIELD", "TOKENS_USED", "RESULT_COUNT"）
        execution_id: 执行 ID
        passed: 是否通过
        details: 验证详情
    """
    status = "✅" if passed else "❌"
    
    log_message = (
        f"[DIAGNOSIS-VALIDATION-{validation_type}] "
        f"execution_id={execution_id}, "
        f"status={status}, "
        f"details={json.dumps(details, ensure_ascii=False)}"
    )
    
    if passed:
        logger.info(log_message)
    else:
        logger.warning(log_message)


# 便捷函数：验证结果数据完整性
def validate_results_before_save(
    execution_id: str,
    results: List[Dict[str, Any]]
) -> bool:
    """
    验证结果数据完整性（保存前强制验证）
    
    返回:
        bool: 验证是否通过
    
    异常:
        ValueError: 验证失败时抛出
    """
    if not results:
        log_diagnosis_validation(
            "RESULTS_EMPTY",
            execution_id,
            passed=False,
            details={"message": "结果列表为空"}
        )
        raise ValueError(f"[{execution_id}] 结果列表不能为空")
    
    errors = []
    warnings = []
    
    for i, r in enumerate(results):
        # 必要字段检查
        required_fields = ['brand', 'question', 'model', 'response']
        for field in required_fields:
            if field not in r:
                errors.append(f"结果[{i}]: 缺少字段 '{field}'")
            elif field == 'brand' and not r.get(field):
                errors.append(f"结果[{i}]: 字段 '{field}' 为空")
        
        # tokens_used 检查（P1 修复验证）
        if 'tokens_used' not in r:
            warnings.append(f"结果[{i}]: 缺少 'tokens_used' 字段")
        elif r.get('tokens_used', 0) == 0:
            warnings.append(f"结果[{i}]: tokens_used=0")
    
    # 记录验证结果
    validation_details = {
        "total_results": len(results),
        "errors_count": len(errors),
        "warnings_count": len(warnings),
        "errors": errors[:5],  # 最多显示 5 个错误
        "warnings": warnings[:5]  # 最多显示 5 个警告
    }
    
    if errors:
        log_diagnosis_validation(
            "RESULTS_INTEGRITY",
            execution_id,
            passed=False,
            details=validation_details
        )
        raise ValueError(f"[{execution_id}] 结果数据验证失败：{errors[:3]}")
    
    if warnings:
        log_diagnosis_validation(
            "RESULTS_INTEGRITY",
            execution_id,
            passed=True,
            details=validation_details
        )
    else:
        log_diagnosis_validation(
            "RESULTS_INTEGRITY",
            execution_id,
            passed=True,
            details=validation_details
        )
    
    return True


# 便捷函数：验证数据库保存结果
def validate_db_save_result(
    execution_id: str,
    expected_count: int,
    db_path: str = "backend_python/database.db"
) -> bool:
    """
    验证数据库保存结果
    
    返回:
        bool: 验证是否通过
    """
    import sqlite3
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询实际保存数量
        cursor.execute("""
            SELECT COUNT(*) as count, 
                   SUM(CASE WHEN brand = '' OR brand IS NULL THEN 1 ELSE 0 END) as empty_brand_count,
                   SUM(CASE WHEN tokens_used = 0 THEN 1 ELSE 0 END) as zero_tokens_count
            FROM diagnosis_results 
            WHERE execution_id = ?
        """, (execution_id,))
        
        row = cursor.fetchone()
        actual_count = row[0]
        empty_brand_count = row[1]
        zero_tokens_count = row[2]
        
        conn.close()
        
        # 验证
        details = {
            "expected_count": expected_count,
            "actual_count": actual_count,
            "empty_brand_count": empty_brand_count,
            "zero_tokens_count": zero_tokens_count
        }
        
        if actual_count != expected_count:
            log_diagnosis_validation(
                "DB_SAVE_COUNT",
                execution_id,
                passed=False,
                details=details
            )
            return False
        
        if empty_brand_count > 0:
            log_diagnosis_validation(
                "DB_BRAND_FIELD",
                execution_id,
                passed=False,
                details=details
            )
            return False
        
        log_diagnosis_validation(
            "DB_SAVE_COMPLETE",
            execution_id,
            passed=True,
            details=details
        )
        return True
        
    except Exception as e:
        log_diagnosis_error(
            "DB_VALIDATION",
            execution_id,
            e,
            {"expected_count": expected_count}
        )
        return False
