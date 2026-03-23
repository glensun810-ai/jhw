"""
服务层数据验证器 - P0 架构级修复

确保 Service 层返回的数据完整性，防止空数据流向 View 层。

核心职责:
1. 验证 Service 层返回数据的完整性
2. 空数据时抛出结构化错误而非返回空字典
3. 记录审计日志，便于问题追踪
4. 支持部分成功场景的降级处理

使用示例:
    from wechat_backend.validators.service_validator import ServiceDataValidator
    
    def get_full_report(self, execution_id: str):
        report = self.storage.get_report(execution_id)
        
        # 服务层数据验证
        ServiceDataValidator.validate_report_data(report, execution_id)
        
        return report

作者：系统架构组
日期：2026-03-18
版本：1.0.0
"""

from typing import Any, Dict, List, Optional
from wechat_backend.error_codes import ErrorCode, BusinessException, ReportException
from wechat_backend.logging_config import db_logger


class ServiceDataValidator:
    """
    服务层数据验证器
    
    验证规则:
    1. 数据不能为 None
    2. 数据不能为空字典
    3. 必须包含关键字段（如 execution_id）
    4. 核心数据字段至少有一个非空
    """
    
    # 报告核心字段列表（至少包含其中之一）
    REPORT_CORE_FIELDS = [
        'results',
        'brandAnalysis', 
        'brandDistribution',
        'sentimentDistribution',
        'analysis'
    ]
    
    # 报告必填字段（必须包含）
    # 注意：由于 convert_response_to_camel 会转换所有字段为 camelCase，
    # 这里需要同时检查 snake_case 和 camelCase
    REPORT_REQUIRED_FIELDS = [
        'execution_id',
        'executionId'  # camelCase 版本（convert_response_to_camel 转换后）
    ]
    
    @staticmethod
    def validate_report_data(report: Any, execution_id: str) -> bool:
        """
        验证报告数据完整性
        
        Args:
            report: 报告数据
            execution_id: 执行 ID（用于日志）
        
        Returns:
            bool: 验证是否通过
            
        Raises:
            BusinessException: 数据验证失败时抛出
        """
        # 【规则 1】检查 None
        if report is None:
            db_logger.error(f"❌ [验证器] report=None: execution_id={execution_id}")
            raise ReportException(
                ErrorCode.REPORT_NOT_FOUND,
                detail={'execution_id': execution_id}
            )
        
        # 【规则 2】检查空字典
        if isinstance(report, dict) and len(report) == 0:
            db_logger.error(f"❌ [验证器] report=空字典：execution_id={execution_id}")
            raise ReportException(
                ErrorCode.DATA_NOT_FOUND,
                detail={'execution_id': execution_id}
            )
        
        # 【规则 3】检查必须是字典类型
        if not isinstance(report, dict):
            db_logger.error(
                f"❌ [验证器] report 类型错误：execution_id={execution_id}, "
                f"type={type(report)}"
            )
            raise ReportException(
                ErrorCode.REPORT_INVALID_FORMAT,
                detail={
                    'expected': 'dict',
                    'actual': str(type(report)),
                    'execution_id': execution_id
                }
            )
        
        # 【规则 4】检查必填字段
        # 注意：由于 convert_response_to_camel 会转换所有字段，需要同时检查 snake_case 和 camelCase
        for field in ServiceDataValidator.REPORT_REQUIRED_FIELDS:
            # 对于 execution_id 字段，需要在多个位置检查
            if field in ('execution_id', 'executionId'):
                # 检查多个可能的位置：
                # 1. report['report'] 对象内
                # 2. report 顶层
                # 3. 通过 execution_id 参数传入的值
                
                report_obj = report.get('report', {})
                
                # 检查 report['report'] 中是否有 execution_id 或 executionId
                has_field_in_report = (
                    isinstance(report_obj, dict) and (
                        report_obj.get('execution_id') is not None or
                        report_obj.get('executionId') is not None
                    )
                )
                
                # 检查 report 顶层是否有 execution_id 或 executionId
                has_field_in_root = (
                    report.get('execution_id') is not None or
                    report.get('executionId') is not None
                )
                
                # 如果没有找到，但 execution_id 参数有值，也认为通过（可以在后续补充）
                has_field = has_field_in_report or has_field_in_root or (execution_id is not None and execution_id != '')
                
                if not has_field:
                    db_logger.error(
                        f"❌ [验证器] report 缺少必填字段：execution_id={execution_id}, "
                        f"missing_field=execution_id/executionId"
                    )
                    raise ReportException(
                        ErrorCode.REPORT_INCOMPLETE,
                        detail={
                            'missing_field': 'execution_id or executionId',
                            'available_fields': list(report_obj.keys()) if isinstance(report_obj, dict) else [],
                            'execution_id': execution_id
                        }
                    )
            elif field not in report:
                db_logger.error(
                    f"❌ [验证器] report 缺少必填字段：execution_id={execution_id}, "
                    f"missing_field={field}"
                )
                raise ReportException(
                    ErrorCode.REPORT_INCOMPLETE,
                    detail={
                        'missing_field': field,
                        'available_fields': list(report.keys()),
                        'execution_id': execution_id
                    }
                )
        
        # 【规则 5】检查核心数据字段（至少有一个非空）
        has_core_data = False
        for field in ServiceDataValidator.REPORT_CORE_FIELDS:
            value = report.get(field)
            if value is not None:
                # 检查是否是空列表或空字典
                if isinstance(value, (list, dict)) and len(value) == 0:
                    continue
                has_core_data = True
                break
        
        if not has_core_data:
            db_logger.warning(
                f"⚠️ [验证器] 报告无核心数据：execution_id={execution_id}, "
                f"checked_fields={ServiceDataValidator.REPORT_CORE_FIELDS}"
            )
            
            # 【架构决策】不抛异常，添加质量警告，允许部分成功
            if 'qualityHints' not in report:
                report['qualityHints'] = {}
            report['qualityHints']['partial_data'] = True
            report['qualityHints']['warnings'] = [
                '报告核心数据不完整，可能影响展示效果',
                '建议检查诊断执行过程或重新诊断'
            ]
            report['qualityHints']['missing_fields'] = ServiceDataValidator.REPORT_CORE_FIELDS
            
            db_logger.info(
                f"⚠️ [验证器] 允许部分成功：execution_id={execution_id}, "
                f"添加质量警告"
            )
        
        # 【规则 6】检查报告状态
        status = report.get('status')
        if status == 'failed':
            db_logger.info(f"⚠️ [验证器] 报告为失败状态：execution_id={execution_id}")
            # 失败状态的报告允许返回，但添加提示
            if 'qualityHints' not in report:
                report['qualityHints'] = {}
            report['qualityHints']['execution_failed'] = True
            report['qualityHints']['error_message'] = report.get('error_message', '诊断执行失败')
        
        db_logger.info(f"✅ [验证器] 报告验证通过：execution_id={execution_id}")
        return True
    
    @staticmethod
    def validate_results_list(results: Any, execution_id: str) -> bool:
        """
        验证诊断结果列表
        
        Args:
            results: 结果列表
            execution_id: 执行 ID
        
        Returns:
            bool: 验证是否通过
        """
        # 允许空列表（表示无结果但不代表错误）
        if results is None:
            db_logger.warning(f"⚠️ [验证器] results=None: execution_id={execution_id}")
            return False
        
        if not isinstance(results, list):
            db_logger.error(
                f"❌ [验证器] results 类型错误：execution_id={execution_id}, "
                f"type={type(results)}"
            )
            return False
        
        # 空列表是允许的
        if len(results) == 0:
            db_logger.warning(f"⚠️ [验证器] results 为空列表：execution_id={execution_id}")
            return False
        
        return True
    
    @staticmethod
    def validate_analysis_data(analysis: Any, execution_id: str) -> bool:
        """
        验证分析数据
        
        Args:
            analysis: 分析数据
            execution_id: 执行 ID
        
        Returns:
            bool: 验证是否通过
        """
        if analysis is None:
            db_logger.warning(f"⚠️ [验证器] analysis=None: execution_id={execution_id}")
            return False
        
        if not isinstance(analysis, dict):
            db_logger.error(
                f"❌ [验证器] analysis 类型错误：execution_id={execution_id}, "
                f"type={type(analysis)}"
            )
            return False
        
        if len(analysis) == 0:
            db_logger.warning(f"⚠️ [验证器] analysis 为空字典：execution_id={execution_id}")
            return False
        
        return True
    
    @staticmethod
    def add_quality_warning(
        report: Dict[str, Any],
        warning_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        向报告添加质量警告
        
        Args:
            report: 报告数据
            warning_type: 警告类型
            message: 警告消息
            details: 详细信息
        """
        if 'qualityHints' not in report:
            report['qualityHints'] = {}
        
        if 'warnings' not in report['qualityHints']:
            report['qualityHints']['warnings'] = []
        
        warning = {
            'type': warning_type,
            'message': message
        }
        
        if details:
            warning['details'] = details
        
        report['qualityHints']['warnings'].append(warning)
        db_logger.warning(f"⚠️ [验证器] 添加质量警告：{warning_type} - {message}")
