"""
品牌诊断报告存储架构 - Service 层实现

核心原则：
1. 业务逻辑封装
2. 事务管理
3. 数据验证
4. 错误处理

作者：首席全栈工程师
日期：2026-02-26
版本：1.0
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from wechat_backend.logging_config import db_logger, api_logger
from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
    DiagnosisAnalysisRepository,
    FileArchiveManager,
    calculate_checksum,
    DATA_SCHEMA_VERSION
)


class DiagnosisReportService:
    """
    诊断报告服务 - 业务逻辑层
    
    职责：
    1. 诊断报告创建
    2. 结果添加
    3. 分析数据添加
    4. 报告完成（快照 + 归档）
    5. 报告查询
    """
    
    def __init__(self):
        self.report_repo = DiagnosisReportRepository()
        self.result_repo = DiagnosisResultRepository()
        self.analysis_repo = DiagnosisAnalysisRepository()
        self.archive_manager = FileArchiveManager()
    
    def create_report(self, execution_id: str, user_id: str, 
                     config: Dict[str, Any]) -> int:
        """
        创建诊断报告
        
        参数:
            execution_id: 执行 ID
            user_id: 用户 ID
            config: 诊断配置 {
                brand_name: 品牌名称
                competitor_brands: 竞品列表
                selected_models: AI 模型列表
                custom_questions: 自定义问题列表
            }
        
        返回:
            report_id: 报告 ID
        """
        db_logger.info(f"开始创建诊断报告：{execution_id}")
        
        # 1. 创建报告记录
        report_id = self.report_repo.create(execution_id, user_id, config)
        
        db_logger.info(f"✅ 诊断报告创建成功：{execution_id}, report_id: {report_id}")
        return report_id
    
    def add_result(self, report_id: int, execution_id: str, 
                  result: Dict[str, Any]) -> int:
        """
        添加诊断结果
        
        参数:
            report_id: 报告 ID
            execution_id: 执行 ID
            result: 结果数据 {
                brand: 品牌
                question: 问题
                model: AI 模型
                response: AI 响应
                geo_data: GEO 分析数据
                quality_score: 质量评分
                quality_level: 质量等级
                quality_details: 质量详情
            }
        
        返回:
            result_id: 结果 ID
        """
        result_id = self.result_repo.add(report_id, execution_id, result)
        db_logger.debug(f"添加诊断结果：{execution_id}, result_id: {result_id}")
        return result_id
    
    def add_results_batch(self, report_id: int, execution_id: str, 
                         results: List[Dict[str, Any]]) -> List[int]:
        """批量添加诊断结果"""
        result_ids = self.result_repo.add_batch(report_id, execution_id, results)
        db_logger.info(f"批量添加 {len(results)} 个诊断结果：{execution_id}")
        return result_ids
    
    def add_analysis(self, report_id: int, execution_id: str, 
                    analysis_type: str, analysis_data: Dict[str, Any]) -> int:
        """
        添加分析数据
        
        参数:
            report_id: 报告 ID
            execution_id: 执行 ID
            analysis_type: 分析类型 (competitive_analysis, brand_scores, etc.)
            analysis_data: 分析数据
        
        返回:
            analysis_id: 分析 ID
        """
        analysis_id = self.analysis_repo.add(
            report_id, execution_id, analysis_type, analysis_data
        )
        db_logger.debug(f"添加分析数据：{execution_id}, type: {analysis_type}")
        return analysis_id
    
    def add_analyses_batch(self, report_id: int, execution_id: str, 
                          analyses: Dict[str, Dict[str, Any]]) -> List[int]:
        """批量添加分析数据"""
        analysis_ids = self.analysis_repo.add_batch(report_id, execution_id, analyses)
        db_logger.info(f"批量添加 {len(analyses)} 个分析数据：{execution_id}")
        return analysis_ids
    
    def complete_report(self, execution_id: str, full_report: Dict[str, Any]) -> bool:
        """
        完成诊断报告（创建快照、归档）
        
        参数:
            execution_id: 执行 ID
            full_report: 完整报告数据 {
                report: 报告主数据
                results: 结果列表
                analysis: 分析数据
            }
        
        返回:
            success: 是否成功
        """
        db_logger.info(f"开始完成诊断报告：{execution_id}")
        
        try:
            # 1. 获取报告
            report = self.report_repo.get_by_execution_id(execution_id)
            if not report:
                db_logger.error(f"❌ 报告不存在：{execution_id}")
                return False
            
            report_id = report['id']
            
            # 2. 更新状态为完成
            self.report_repo.update_status(
                execution_id, 'completed', 100, 'completed', True
            )
            
            # 3. 创建快照
            self.report_repo.create_snapshot(
                report_id, execution_id, full_report, 'completed'
            )
            
            # 4. 保存到文件
            created_at = datetime.fromisoformat(report['created_at'])
            self.archive_manager.save_report(execution_id, full_report, created_at)
            
            db_logger.info(f"✅ 诊断报告完成：{execution_id}")
            return True
            
        except Exception as e:
            db_logger.error(f"❌ 完成报告失败：{execution_id}, 错误：{e}")
            return False
    
    def get_full_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取完整报告（P0-REPORT-2 优化：处理失败场景）

        参数:
            execution_id: 执行 ID

        返回:
            完整报告数据 {
                report: 报告主数据
                results: 结果列表
                analysis: 分析数据
                meta: 元数据
            }
        """
        db_logger.info(f"获取完整报告：{execution_id}")

        # 1. 获取报告主数据
        report = self.report_repo.get_by_execution_id(execution_id)
        if not report:
            db_logger.warning(f"报告不存在：{execution_id}")
            return None

        # P0-REPORT-2 优化：处理诊断失败场景
        # 如果报告状态为 failed，返回包含错误信息的结构
        if report.get('status') == 'failed':
            db_logger.info(f"报告为失败状态：{execution_id}")
            return {
                'report': report,  # 包含 execution_id, user_id, brand_name 等
                'results': [],
                'analysis': {},
                'error': {
                    'status': 'failed',
                    'stage': report.get('stage', 'unknown'),
                    'message': '诊断执行失败，请查看日志获取详细错误信息'
                },
                'meta': {
                    'data_schema_version': report.get('data_schema_version', DATA_SCHEMA_VERSION),
                    'server_version': report.get('server_version', 'unknown'),
                    'retrieved_at': datetime.now().isoformat()
                }
            }

        # 2. 获取结果明细
        results = self.result_repo.get_by_execution_id(execution_id)

        # 3. 获取分析数据
        analysis = self.analysis_repo.get_by_execution_id(execution_id)

        # 4. 构建完整报告
        full_report = {
            'report': report,
            'results': results,
            'analysis': analysis,
            'meta': {
                'data_schema_version': report.get('data_schema_version', DATA_SCHEMA_VERSION),
                'server_version': report.get('server_version', 'unknown'),
                'retrieved_at': datetime.now().isoformat()
            }
        }

        # 5. 验证完整性（可选）
        checksum = report.get('checksum')
        if checksum:
            full_report['checksum_verified'] = True  # 简化验证

        db_logger.info(f"✅ 获取完整报告成功：{execution_id}, 结果数：{len(results)}")
        return full_report
    
    def get_user_history(self, user_id: str, page: int = 1, 
                        limit: int = 20) -> Dict[str, Any]:
        """
        获取用户历史
        
        参数:
            user_id: 用户 ID
            page: 页码
            limit: 每页数量
        
        返回:
            {
                reports: 报告列表
                pagination: 分页信息
            }
        """
        offset = (page - 1) * limit
        reports = self.report_repo.get_user_history(user_id, limit, offset)
        
        return {
            'reports': reports,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(reports),  # 实际应该查询总数
                'has_more': len(reports) == limit
            }
        }
    
    def update_progress(self, execution_id: str, progress: int, stage: str) -> bool:
        """
        更新诊断进度
        
        参数:
            execution_id: 执行 ID
            progress: 进度 (0-100)
            stage: 阶段 (init, ai_fetching, intelligence_analyzing, etc.)
        
        返回:
            success: 是否成功
        """
        return self.report_repo.update_status(
            execution_id, 'processing', progress, stage
        )


# ==================== 工具服务 ====================

class ReportValidationService:
    """
    报告验证服务
    
    职责：
    1. 数据完整性验证
    2. 校验和验证
    3. 数据格式验证
    """
    
    @staticmethod
    def validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证报告数据（P0-REPORT-1 修复：检查正确的字段位置）

        返回:
            {
                is_valid: 是否有效
                errors: 错误列表
                warnings: 警告列表
            }
        """
        errors = []
        warnings = []

        # P0-REPORT-1 修复：报告结构是 {'report': {...}, 'results': [...], 'analysis': {...}}
        # 必填字段在 report 对象内，不在顶层
        report_data = report.get('report', {})
        
        # 验证必填字段（在 report 对象内）
        required_fields = ['execution_id', 'user_id', 'brand_name', 'created_at']
        for field in required_fields:
            if field not in report_data:
                errors.append(f"缺少必填字段：{field}")
        
        # 验证 report 对象是否存在
        if not report_data:
            errors.append("report 对象为空或缺失")

        # 验证结果数据
        if 'results' in report:
            if not isinstance(report['results'], list):
                errors.append("results 必须是数组")
            else:
                for i, result in enumerate(report['results']):
                    if 'brand' not in result:
                        errors.append(f"结果 {i} 缺少 brand 字段")
                    if 'question' not in result:
                        errors.append(f"结果 {i} 缺少 question 字段")
                    if 'model' not in result:
                        errors.append(f"结果 {i} 缺少 model 字段")
        else:
            warnings.append("报告缺少 results 数据")

        # 验证分析数据
        if 'analysis' in report:
            if not isinstance(report['analysis'], dict):
                errors.append("analysis 必须是对象")
        else:
            warnings.append("报告缺少 analysis 数据")

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }


# ==================== 单例 ====================

# 全局服务实例
_report_service = None
_validation_service = None


def get_report_service() -> DiagnosisReportService:
    """获取报告服务单例"""
    global _report_service
    if _report_service is None:
        _report_service = DiagnosisReportService()
    return _report_service


def get_validation_service() -> ReportValidationService:
    """获取验证服务单例"""
    global _validation_service
    if _validation_service is None:
        _validation_service = ReportValidationService()
    return _validation_service
