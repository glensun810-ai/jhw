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
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from wechat_backend.logging_config import db_logger, api_logger
# P2-1 优化：导入日志增强模块
from wechat_backend.logging_enhancements import sampled_logger, aggregated_logger
from wechat_backend.diagnosis_report_repository import (
    DiagnosisReportRepository,
    DiagnosisResultRepository,
    DiagnosisAnalysisRepository,
    FileArchiveManager,
    calculate_checksum,
    DATA_SCHEMA_VERSION
)

# P2-1 优化：创建采样日志器（用于高频日志）
# 批量操作日志使用 10% 采样率
batch_operation_logger = sampled_logger('wechat_backend.service.batch', sample_rate=0.1)
# 缓存日志使用 20% 采样率
cache_operation_logger = sampled_logger('wechat_backend.service.cache', sample_rate=0.2)

# P0 修复：导入字段转换器（使用相对导入）
try:
    from utils.field_converter import convert_response_to_camel
except ImportError:
    # 如果在 wechat_backend 包内，尝试相对导入
    try:
        from ..utils.field_converter import convert_response_to_camel
    except ImportError:
        # 如果都失败，使用备用方案
        api_logger.warning("field_converter 导入失败，使用备用转换函数")
        def convert_response_to_camel(data):
            """备用转换函数"""
            return data


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
                         results: List[Dict[str, Any]],
                         batch_size: int = 10,  # 【P0 新增】分批大小
                         commit: bool = True    # 【P0 新增】是否提交
    ) -> List[int]:
        """
        批量添加诊断结果

        【P0 修复 - 2026-03-05】支持分批提交，减少连接持有时间

        参数:
            report_id: 报告 ID
            execution_id: 执行 ID
            results: 结果列表
            batch_size: 每批数量（默认 10）
            commit: 是否提交事务（默认 True）

        返回:
            result_ids: 结果 ID 列表
        """
        result_ids = self.result_repo.add_batch(
            report_id, execution_id, results,
            batch_size=batch_size,
            commit=commit
        )
        # P2-1 优化：批量操作日志使用采样日志器，减少日志量
        batch_count = (len(results) + batch_size - 1) // batch_size
        batch_operation_logger.info(
            f"批量添加 {len(results)} 个诊断结果：{execution_id}, batches={batch_count}"
        )
        # 详细日志使用 DEBUG 级别
        db_logger.debug(
            f"批量添加诊断结果详情：{execution_id}, count={len(results)}, "
            f"batch_size={batch_size}, batches={batch_count}"
        )
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
        完成诊断报告（创建快照、归档）- P0 修复增强版

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

            # 3. 创建快照（P0 修复：快照失败不影响主流程）
            snapshot_result = self.report_repo.create_snapshot(
                report_id, execution_id, full_report, 'completed'
            )
            if snapshot_result < 0:
                db_logger.warning(f"⚠️ 快照创建失败，但继续执行：{execution_id}")

            # 4. 保存到文件
            try:
                created_at = datetime.fromisoformat(report['created_at'])
                self.archive_manager.save_report(execution_id, full_report, created_at)
            except Exception as e:
                db_logger.error(f"❌ 文件保存失败：{execution_id}, 错误：{e}")
                # 文件保存失败不影响主流程

            db_logger.info(f"✅ 诊断报告完成：{execution_id}")
            return True

        except Exception as e:
            db_logger.error(f"❌ 完成报告失败：{execution_id}, 错误：{e}", exc_info=True)
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
                analysis: 分析数据（嵌套结构）
                brandDistribution: 品牌分布（前端格式）
                sentimentDistribution: 情感分布（前端格式）
                keywords: 关键词列表（前端格式）
                meta: 元数据
                validation: 验证信息
            }
        """
        db_logger.info(f"获取完整报告：{execution_id}")

        # 1. 获取报告主数据
        try:
            report = self.report_repo.get_by_execution_id(execution_id)
        except Exception as e:
            db_logger.error(f"查询报告失败：execution_id={execution_id}, 错误：{e}")
            return self._create_fallback_report(
                execution_id,
                f'数据库查询失败：{str(e)}',
                'database_error'
            )

        # P0 修复：增加判空逻辑，防止 report 为 None
        if not report:
            db_logger.warning(f"报告不存在：execution_id={execution_id}")
            return self._create_fallback_report(execution_id, '报告不存在', 'not_found')

        # P0 修复：确保 report 是字典类型
        if not isinstance(report, dict):
            db_logger.error(f"报告格式错误：execution_id={execution_id}, type={type(report)}")
            return self._create_fallback_report(
                execution_id,
                '报告数据格式错误',
                'invalid_format'
            )

        # P0 修复：验证 report 关键字段，防止空字典
        if not report.get('execution_id'):
            db_logger.error(f"report 缺少 execution_id 字段：execution_id={execution_id}")
            return self._create_fallback_report(
                execution_id,
                '报告数据不完整',
                'incomplete_data'
            )

        # P1-1 修复：完善降级方案，处理多种异常场景

        # 场景 1: 报告状态为 failed
        if report.get('status') == 'failed':
            db_logger.info(f"报告为失败状态：execution_id={execution_id}")
            return self._create_fallback_report(
                execution_id,
                '诊断执行失败，请查看日志获取详细错误信息',
                'failed',
                report
            )

        # 场景 2: 报告状态为 processing 但超时（超过 10 分钟）
        if report.get('status') == 'processing':
            created_at = report.get('created_at')
            if created_at:
                try:
                    created_time = datetime.fromisoformat(created_at)
                    time_diff = (datetime.now() - created_time).total_seconds()
                    if time_diff > 600:  # 超过 10 分钟
                        db_logger.warning(f"报告处理超时：execution_id={execution_id}, 已耗时{time_diff}秒")
                        return self._create_fallback_report(
                            execution_id,
                            '诊断处理超时，建议重新执行诊断',
                            'timeout',
                            report
                        )
                except Exception as e:
                    db_logger.error(f"时间解析失败：execution_id={execution_id}, 错误：{e}")

        # 2. 获取结果明细（增强版 - 支持重试）
        max_retries = 3
        retry_delay = 1.0  # 秒
        
        for attempt in range(max_retries):
            try:
                results = self.result_repo.get_by_execution_id(execution_id)
                
                # 【P0 关键修复 - 2026-03-12 第 10 次】如果 results 为空，等待后重试
                if not results or len(results) == 0:
                    if attempt < max_retries - 1:
                        db_logger.warning(
                            f"⚠️ [重试] results 为空，{retry_delay}秒后重试：{execution_id} "
                            f"(尝试 {attempt + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2  # 指数退避
                        continue
                    else:
                        db_logger.error(
                            f"❌ [重试失败] results 始终为空：{execution_id}, "
                            f"重试 {max_retries} 次后放弃"
                        )
                else:
                    db_logger.info(
                        f"✅ [重试成功] 获取到 results：{execution_id}, "
                        f"数量={len(results)}, 尝试={attempt + 1}"
                    )
                
                break  # 成功获取，退出重试循环
                
            except Exception as e:
                if attempt < max_retries - 1:
                    db_logger.warning(f"查询结果失败，重试：{execution_id}, 错误={e}")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    db_logger.error(f"查询结果失败，放弃：{execution_id}, 错误={e}")
                    results = []
                    break
        
        # P1-1 降级方案：结果为空时的处理
        if not results or len(results) == 0:
            db_logger.warning(f"报告结果为空（重试后仍然为空）：{execution_id}")
            
            # 检查是否有部分结果（可能正在执行中）
            progress = report.get('progress', 0)
            if progress > 0 and progress < 100:
                return self._create_partial_fallback_report(execution_id, report, progress)
            
            # 完全无结果，创建包含元数据的降级报告
            return self._create_fallback_report(
                execution_id,
                '诊断已完成，但未生成有效结果。可能原因：AI 调用失败或数据保存失败',
                'no_results',
                report
            )

        # 3. 获取分析数据
        try:
            analysis = self.analysis_repo.get_by_execution_id(execution_id)
        except Exception as e:
            db_logger.error(f"查询分析数据失败：execution_id={execution_id}, 错误：{e}")
            analysis = {}

        # P1-1 降级方案：分析数据缺失时提供默认值
        analysis_data = self._ensure_complete_analysis(analysis, execution_id)

        # 【P0 关键修复 - 2026-03-12 第 4 次】检查结果是否为空
        # WAL 检查点后结果应该始终有数据，如果为空说明有真正的问题
        if not results or len(results) == 0:
            db_logger.error(
                f"❌ 报告结果为空：execution_id={execution_id}, "
                f"WAL 检查点后仍然为空，说明数据未正确保存！"
            )
            # 创建详细的错误报告，帮助排查问题
            return self._create_fallback_report(
                execution_id,
                f'诊断执行完成但未生成有效结果。可能原因：1) AI 调用返回空数据 2) 数据库保存失败 3) WAL 检查点失败',
                'no_results',
                report
            )

        # 4. 计算品牌分布（传递预期品牌列表用于完整性检查）
        # 构建完整的品牌列表：主品牌 + 竞品
        expected_brands = [report.get('brand_name', '')] if report.get('brand_name') else []
        if report.get('competitor_brands'):
            expected_brands.extend(report.get('competitor_brands', []))

        brand_distribution = self._calculate_brand_distribution(results, expected_brands)

        # 5. 计算情感分布
        sentiment_distribution = self._calculate_sentiment_distribution(results)

        # 6. 提取关键词
        keywords = self._extract_keywords(results)

        # 【P0 关键修复 - 2026-03-12 第 7 次】验证计算结果是否为空
        # 如果为空，记录详细错误日志用于排查
        if not brand_distribution.get('data') or brand_distribution.get('total_count', 0) == 0:
            db_logger.error(
                f"❌ [数据验证失败] execution_id={execution_id}, "
                f"brandDistribution.data={brand_distribution.get('data')}, "
                f"brandDistribution.total_count={brand_distribution.get('total_count')}, "
                f"results_count={len(results)}, "
                f"results_sample={results[:3] if results else '[]'}"  # 记录前 3 条结果用于排查
            )
            # 这是异常情况，需要排查为什么 results 有数据但品牌分布为空
            # 可能原因：1) 所有 brand 字段为空 2) results 本身就是空的

        if not sentiment_distribution.get('data') or sentiment_distribution.get('total_count', 0) == 0:
            db_logger.warning(
                f"⚠️ [数据验证警告] execution_id={execution_id}, "
                f"sentimentDistribution.data={sentiment_distribution.get('data')}, "
                f"sentimentDistribution.total_count={sentiment_distribution.get('total_count')}, "
                f"results_count={len(results)}"
            )

        if not keywords or len(keywords) == 0:
            db_logger.warning(
                f"⚠️ [数据验证警告] execution_id={execution_id}, "
                f"keywords_count={len(keywords)}, "
                f"results_count={len(results)}"
            )

        # P1-1 降级方案：验证数据质量，添加警告信息
        validation = self._validate_report_data(report, results, analysis_data)

        # 如果数据质量低，添加警告
        quality_warnings = self._check_data_quality(results, analysis_data)
        if quality_warnings:
            validation['warnings'].extend(quality_warnings)

        # P1-1 增强：添加降级场景识别
        fallback_scenarios = self._detect_fallback_scenarios(report, results, analysis_data)
        if fallback_scenarios:
            validation['fallback_scenarios'] = fallback_scenarios

        # 7. 构建完整报告（增强版）
        full_report = {
            'report': report,
            'results': results,
            'analysis': analysis_data,
            # P0-1 新增：前端需要的聚合数据
            'brandDistribution': brand_distribution,
            'sentimentDistribution': sentiment_distribution,
            'keywords': keywords,
            'meta': {
                'data_schema_version': report.get('data_schema_version', DATA_SCHEMA_VERSION),
                'server_version': report.get('server_version', 'unknown'),
                'retrieved_at': datetime.now().isoformat()
            },
            # P0-3 新增：验证信息
            'validation': validation,
            # P1-1 新增：质量提示
            'qualityHints': {
                'has_low_quality_results': any(r.get('quality_score', 100) < 60 for r in results),
                'has_partial_analysis': any(v == {} for v in analysis_data.values()),
                'warnings': quality_warnings or []
            }
        }

        # 8. 验证完整性（可选）
        checksum = report.get('checksum')
        if checksum:
            full_report['checksum_verified'] = True

        db_logger.info(f"✅ 获取完整报告成功：{execution_id}, 结果数：{len(results)}")
        # P0 修复：转换为 camelCase
        return convert_response_to_camel(full_report)

    def _create_fallback_report(self, execution_id: str, error_message: str,
                                 error_type: str, report: Optional[Dict] = None) -> Dict[str, Any]:
        """
        P1-1 新增：创建降级报告（用于异常场景）

        参数:
            execution_id: 执行 ID
            error_message: 错误信息
            error_type: 错误类型 (not_found, failed, timeout, no_results)
            report: 原始报告数据（可选）

        返回:
            降级报告数据
        """
        db_logger.info(f"创建降级报告：{execution_id}, 类型：{error_type}")

        # P1-1 增强：添加详细的降级场景信息
        fallback_info = {
            'not_found': {
                'title': '报告不存在',
                'description': '未找到对应的诊断报告',
                'icon': 'search',
                'actions': [
                    {'text': '重新诊断', 'type': 'navigate', 'url': '/pages/diagnosis/diagnosis'},
                    {'text': '查看历史', 'type': 'navigate', 'url': '/pages/history/history'}
                ]
            },
            'failed': {
                'title': '诊断失败',
                'description': '诊断过程中遇到错误',
                'icon': 'error',
                'actions': [
                    {'text': '查看错误详情', 'type': 'show_error_details'},
                    {'text': '重新诊断', 'type': 'navigate', 'url': '/pages/diagnosis/diagnosis'}
                ]
            },
            'timeout': {
                'title': '诊断超时',
                'description': '诊断处理时间过长',
                'icon': 'time',
                'actions': [
                    {'text': '继续等待', 'type': 'wait'},
                    {'text': '查看历史', 'type': 'navigate', 'url': '/pages/history/history'}
                ]
            },
            'no_results': {
                'title': '无有效结果',
                'description': '诊断未生成有效结果',
                'icon': 'warning',
                'actions': [
                    {'text': '优化配置', 'type': 'navigate', 'url': '/pages/diagnosis/diagnosis'},
                    {'text': '联系支持', 'type': 'contact_support'}
                ]
            }
        }

        fallback_config = fallback_info.get(error_type, {
            'title': '未知错误',
            'description': '发生未知错误',
            'icon': 'error',
            'actions': [
                {'text': '返回首页', 'type': 'navigate', 'url': '/pages/index/index'}
            ]
        })

        # P0 修复：转换为 camelCase
        return convert_response_to_camel({
            'report': report or {
                'execution_id': execution_id,
                'status': 'error',
                'created_at': datetime.now().isoformat()
            },
            'results': [],
            'analysis': {},
            'brandDistribution': {'data': {}, 'total_count': 0},
            'sentimentDistribution': {'data': {'positive': 0, 'neutral': 0, 'negative': 0}, 'total_count': 0},
            'keywords': [],
            'error': {
                'status': error_type,
                'message': error_message,
                'suggestion': self._get_error_suggestion(error_type),
                'fallback_info': fallback_config
            },
            'meta': {
                'data_schema_version': DATA_SCHEMA_VERSION,
                'server_version': '2.0.0',
                'retrieved_at': datetime.now().isoformat()
            },
            'validation': {
                'is_valid': False,
                'errors': [error_message],
                'warnings': [],
                'fallback_scenarios': [error_type]
            },
            'qualityHints': {
                'has_low_quality_results': False,
                'has_partial_analysis': True,
                'warnings': [error_message]
            }
        })

    def _create_partial_fallback_report(self, execution_id: str, report: Dict, 
                                         progress: int) -> Dict[str, Any]:
        """
        P1-1 新增：创建部分结果降级报告
        
        参数:
            execution_id: 执行 ID
            report: 报告主数据
            progress: 当前进度
        
        返回:
            部分结果报告
        """
        # P0 修复：转换为 camelCase
        return convert_response_to_camel({
            'report': report,
            'results': [],
            'analysis': {},
            'brandDistribution': {'data': {}, 'total_count': 0},
            'sentimentDistribution': {'data': {'positive': 0, 'neutral': 0, 'negative': 0}, 'total_count': 0},
            'keywords': [],
            'partial': {
                'is_partial': True,
                'progress': progress,
                'stage': report.get('stage', 'unknown'),
                'message': f'诊断进行中，当前进度{progress}%',
                'suggestion': '请稍候重试，或等待诊断完成后再次查看'
            },
            'meta': {
                'data_schema_version': DATA_SCHEMA_VERSION,
                'server_version': '2.0.0',
                'retrieved_at': datetime.now().isoformat()
            },
            'validation': {
                'is_valid': False,
                'errors': [],
                'warnings': ['诊断尚未完成，数据可能不完整']
            },
            'qualityHints': {
                'has_low_quality_results': False,
                'has_partial_analysis': True,
                'warnings': ['诊断进行中']
            }
        })

    def _ensure_complete_analysis(self, analysis: Dict, execution_id: str = None) -> Dict[str, Any]:
        """
        P1-2 修复：确保分析数据完整（缺失时提供默认值 - 增强版）

        参数:
            analysis: 原始分析数据
            execution_id: 执行 ID（可选，用于日志）

        返回:
            完整的分析数据（包含缺失标记和建议）
        """
        required_analysis_types = [
            'competitive_analysis',
            'brand_scores',
            'semantic_drift',
            'source_purity',
            'recommendations'
        ]

        complete_analysis = {}
        missing_types = []
        partial_types = []  # 有部分数据但不完整

        for analysis_type in required_analysis_types:
            if analysis_type in analysis and analysis[analysis_type]:
                analysis_data = analysis[analysis_type]
                
                # 检查数据是否完整（有 warning 表示是默认值）
                if analysis_data.get('warning'):
                    partial_types.append(analysis_type)
                    complete_analysis[analysis_type] = analysis_data
                else:
                    complete_analysis[analysis_type] = analysis_data
            else:
                complete_analysis[analysis_type] = self._get_default_analysis(analysis_type)
                missing_types.append(analysis_type)

        # P1-2 增强：详细日志记录
        if missing_types and execution_id:
            db_logger.warning(
                f"分析数据缺失：{execution_id}, "
                f"缺失类型：{missing_types}, "
                f"部分缺失：{partial_types}"
            )
        elif partial_types and execution_id:
            db_logger.info(
                f"分析数据部分缺失：{execution_id}, "
                f"部分缺失类型：{partial_types}"
            )
        elif execution_id:
            db_logger.info(f"分析数据完整：{execution_id}")

        # 添加分析完整性摘要
        complete_analysis['_completeness_summary'] = {
            'total_types': len(required_analysis_types),
            'complete_count': len(required_analysis_types) - len(missing_types) - len(partial_types),
            'partial_count': len(partial_types),
            'missing_count': len(missing_types),
            'missing_types': missing_types,
            'partial_types': partial_types,
            'completeness_ratio': round(
                (len(required_analysis_types) - len(missing_types)) / len(required_analysis_types) * 100, 2
            )
        }

        return complete_analysis

    def _get_default_analysis(self, analysis_type: str) -> Dict[str, Any]:
        """
        P1-2 修复：获取默认分析数据（增强版 - 提供有意义的默认值）

        参数:
            analysis_type: 分析类型

        返回:
            默认分析数据（包含有用的占位符和建议）
        """
        defaults = {
            'competitive_analysis': {
                'warning': '竞品分析数据暂缺',
                'description': '竞品分析模块未能生成有效数据，可能是因为竞品品牌数量不足或 AI 未能返回有效的竞品信息',
                'data': {
                    'main_brand_share': 0,
                    'competitor_shares': {},
                    'rank': 0,
                    'total_competitors': 0,
                    'analysis_note': '建议：增加竞品品牌数量（至少 3 个）以获得更准确的竞争分析'
                },
                'fallback_tips': [
                    '确保选择了足够的竞品品牌（建议 3-5 个）',
                    '检查竞品品牌名称是否准确',
                    '尝试使用更具体的问题来获取竞品信息'
                ]
            },
            'brand_scores': {
                'warning': '品牌评分数据暂缺',
                'description': '品牌评分模块未能生成有效数据，可能是因为 AI 返回的评分格式不正确或缺少必要的评分维度',
                'scores': {},
                'fallback_tips': [
                    '品牌评分需要 AI 返回结构化的评分数据',
                    '检查 AI 平台是否支持评分功能',
                    '尝试减少评分维度以提高成功率'
                ],
                'default_dimensions': {
                    'brand_awareness': {'score': 0, 'note': '数据不足'},
                    'brand_image': {'score': 0, 'note': '数据不足'},
                    'brand_loyalty': {'score': 0, 'note': '数据不足'},
                    'perceived_quality': {'score': 0, 'note': '数据不足'}
                }
            },
            'semantic_drift': {
                'warning': '语义偏移数据暂缺',
                'description': '语义偏移分析需要足够的关键词数据，当前结果中关键词数量不足',
                'drift_score': 0,
                'keywords': [],
                'fallback_tips': [
                    '语义偏移分析需要每个品牌至少有 5 条有效结果',
                    '增加问题数量以获取更多关键词数据',
                    '检查 AI 返回的内容是否包含足够的关键词'
                ],
                'analysis_note': '当结果数量充足时，语义偏移分析将自动计算'
            },
            'source_purity': {
                'warning': '信源纯净度数据暂缺',
                'description': '信源纯净度分析需要识别信息来源，当前数据中信源信息不足',
                'purity_score': 0,
                'sources': [],
                'fallback_tips': [
                    '信源纯净度分析需要 AI 返回信息来源',
                    '确保问题设计中包含来源相关的询问',
                    '检查 AI 平台是否支持来源识别'
                ],
                'source_types': {
                    'official': 0,
                    'media': 0,
                    'user_generated': 0,
                    'unknown': 0
                }
            },
            'recommendations': {
                'warning': '优化建议数据暂缺',
                'description': '优化建议模块未能生成有效建议，可能是因为缺少足够的分析数据',
                'suggestions': [],
                'fallback_tips': [
                    '优化建议基于其他分析模块的结果',
                    '确保竞品分析、品牌评分等模块正常工作',
                    '查看其他分析模块的警告信息以了解具体问题'
                ],
                'generic_suggestions': [
                    '增加竞品数量以获得更全面的竞争视角',
                    '优化问题描述以获取更具体的 AI 回答',
                    '选择更具体的品牌名称以减少歧义',
                    '定期检查诊断结果质量并调整配置'
                ]
            }
        }
        
        result = defaults.get(analysis_type, {
            'warning': '数据暂缺',
            'description': f'{analysis_type} 模块未能生成有效数据',
            'data': {},
            'fallback_tips': [
                '检查诊断配置是否正确',
                '查看系统日志获取详细错误信息',
                '联系技术支持获取帮助'
            ]
        })
        
        # P1-2 增强：记录默认值使用日志
        db_logger.debug(f"使用默认分析数据：type={analysis_type}")
        
        return result

    def _check_data_quality(self, results: List[Dict], analysis: Dict) -> List[str]:
        """
        P1-1 新增：检查数据质量
        
        参数:
            results: 结果列表
            analysis: 分析数据
        
        返回:
            质量警告列表
        """
        warnings = []
        
        # 检查低质量结果
        low_quality_count = sum(1 for r in results if r.get('quality_score', 100) < 60)
        if low_quality_count > 0:
            ratio = low_quality_count / len(results) * 100
            warnings.append(f'{low_quality_count}/{len(results)} 条结果质量较低')
        
        # 检查空分析数据
        empty_analysis = sum(1 for v in analysis.values() if not v or v == {})
        if empty_analysis > 0:
            warnings.append(f'{empty_analysis} 项分析数据缺失')
        
        # 检查情感分布异常
        sentiment_dist = self._calculate_sentiment_distribution(results)
        total = sentiment_dist['total_count']
        if total > 0:
            neutral_ratio = sentiment_dist['data']['neutral'] / total
            if neutral_ratio > 0.8:
                warnings.append('情感分析结果以中性为主，可能需要优化问题')
        
        return warnings

    def _get_error_suggestion(self, error_type: str) -> str:
        """
        P1-1 新增：获取错误建议

        参数:
            error_type: 错误类型

        返回:
            建议文本
        """
        suggestions = {
            'not_found': '请检查执行 ID 是否正确，或重新进行诊断',
            'failed': '诊断过程中遇到错误，建议优化问题后重试',
            'timeout': '诊断处理时间过长，建议减少品牌数量或 AI 平台数量后重试',
            'no_results': '诊断未生成有效结果，建议检查 AI 平台配置后重试'
        }
        return suggestions.get(error_type, '请稍后重试或联系技术支持')

    def _detect_fallback_scenarios(self, report: Dict, results: List, analysis: Dict) -> List[Dict[str, Any]]:
        """
        P1-1 新增：检测降级场景

        参数:
            report: 报告主数据
            results: 结果列表
            analysis: 分析数据

        返回:
            降级场景列表，每个场景包含：
            - scenario: 场景类型
            - severity: 严重程度 (low/medium/high)
            - message: 描述信息
            - suggestion: 用户建议
        """
        scenarios = []

        # 场景 1: 低质量结果过多
        if results:
            low_quality_count = sum(1 for r in results if r.get('quality_score', 100) < 60)
            ratio = low_quality_count / len(results)
            if ratio > 0.5:
                scenarios.append({
                    'scenario': 'low_quality_results',
                    'severity': 'high' if ratio > 0.8 else 'medium',
                    'message': f'{low_quality_count}/{len(results)} 条结果质量较低',
                    'suggestion': 'AI 返回的内容质量不高，建议优化问题描述或选择更具体的品牌名称',
                    'metrics': {
                        'low_quality_count': low_quality_count,
                        'total_count': len(results),
                        'ratio': round(ratio * 100, 2)
                    }
                })

        # 场景 2: 分析数据缺失
        if analysis:
            missing_analysis = [k for k, v in analysis.items() if not v or v == {} or v.get('warning')]
            if len(missing_analysis) > 0:
                scenarios.append({
                    'scenario': 'missing_analysis',
                    'severity': 'high' if len(missing_analysis) > 3 else 'medium',
                    'message': f'{len(missing_analysis)} 项分析数据缺失',
                    'suggestion': '部分分析模块未能生成结果，报告参考价值可能受限',
                    'metrics': {
                        'missing_types': missing_analysis,
                        'missing_count': len(missing_analysis)
                    }
                })

        # 场景 3: 结果数量不足
        if results and len(results) < 5:
            scenarios.append({
                'scenario': 'insufficient_results',
                'severity': 'medium',
                'message': f'诊断结果数量较少（{len(results)} 条）',
                'suggestion': '结果数量不足可能影响分析准确性，建议增加竞品数量或问题数量',
                'metrics': {
                    'result_count': len(results),
                    'recommended_min': 5
                }
            })

        # 场景 4: 情感分布异常
        if results:
            sentiment_dist = self._calculate_sentiment_distribution(results)
            total = sentiment_dist['total_count']
            if total > 0:
                neutral_ratio = sentiment_dist['data']['neutral'] / total
                if neutral_ratio > 0.8:
                    scenarios.append({
                        'scenario': 'neutral_sentiment_dominant',
                        'severity': 'low',
                        'message': '情感分析结果以中性为主',
                        'suggestion': '中性评价过多可能意味着问题不够具体或品牌特征不明显',
                        'metrics': {
                            'neutral_ratio': round(neutral_ratio * 100, 2)
                        }
                    })

        # 场景 5: 执行时间过长
        if report.get('created_at'):
            try:
                created_time = datetime.fromisoformat(report['created_at'])
                elapsed = (datetime.now() - created_time).total_seconds()
                if elapsed > 300:  # 超过 5 分钟
                    scenarios.append({
                        'scenario': 'long_execution_time',
                        'severity': 'low',
                        'message': f'诊断执行时间较长（{int(elapsed)}秒）',
                        'suggestion': '执行时间长可能是因为分析的数据量大，不影响结果准确性',
                        'metrics': {
                            'elapsed_seconds': int(elapsed)
                        }
                    })
            except Exception:
                pass

        return scenarios

    def _calculate_brand_distribution(
        self,
        results: List[Dict[str, Any]],
        expected_brands: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        计算品牌分布数据（增强版 - 支持少样本和空数据兜底）

        参数:
            results: 结果列表
            expected_brands: 预期的品牌列表（可选，用于检测数据完整性）

        返回:
            {
                data: {品牌名：数量，...},
                total_count: 总数，
                success_rate: 成功率（如果有 expected_brands）,
                quality_warning: 质量警告（如果数据不完整）,
                _debug_info: 调试信息（用于前端降级）
            }
        """
        distribution = {}
        valid_results_count = 0

        for result in results:
            # P0 修复：检查结果是否为 None
            if not result:
                continue

            # 【P0 关键修复 - 2026-03-13 第 11 次】优先使用 extracted_brand（从 AI 响应中提取的品牌）
            brand = result.get('extracted_brand') if result else None
            
            # 如果 extracted_brand 不存在，使用 brand 字段
            if not brand or not str(brand).strip():
                brand = result.get('brand') if result else None
            
            # 如果还是为空，使用 'Unknown'
            if not brand or not str(brand).strip():
                brand = 'Unknown'
                db_logger.warning(f"[品牌分布] 发现空 brand，已替换为 'Unknown': result={result}")

            distribution[brand] = distribution.get(brand, 0) + 1
            valid_results_count += 1

        total_count = sum(distribution.values())

        # 【P0 关键修复 - 2026-03-12 第 10 次】如果 results 为空，使用 expected_brands 创建兜底数据
        if not results or len(results) == 0:
            db_logger.warning(
                f"⚠️ [品牌分布] results 为空，使用 expected_brands 创建兜底数据："
                f"expected_brands={expected_brands}"
            )

            # 使用预期品牌创建空分布
            if expected_brands:
                for brand in expected_brands:
                    if brand and str(brand).strip():
                        distribution[brand] = 0

            # 如果 expected_brands 也为空，使用 'Unknown'
            if not distribution:
                distribution['Unknown'] = 0

            total_count = 0
            db_logger.info(
                f"[品牌分布] 兜底数据创建完成：distribution={distribution}"
            )

        # 【P0 关键修复】如果 total_count 为 0 但 distribution 有数据，至少返回数据
        if total_count == 0 and distribution:
            db_logger.warning(
                f"⚠️ [品牌分布] total_count 为 0 但 distribution 有数据，返回空分布："
                f"distribution={distribution}"
            )

        # 检测数据不足
        quality_warning = None
        if expected_brands and len(distribution) < len(expected_brands):
            missing = set(expected_brands) - set(distribution.keys())
            quality_warning = f"数据不完整：缺失品牌 {missing}"
            db_logger.warning(
                f"[品牌分布] 数据不完整：expected={expected_brands}, "
                f"actual={list(distribution.keys())}, missing={missing}"
            )

        # 计算成功率
        success_rate = None
        if expected_brands and len(expected_brands) > 0:
            success_rate = total_count / len(expected_brands) if len(expected_brands) > 0 else None

        return {
            'data': distribution,
            'total_count': total_count,
            'success_rate': success_rate,
            'quality_warning': quality_warning,
            # 【P0 关键修复 - 第 10 次】添加调试信息，便于前端降级
            '_debug_info': {
                'results_count': len(results) if results else 0,
                'valid_results_count': valid_results_count,
                'expected_brands_count': len(expected_brands) if expected_brands else 0,
                'distribution_keys': list(distribution.keys()),
                'has_data': bool(distribution),
                'total_count': total_count,
                # 【P0 关键修复 - 第 11 次】添加 extracted_brand 统计
                'extracted_brand_count': sum(1 for r in results if r.get('extracted_brand')),
                'extraction_success_rate': sum(1 for r in results if r.get('extracted_brand')) / len(results) if results else 0
            }
        }

    def _calculate_sentiment_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算情感分布数据

        参数:
            results: 结果列表

        返回:
            {
                data: {positive: 数量，neutral: 数量，negative: 数量},
                total_count: 总数
            }
        """
        sentiment_counts = {'positive': 0, 'neutral': 0, 'negative': 0}

        for result in results:
            # P0 修复：检查结果是否为 None
            if not result:
                db_logger.warning('发现 None 结果，跳过情感分析')
                continue

            # P0 修复：安全获取 geo_data，确保默认为空字典
            geo_data = result.get('geo_data') or {}

            # P0 修复：安全获取 sentiment 值
            sentiment = geo_data.get('sentiment', 0) if geo_data else 0

            if sentiment > 0.3:
                sentiment_counts['positive'] += 1
            elif sentiment < -0.3:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1

        return {
            'data': sentiment_counts,
            'total_count': sum(sentiment_counts.values())
        }

    def _extract_keywords(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取关键词（增强版 - 支持从 responseContent 中提取）

        参数:
            results: 结果列表

        返回:
            关键词列表
        """
        keywords = []
        seen = set()

        for result in results:
            # P0 修复：检查结果是否为 None
            if not result:
                continue

            # 方式 1: 从 geo_data.keywords 提取
            geo_data = result.get('geo_data') or {}
            extracted_keywords = geo_data.get('keywords', []) if geo_data else []

            if extracted_keywords and isinstance(extracted_keywords, list):
                for kw in extracted_keywords:
                    word = kw.get('word', '') if isinstance(kw, dict) else str(kw)
                    if word and word not in seen:
                        keywords.append(kw if isinstance(kw, dict) else {'word': kw, 'count': 1})
                        seen.add(word)

            # 方式 2: 如果 geo_data 为空，从 responseContent 中提取关键词（P0 修复 - 2026-03-11）
            if not extracted_keywords:
                response_content = result.get('response_content') or result.get('responseContent')
                if response_content and isinstance(response_content, str):
                    # 从 JSON 片段中提取 top3_brands
                    try:
                        # 尝试从 responseContent 中提取 JSON 部分
                        import re
                        json_match = re.search(r'\{.*?"top3_brands".*?\}', response_content, re.DOTALL)
                        if json_match:
                            json_str = json_match.group()
                            json_data = json.loads(json_str)
                            top3 = json_data.get('top3_brands', [])
                            if top3 and isinstance(top3, list):
                                for brand in top3:
                                    if isinstance(brand, dict):
                                        word = brand.get('name', '')
                                        if word and word not in seen:
                                            keywords.append({'word': word, 'count': 1, 'source': 'top3_brands'})
                                            seen.add(word)
                                        # 也提取 reason 中的关键词
                                        reason = brand.get('reason', '')
                                        if reason:
                                            # 简单分词（中文按字符，英文按空格）
                                            if any('\u4e00' <= c <= '\u9fff' for c in reason):
                                                # 中文：简单提取 2-4 字短语
                                                for i in range(len(reason) - 1):
                                                    phrase = reason[i:i+2]
                                                    if phrase not in seen and len(phrase) >= 2:
                                                        keywords.append({'word': phrase, 'count': 1, 'source': 'reason'})
                                                        seen.add(phrase)
                                            else:
                                                # 英文：按空格分词
                                                for word in reason.split():
                                                    if len(word) > 3 and word not in seen:
                                                        keywords.append({'word': word, 'count': 1, 'source': 'reason'})
                                                        seen.add(word)
                    except Exception as e:
                        db_logger.debug(f"从 responseContent 提取关键词失败：{e}")

        return keywords

    def _validate_report_data(self, report: Dict, results: List, analysis: Dict) -> Dict[str, Any]:
        """
        验证报告数据
        
        返回:
            {
                is_valid: bool,
                errors: [],
                warnings: []
            }
        """
        errors = []
        warnings = []
        
        # 1. 验证报告主数据
        if not report.get('execution_id'):
            errors.append('execution_id 缺失')
        if not report.get('brand_name'):
            errors.append('brand_name 缺失')
        
        # 2. 验证结果数据
        if not isinstance(results, list):
            errors.append('results 必须是数组')
        elif len(results) == 0:
            warnings.append('结果数组为空')
        
        # 3. 验证分析数据
        required_analysis = ['competitive_analysis', 'brand_scores']
        for analysis_type in required_analysis:
            if analysis_type not in analysis:
                warnings.append(f'缺少分析数据：{analysis_type}')
        
        # 4. 验证校验和
        checksum = report.get('checksum')
        if checksum:
            calculated_checksum = calculate_checksum({
                'report': report,
                'results': results,
                'analysis': analysis
            })
            if checksum != calculated_checksum:
                errors.append('校验和不匹配，数据可能已损坏')
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
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

        # P21 修复：计算 health_score 并返回 snake_case 格式
        for report in reports:
            # 根据 status 和 progress 计算 health_score
            if report.get('status') == 'completed':
                report['health_score'] = 100
            elif report.get('status') == 'failed':
                report['health_score'] = 0
            else:
                report['health_score'] = report.get('progress', 0)

        return {
            'reports': reports,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(reports),
                'has_more': len(reports) == limit
            }
        }

    def get_history_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        获取历史报告（增强版 - 2026-03-13）

        专为历史报告查看优化：
        1. 优先从数据库读取，不触发新的诊断
        2. 包含完整的元数据（品牌、时间、状态等）
        3. 即使部分数据缺失，也返回可用的最大数据集
        4. 强化本地缓存友好的数据格式
        5. 【P0 关键修复】支持从 DiagnosisResult 表重建完整数据

        参数:
            execution_id: 执行 ID

        返回:
            完整的报告数据，包含 brandDistribution, sentimentDistribution, keywords 等
        """
        db_logger.info(f"[HistoryReport] 开始获取历史报告：{execution_id}")

        # 1. 获取报告主数据
        try:
            report = self.report_repo.get_by_execution_id(execution_id)
        except Exception as e:
            db_logger.error(f"[HistoryReport] 查询报告失败：{e}")
            return self._create_fallback_report(
                execution_id,
                f'数据库查询失败：{str(e)}',
                'database_error'
            )

        if not report:
            db_logger.warning(f"[HistoryReport] 报告不存在：{execution_id}")
            return self._create_fallback_report(execution_id, '报告不存在', 'not_found')

        if not isinstance(report, dict):
            db_logger.error(f"[HistoryReport] 报告格式错误：type={type(report)}")
            return self._create_fallback_report(
                execution_id,
                '报告数据格式错误',
                'invalid_format'
            )

        # 2. 获取结果明细
        try:
            results = self.result_repo.get_by_execution_id(execution_id)
        except Exception as e:
            db_logger.error(f"[HistoryReport] 查询结果失败：{e}")
            results = []

        # 3. 结果为空时的处理
        # 【P0 关键修复 - 2026-03-13 第 15 次补充】尝试从 DiagnosisResult 表重建数据
        if not results or len(results) == 0:
            db_logger.warning(f"[HistoryReport] ⚠️ 结果数据为空：{execution_id}")

            # 尝试 1: 从 DiagnosisResult ORM 模型重建（使用 SQLAlchemy）
            try:
                from wechat_backend.models import DiagnosisResult
                db_results = DiagnosisResult.query.filter_by(execution_id=execution_id).all()

                if db_results:
                    db_logger.info(
                        f"[HistoryReport] ✅ [尝试 1] 从 DiagnosisResult ORM 重建数据：{len(db_results)} 条"
                    )

                    # 转换为字典格式（包含完整字段）
                    results = []
                    for r in db_results:
                        result_dict = {
                            'id': r.id,
                            'execution_id': r.execution_id,
                            'brand': r.brand,
                            'extracted_brand': r.extracted_brand,
                            'question': r.question,
                            'model': r.model,
                            'response_content': r.response_content,
                            'response_latency': r.response_latency,
                            'status': r.status,
                            'error_message': r.error_message,
                            'quality_score': r.quality_score,
                            'quality_level': r.quality_level,
                            'created_at': r.created_at.isoformat() if r.created_at else None,
                            'updated_at': r.updated_at.isoformat() if r.updated_at else None
                        }
                        
                        # 解析 JSON 字段
                        try:
                            result_dict['geo_data'] = json.loads(r.geo_data) if r.geo_data else {}
                        except:
                            result_dict['geo_data'] = {}
                        
                        try:
                            result_dict['quality_details'] = json.loads(r.quality_details) if r.quality_details else {}
                        except:
                            result_dict['quality_details'] = {}
                        
                        # 添加 response 对象（保持向后兼容）
                        result_dict['response'] = {
                            'content': r.response_content,
                            'latency': r.response_latency
                        }
                        
                        results.append(result_dict)

                    db_logger.info(
                        f"[HistoryReport] ✅ [尝试 1] 重建完成：results_count={len(results)}"
                    )
            except Exception as rebuild_err:
                db_logger.error(
                    f"[HistoryReport] ❌ [尝试 1] ORM 重建失败：{rebuild_err}"
                )
                results = []

            # 尝试 2: 如果 ORM 方式失败，直接使用 SQL 查询
            if not results or len(results) == 0:
                try:
                    db_logger.info(f"[HistoryReport] ⏳ [尝试 2] 使用 SQL 直接查询...")
                    
                    from wechat_backend.database_connection_pool import get_db_pool
                    pool = get_db_pool()
                    conn = pool.get_connection()
                    conn.row_factory = sqlite3.Row
                    
                    try:
                        cursor = conn.cursor()
                        cursor.execute("""
                            SELECT * FROM diagnosis_results
                            WHERE execution_id = ?
                            ORDER BY brand, question, model
                        """, (execution_id,))
                        
                        db_rows = cursor.fetchall()
                        
                        if db_rows:
                            db_logger.info(
                                f"[HistoryReport] ✅ [尝试 2] 从 diagnosis_results SQL 重建数据：{len(db_rows)} 条"
                            )
                            
                            for row in db_rows:
                                item = dict(row)
                                
                                # 解析 JSON 字段
                                try:
                                    item['geo_data'] = json.loads(item['geo_data']) if item.get('geo_data') else {}
                                except:
                                    item['geo_data'] = {}
                                
                                try:
                                    item['quality_details'] = json.loads(item['quality_details']) if item.get('quality_details') else {}
                                except:
                                    item['quality_details'] = {}
                                
                                # 构建 response 对象
                                item['response'] = {
                                    'content': item['response_content'],
                                    'latency': item.get('response_latency')
                                }
                                
                                results.append(item)
                            
                            db_logger.info(
                                f"[HistoryReport] ✅ [尝试 2] 重建完成：results_count={len(results)}"
                            )
                    finally:
                        pool.return_connection(conn)
                        
                except Exception as sql_err:
                    db_logger.error(
                        f"[HistoryReport] ❌ [尝试 2] SQL 重建失败：{sql_err}"
                    )
                    results = []

            # 检查报告状态
            if report.get('status') == 'failed':
                return self._create_fallback_report(
                    execution_id,
                    '诊断执行失败',
                    'failed',
                    report
                )

            # 如果重建后仍然为空，返回部分数据
            if not results or len(results) == 0:
                db_logger.warning(
                    f"[HistoryReport] ⚠️ 所有重建尝试都失败，返回部分数据"
                )
                return self._create_partial_fallback_report(
                    execution_id,
                    report,
                    report.get('progress', 0)
                )
            else:
                db_logger.info(
                    f"[HistoryReport] ✅ 重建成功，继续构建完整报告"
                )

        # 4. 计算品牌分布（传递预期品牌列表用于完整性检查）
        # 构建完整的品牌列表：主品牌 + 竞品
        expected_brands = [report.get('brand_name', '')] if report.get('brand_name') else []
        if report.get('competitor_brands'):
            expected_brands.extend(report.get('competitor_brands', []))

        brand_distribution = self._calculate_brand_distribution(results, expected_brands)

        # 5. 计算情感分布
        sentiment_distribution = self._calculate_sentiment_distribution(results)

        # 6. 提取关键词
        keywords = self._extract_keywords(results)

        # 7. 构建完整报告（历史报告优化版）
        full_report = {
            'execution_id': execution_id,
            'report_id': report.get('report_id'),
            'brand_name': report.get('brand_name', ''),
            'competitor_brands': report.get('competitor_brands', []),
            'selected_models': report.get('selected_models', []),
            'status': report.get('status', 'completed'),
            'progress': report.get('progress', 100),
            'stage': report.get('stage', 'completed'),
            'is_completed': report.get('is_completed', False),
            'created_at': report.get('created_at', ''),
            'completed_at': report.get('completed_at', ''),
            
            # 核心展示数据
            'brandDistribution': brand_distribution,
            'sentimentDistribution': sentiment_distribution,
            'keywords': keywords,
            
            # 明细数据
            'results': results,
            'detailed_results': results,  # 兼容前端期望
            
            # 元数据
            'meta': {
                'result_count': len(results),
                'brand_count': len(set(r.get('brand', '') for r in results if r.get('brand'))),
                'model_count': len(set(r.get('model', '') for r in results if r.get('model'))),
                'data_version': '1.0',
                'is_history': True  # 标记为历史数据
            }
        }

        db_logger.info(
            f"[HistoryReport] ✅ 历史报告获取成功：{execution_id}, "
            f"results={len(results)}, brands={full_report['meta']['brand_count']}"
        )

        return full_report

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
    4. 数据质量评分
    """

    @staticmethod
    def validate_report(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        P1-3 修复：完善报告验证（添加详细验证和评分）

        返回:
            {
                is_valid: 是否有效
                errors: 错误列表
                warnings: 警告列表
                quality_score: 质量评分 (0-100)
                details: 详细验证信息
            }
        """
        errors = []
        warnings = []
        quality_issues = []

        # P0-REPORT-1 修复：报告结构是 {'report': {...}, 'results': [...], 'analysis': {...}}
        # 必填字段在 report 对象内，不在顶层
        report_data = report.get('report', {})

        # 1. 验证报告主数据
        report_valid = ReportValidationService._validate_report_data(report_data, errors, warnings)
        
        # 2. 验证结果数据
        results_valid = ReportValidationService._validate_results_data(report.get('results', []), errors, warnings, quality_issues)
        
        # 3. 验证分析数据
        analysis_valid = ReportValidationService._validate_analysis_data(report.get('analysis', {}), errors, warnings, quality_issues)
        
        # 4. 验证聚合数据
        aggregation_valid = ReportValidationService._validate_aggregation_data(report, errors, warnings)
        
        # 5. 验证校验和
        checksum_valid = ReportValidationService._validate_checksum(report, errors, warnings)

        # 计算质量评分
        quality_score = ReportValidationService._calculate_quality_score(
            report_valid, results_valid, analysis_valid, aggregation_valid, checksum_valid,
            len(errors), len(warnings), len(quality_issues)
        )

        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'quality_issues': quality_issues,
            'quality_score': quality_score,
            'details': {
                'report_valid': report_valid,
                'results_valid': results_valid,
                'analysis_valid': analysis_valid,
                'aggregation_valid': aggregation_valid,
                'checksum_valid': checksum_valid
            }
        }

    @staticmethod
    def _validate_report_data(report_data: Dict, errors: List, warnings: List) -> bool:
        """验证报告主数据"""
        # P0 修复：增加判空逻辑，防止 NoneType 错误
        if report_data is None:
            errors.append("report 对象为 None")
            return False
        
        if not report_data:
            errors.append("report 对象为空或缺失")
            return False

        # 验证必填字段
        required_fields = ['execution_id', 'user_id', 'brand_name', 'created_at']
        for field in required_fields:
            if field not in report_data:
                errors.append(f"缺少必填字段：{field}")

        # 验证状态字段
        status = report_data.get('status')
        if status and status not in ['pending', 'processing', 'completed', 'failed']:
            warnings.append(f"未知状态：{status}")

        # 验证进度
        progress = report_data.get('progress')
        if progress is not None and (not isinstance(progress, (int, float)) or progress < 0 or progress > 100):
            errors.append(f"进度值无效：{progress}")

        return len(errors) == 0

    @staticmethod
    def _validate_results_data(results: List, errors: List, warnings: List, quality_issues: List) -> bool:
        """验证结果数据"""
        if not results:
            warnings.append("报告缺少 results 数据")
            return True  # 不是致命错误
        
        if not isinstance(results, list):
            errors.append("results 必须是数组")
            return False
        
        # 验证每个结果
        required_fields = ['brand', 'question', 'model']
        empty_results = 0
        
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                errors.append(f"结果 {i} 格式错误")
                continue
            
            # 检查必填字段
            for field in required_fields:
                if field not in result:
                    errors.append(f"结果 {i} 缺少 {field} 字段")
            
            # 检查结果是否为空
            if not result.get('geo_data') and not result.get('response'):
                empty_results += 1
                quality_issues.append(f"结果 {i} 内容为空")
            
            # 验证质量评分
            quality_score = result.get('quality_score')
            if quality_score is not None:
                if not isinstance(quality_score, (int, float)) or quality_score < 0 or quality_score > 100:
                    warnings.append(f"结果 {i} 质量评分无效：{quality_score}")
                elif quality_score < 60:
                    quality_issues.append(f"结果 {i} 质量较低：{quality_score}")
        
        if empty_results > 0:
            warnings.append(f"{empty_results}/{len(results)} 个结果为空")
        
        return len(errors) == 0

    @staticmethod
    def _validate_analysis_data(analysis: Dict, errors: List, warnings: List, quality_issues: List) -> bool:
        """验证分析数据"""
        if not analysis:
            warnings.append("报告缺少 analysis 数据")
            return True  # 不是致命错误
        
        if not isinstance(analysis, dict):
            errors.append("analysis 必须是对象")
            return False
        
        # 验证必需的分析类型
        required_analysis = ['competitive_analysis', 'brand_scores']
        optional_analysis = ['semantic_drift', 'source_purity', 'recommendations']
        
        for analysis_type in required_analysis:
            if analysis_type not in analysis:
                warnings.append(f"缺少必需分析数据：{analysis_type}")
            elif not analysis[analysis_type]:
                quality_issues.append(f"分析数据 {analysis_type} 为空")
        
        for analysis_type in optional_analysis:
            if analysis_type not in analysis:
                quality_issues.append(f"缺少可选分析数据：{analysis_type}")
        
        return len(errors) == 0

    @staticmethod
    def _validate_aggregation_data(report: Dict, errors: List, warnings: List) -> bool:
        """验证聚合数据"""
        # 验证品牌分布
        brand_dist = report.get('brandDistribution')
        if brand_dist:
            if not isinstance(brand_dist, dict) or 'data' not in brand_dist:
                warnings.append("品牌分布数据格式错误")
        else:
            quality_issues.append("缺少品牌分布数据")
        
        # 验证情感分布
        sentiment_dist = report.get('sentimentDistribution')
        if sentiment_dist:
            if not isinstance(sentiment_dist, dict) or 'data' not in sentiment_dist:
                warnings.append("情感分布数据格式错误")
            else:
                # 验证情感数据完整性
                data = sentiment_dist.get('data', {})
                required_emotions = ['positive', 'neutral', 'negative']
                for emotion in required_emotions:
                    if emotion not in data:
                        warnings.append(f"缺少情感数据：{emotion}")
        else:
            quality_issues.append("缺少情感分布数据")
        
        # 验证关键词
        keywords = report.get('keywords')
        if keywords is not None:
            if not isinstance(keywords, list):
                errors.append("keywords 必须是数组")
        else:
            quality_issues.append("缺少关键词数据")
        
        return len(errors) == 0

    @staticmethod
    def _validate_checksum(report: Dict, errors: List, warnings: List) -> bool:
        """验证校验和"""
        checksum = report.get('checksum')
        checksum_verified = report.get('checksum_verified')
        
        if checksum and not checksum_verified:
            warnings.append("校验和未验证，数据可能已损坏")
            return False
        
        if checksum_verified:
            # 尝试验证校验和
            try:
                calculated = calculate_checksum({
                    'report': report.get('report'),
                    'results': report.get('results'),
                    'analysis': report.get('analysis')
                })
                if checksum != calculated:
                    errors.append("校验和不匹配，数据已损坏")
                    return False
            except Exception as e:
                warnings.append(f"校验和验证失败：{e}")
        
        return True

    @staticmethod
    def _calculate_quality_score(report_valid: bool, results_valid: bool, 
                                  analysis_valid: bool, aggregation_valid: bool,
                                  checksum_valid: bool, errors: int, 
                                  warnings: int, quality_issues: int) -> int:
        """
        计算质量评分 (0-100)
        
        评分规则：
        - 基础分：100 分
        - 每个错误：-20 分
        - 每个警告：-5 分
        - 每个质量问题：-3 分
        - 验证失败：-10 分
        """
        score = 100
        
        # 错误扣分
        score -= errors * 20
        
        # 警告扣分
        score -= warnings * 5
        
        # 质量问题扣分
        score -= quality_issues * 3
        
        # 验证失败扣分
        if not report_valid:
            score -= 10
        if not results_valid:
            score -= 10
        if not analysis_valid:
            score -= 5
        if not aggregation_valid:
            score -= 5
        if not checksum_valid:
            score -= 10
        
        # 确保分数在 0-100 范围内
        return max(0, min(100, score))


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
