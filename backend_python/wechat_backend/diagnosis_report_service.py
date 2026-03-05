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

# P0 修复：导入字段转换器
from utils.field_converter import convert_response_to_camel


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
        db_logger.info(
            f"批量添加 {len(results)} 个诊断结果：{execution_id}, "
            f"batches={(len(results) + batch_size - 1) // batch_size}"
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

        # 2. 获取结果明细
        try:
            results = self.result_repo.get_by_execution_id(execution_id)
        except Exception as e:
            db_logger.error(f"查询结果失败：execution_id={execution_id}, 错误：{e}")
            results = []

        # P1-1 降级方案：结果为空时的处理
        if not results or len(results) == 0:
            db_logger.warning(f"报告结果为空：{execution_id}")
            # 检查是否有部分结果（可能正在执行中）
            progress = report.get('progress', 0)
            if progress > 0 and progress < 100:
                return self._create_partial_fallback_report(execution_id, report, progress)
            # 完全无结果
            return self._create_fallback_report(
                execution_id,
                '诊断已完成，但未生成有效结果',
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

        # 4. 计算品牌分布
        brand_distribution = self._calculate_brand_distribution(results)

        # 5. 计算情感分布
        sentiment_distribution = self._calculate_sentiment_distribution(results)

        # 6. 提取关键词
        keywords = self._extract_keywords(results)

        # P1-1 降级方案：验证数据质量，添加警告信息
        validation = self._validate_report_data(report, results, analysis_data)
        
        # 如果数据质量低，添加警告
        quality_warnings = self._check_data_quality(results, analysis_data)
        if quality_warnings:
            validation['warnings'].extend(quality_warnings)

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
                'suggestion': self._get_error_suggestion(error_type)
            },
            'meta': {
                'data_schema_version': DATA_SCHEMA_VERSION,
                'server_version': '2.0.0',
                'retrieved_at': datetime.now().isoformat()
            },
            'validation': {
                'is_valid': False,
                'errors': [error_message],
                'warnings': []
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
        P1-1 新增：确保分析数据完整（缺失时提供默认值）

        参数:
            analysis: 原始分析数据
            execution_id: 执行 ID（可选，用于日志）

        返回:
            完整的分析数据
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

        for analysis_type in required_analysis_types:
            if analysis_type in analysis and analysis[analysis_type]:
                complete_analysis[analysis_type] = analysis[analysis_type]
            else:
                complete_analysis[analysis_type] = self._get_default_analysis(analysis_type)
                missing_types.append(analysis_type)

        if missing_types and execution_id:
            db_logger.warning(f"分析数据缺失：{execution_id}, 缺失类型：{missing_types}")

        return complete_analysis

    def _get_default_analysis(self, analysis_type: str) -> Dict[str, Any]:
        """
        P1-1 新增：获取默认分析数据
        
        参数:
            analysis_type: 分析类型
        
        返回:
            默认分析数据
        """
        defaults = {
            'competitive_analysis': {
                'warning': '竞品分析数据暂缺',
                'data': {}
            },
            'brand_scores': {
                'warning': '品牌评分数据暂缺',
                'scores': {}
            },
            'semantic_drift': {
                'warning': '语义偏移数据暂缺',
                'drift_score': 0,
                'keywords': []
            },
            'source_purity': {
                'warning': '信源纯净度数据暂缺',
                'purity_score': 0,
                'sources': []
            },
            'recommendations': {
                'warning': '优化建议数据暂缺',
                'suggestions': []
            }
        }
        return defaults.get(analysis_type, {'warning': '数据暂缺', 'data': {}})

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

    def _calculate_brand_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算品牌分布数据

        参数:
            results: 结果列表

        返回:
            {
                data: {品牌名：数量，...},
                total_count: 总数
            }
        """
        distribution = {}
        for result in results:
            # P0 修复：检查结果是否为 None
            if not result:
                continue
            
            # P0 修复：安全获取 brand
            brand = result.get('brand', 'Unknown') if result else 'Unknown'
            distribution[brand] = distribution.get(brand, 0) + 1

        return {
            'data': distribution,
            'total_count': sum(distribution.values())
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
        提取关键词

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
            
            # P0 修复：安全获取 geo_data
            geo_data = result.get('geo_data') or {}
            
            # P0 修复：安全获取 keywords
            extracted_keywords = geo_data.get('keywords', []) if geo_data else []

            if extracted_keywords and isinstance(extracted_keywords, list):
                for kw in extracted_keywords:
                    word = kw.get('word', '') if isinstance(kw, dict) else str(kw)
                    if word and word not in seen:
                        keywords.append(kw if isinstance(kw, dict) else {'word': kw, 'count': 1})
                        seen.add(word)

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

        # P0 修复：转换为 camelCase
        return convert_response_to_camel({
            'reports': reports,
            'pagination': {
                'page': page,
                'limit': limit,
                'total': len(reports),  # 实际应该查询总数
                'has_more': len(reports) == limit
            }
        })
    
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
