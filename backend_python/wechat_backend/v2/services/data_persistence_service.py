"""
数据持久化服务

将原始 AI 响应数据持久化到数据库，支持批量保存、GEO 分析集成。

作者：系统架构组
日期：2026-02-27
版本：2.0.0
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from wechat_backend.v2.models.diagnosis_result import DiagnosisResult
from wechat_backend.v2.repositories.diagnosis_result_repository import DiagnosisResultRepository
from wechat_backend.v2.analytics.geo_parser import GEOAnalyzer, GEOData
from wechat_backend.logging_config import api_logger
from wechat_backend.v2.exceptions import DataPersistenceError

logger = logging.getLogger(__name__)


class DataPersistenceService:
    """
    数据持久化服务
    
    职责：
    1. 将原始 AI 响应转换为 DiagnosisResult 对象
    2. 调用 GEO 解析器进行分析
    3. 批量保存结果到数据库
    4. 与诊断报告关联
    
    使用示例:
        >>> service = DataPersistenceService()
        >>> result_id = await service.save_ai_response(...)
        >>> result_ids = await service.save_batch_responses(...)
    """
    
    def __init__(
        self,
        result_repo: Optional[DiagnosisResultRepository] = None,
        geo_analyzer: Optional[GEOAnalyzer] = None,
    ):
        """
        初始化数据持久化服务
        
        Args:
            result_repo: 结果仓库实例（可选）
            geo_analyzer: GEO 分析器实例（可选）
        """
        self.result_repo = result_repo or DiagnosisResultRepository()
        self.geo_analyzer = geo_analyzer or GEOAnalyzer()
        
        api_logger.info(
            "data_persistence_service_initialized",
            extra={
                'event': 'data_persistence_service_initialized',
            }
        )
    
    async def save_ai_response(
        self,
        execution_id: str,
        report_id: int,
        brand: str,
        question: str,
        model: str,
        response: Dict[str, Any],
        latency_ms: int,
        error_message: Optional[str] = None,
    ) -> int:
        """
        保存单个 AI 响应
        
        流程：
        1. 提取响应文本
        2. 进行 GEO 分析
        3. 创建 DiagnosisResult 对象
        4. 保存到数据库
        
        Args:
            execution_id: 执行 ID
            report_id: 报告 ID
            brand: 品牌名称
            question: 问题内容
            model: AI 模型名称
            response: AI 响应数据
            latency_ms: 延迟（毫秒）
            error_message: 错误信息（可选）
        
        Returns:
            int: 结果记录 ID
        
        Raises:
            DataPersistenceError: 保存失败
        """
        try:
            # 提取响应文本
            response_text = self._extract_response_text(response)
            
            # 进行 GEO 分析（如果没有错误）
            geo_data = None
            exposure = False
            sentiment = 'neutral'
            keywords = []
            
            if not error_message and response_text:
                geo_result = self.geo_analyzer.analyze(
                    response_text=response_text,
                    brand_name=brand,
                )
                geo_data = {
                    'confidence': geo_result.confidence,
                    'details': geo_result.details,
                }
                exposure = geo_result.exposure
                sentiment = geo_result.sentiment
                keywords = geo_result.keywords
            
            # 创建结果对象
            result = DiagnosisResult(
                report_id=report_id,
                execution_id=execution_id,
                brand=brand,
                question=question,
                model=model,
                response=response,
                response_text=response_text,
                geo_data=geo_data,
                exposure=exposure,
                sentiment=sentiment,
                keywords=keywords,
                latency_ms=latency_ms,
                error_message=error_message,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            
            # 保存到数据库
            result_id = self.result_repo.create(result)
            
            api_logger.info(
                "ai_response_saved",
                extra={
                    'event': 'ai_response_saved',
                    'result_id': result_id,
                    'execution_id': execution_id,
                    'report_id': report_id,
                    'brand': brand,
                    'model': model,
                    'has_error': error_message is not None,
                    'exposure': exposure,
                    'sentiment': sentiment,
                }
            )
            
            return result_id
            
        except Exception as e:
            api_logger.error(
                "ai_response_save_failed",
                extra={
                    'event': 'ai_response_save_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DataPersistenceError(f"保存 AI 响应失败：{e}") from e
    
    async def save_batch_responses(
        self,
        execution_id: str,
        report_id: int,
        responses: List[Dict[str, Any]],
    ) -> List[int]:
        """
        批量保存多个 AI 响应
        
        Args:
            execution_id: 执行 ID
            report_id: 报告 ID
            responses: 响应列表，每个元素包含：
                - brand: 品牌名称
                - question: 问题内容
                - model: AI 模型名称
                - response: AI 响应数据
                - latency_ms: 延迟（可选）
                - error_message: 错误信息（可选）
        
        Returns:
            List[int]: 结果记录 ID 列表
        
        Raises:
            DataPersistenceError: 批量保存失败
        """
        try:
            results = []
            
            for resp in responses:
                # 提取响应文本
                response_text = self._extract_response_text(resp.get('response', {}))
                
                # 进行 GEO 分析（如果没有错误）
                geo_data = None
                exposure = False
                sentiment = 'neutral'
                keywords = []
                
                if not resp.get('error_message') and response_text:
                    geo_result = self.geo_analyzer.analyze(
                        response_text=response_text,
                        brand_name=resp['brand'],
                    )
                    geo_data = {
                        'confidence': geo_result.confidence,
                        'details': geo_result.details,
                    }
                    exposure = geo_result.exposure
                    sentiment = geo_result.sentiment
                    keywords = geo_result.keywords
                
                # 创建结果对象
                result = DiagnosisResult(
                    report_id=report_id,
                    execution_id=execution_id,
                    brand=resp['brand'],
                    question=resp['question'],
                    model=resp['model'],
                    response=resp.get('response', {}),
                    response_text=response_text,
                    geo_data=geo_data,
                    exposure=exposure,
                    sentiment=sentiment,
                    keywords=keywords,
                    latency_ms=resp.get('latency_ms'),
                    error_message=resp.get('error_message'),
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                
                results.append(result)
            
            # 批量保存
            ids = self.result_repo.create_many(results)
            
            api_logger.info(
                "batch_responses_saved",
                extra={
                    'event': 'batch_responses_saved',
                    'execution_id': execution_id,
                    'report_id': report_id,
                    'count': len(ids),
                }
            )
            
            return ids
            
        except Exception as e:
            api_logger.error(
                "batch_responses_save_failed",
                extra={
                    'event': 'batch_responses_save_failed',
                    'execution_id': execution_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                }
            )
            raise DataPersistenceError(f"批量保存响应失败：{e}") from e
    
    def get_results_for_report(
        self,
        report_id: int,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DiagnosisResult]:
        """
        获取报告的所有结果
        
        Args:
            report_id: 报告 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[DiagnosisResult]: 结果列表
        """
        return self.result_repo.get_by_report_id(report_id, limit, offset)
    
    def get_results_for_execution(
        self,
        execution_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[DiagnosisResult]:
        """
        获取执行的所有结果
        
        Args:
            execution_id: 执行 ID
            limit: 每页数量
            offset: 偏移量
        
        Returns:
            List[DiagnosisResult]: 结果列表
        """
        return self.result_repo.get_by_execution_id(execution_id, limit, offset)
    
    def update_analysis(
        self,
        result_id: int,
        geo_data: Dict[str, Any],
        exposure: bool,
        sentiment: str,
        keywords: List[str],
    ) -> bool:
        """
        更新分析结果
        
        Args:
            result_id: 结果 ID
            geo_data: GEO 分析数据
            exposure: 是否露出
            sentiment: 情感倾向
            keywords: 关键词列表
        
        Returns:
            bool: 是否更新成功
        """
        return self.result_repo.update_geo_data(
            result_id, geo_data, exposure, sentiment, keywords,
        )
    
    def get_statistics(self, report_id: int) -> Dict[str, Any]:
        """
        获取报告的统计信息
        
        Args:
            report_id: 报告 ID
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        return self.result_repo.get_statistics(report_id)
    
    def _extract_response_text(self, response: Dict[str, Any]) -> Optional[str]:
        """
        从不同 AI 平台的响应中提取文本内容
        
        处理不同平台的响应格式差异。
        
        Args:
            response: AI 响应数据
        
        Returns:
            Optional[str]: 提取的文本内容
        """
        try:
            if not response:
                return None
            
            # DeepSeek/GPT 格式
            if 'choices' in response:
                choices = response['choices']
                if choices and len(choices) > 0:
                    if 'message' in choices[0]:
                        return choices[0]['message'].get('content', '')
                    elif 'text' in choices[0]:
                        return choices[0].get('text', '')
            
            # 豆包格式
            if 'data' in response and 'content' in response['data']:
                return response['data']['content']
            
            # 通义千问格式
            if 'output' in response and 'text' in response['output']:
                return response['output']['text']
            
            # 通用：尝试直接取 content 字段
            if 'content' in response:
                return response['content']
            
            # 如果都没找到，返回整个响应的字符串表示
            import json
            return json.dumps(response, ensure_ascii=False)
            
        except Exception as e:
            logger.warning(f"Failed to extract response text: {e}")
            return None
