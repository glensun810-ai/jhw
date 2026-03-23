"""
诊断报告数据转换器

职责：
1. 将后端格式转换为前端期望格式
2. 数据聚合和计算
3. 数据格式验证

作者：系统架构组
日期：2026-03-01
版本：1.0
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class ReportTransformer:
    """
    报告数据转换器
    将后端格式转换为前端期望格式
    """

    @staticmethod
    def transform_to_frontend_format(report: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换为前端格式

        参数:
            report: 后端返回的原始报告数据

        返回:
            前端期望的报告格式
        """
        if not report:
            return ReportTransformer._create_empty_report()

        return {
            # 报告主数据
            'report': report.get('report', {}),

            # 结果列表
            'results': report.get('results', []),

            # 分析数据（嵌套结构）
            'analysis': {
                'competitive_analysis': report.get('analysis', {}).get('competitive_analysis', {}),
                'brand_scores': report.get('analysis', {}).get('brand_scores', {}),
                'semantic_drift': report.get('analysis', {}).get('semantic_drift', {}),
                'source_purity': report.get('analysis', {}).get('source_purity', {}),
                'recommendations': report.get('analysis', {}).get('recommendations', {})
            },

            # P0-1 新增：前端需要的聚合数据
            'brandDistribution': ReportTransformer._calculate_brand_distribution(
                report.get('results', [])
            ),
            'sentimentDistribution': ReportTransformer._calculate_sentiment_distribution(
                report.get('results', [])
            ),
            'keywords': ReportTransformer._extract_keywords(
                report.get('results', [])
            ),

            # 元数据
            'meta': report.get('meta', {}),

            # 验证信息
            'validation': report.get('validation', {
                'is_valid': True,
                'errors': [],
                'warnings': []
            })
        }

    @staticmethod
    def _clean_brand_name(brand: str) -> str:
        """
        清理品牌名称（静态方法，便于前端格式转换时使用）
        
        清理规则：
        1. 去除前后空格
        2. 去除括号及括号内内容
        3. 去除常见后缀词
        4. 统一英文品牌大小写
        
        参数:
            brand: 原始品牌名称
            
        返回:
            清理后的品牌名称
        """
        if not brand or not str(brand).strip():
            return ''
        
        import re
        brand = str(brand).strip()
        
        # 去除括号及括号内内容
        brand = re.sub(r'\([^)]*\)', '', brand)
        brand = re.sub(r'（[^)]*）', '', brand)
        brand = re.sub(r'\[[^\]]*\]', '', brand)
        brand = re.sub(r'【[^\]]*】', '', brand)
        brand = brand.strip()
        
        # 去除常见后缀词
        suffixes = ['品牌', '公司', '汽车', '科技', '集团', 'Co.', 'Corp.', 'Inc.', 'Ltd.']
        for suffix in suffixes:
            if brand.endswith(suffix) and len(brand) > len(suffix) + 1:
                brand = brand[:-len(suffix)].strip()
        
        # 英文品牌首字母大写
        if brand.isascii():
            brand = brand.title()
        
        return brand.strip() if brand else ''

    @staticmethod
    def _calculate_brand_distribution(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算品牌分布数据（增强版 - 与 diagnosis_report_service 保持一致）
        
        核心改进：
        1. 优先使用 extracted_brand
        2. 品牌名称清理和标准化
        3. 多层降级：extracted_brand → brand → Unknown
        4. 确保始终返回有效数据

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
            if not result:
                continue

            brand = None

            # 层级 1: 优先使用 extracted_brand
            if not brand:
                extracted = result.get('extracted_brand')
                if extracted and str(extracted).strip():
                    cleaned = ReportTransformer._clean_brand_name(extracted)
                    if cleaned:
                        brand = cleaned

            # 层级 2: 使用 brand 字段
            if not brand:
                brand_val = result.get('brand')
                if brand_val and str(brand_val).strip():
                    cleaned = ReportTransformer._clean_brand_name(brand_val)
                    if cleaned:
                        brand = cleaned

            # 层级 3: 使用 'Unknown'
            if not brand:
                brand = 'Unknown'

            distribution[brand] = distribution.get(brand, 0) + 1

        # 确保 distribution 不为空
        if not distribution:
            distribution['Unknown'] = 0

        return {
            'data': distribution,
            'total_count': len(results) if results else 0
        }

    @staticmethod
    def _calculate_sentiment_distribution(results: List[Dict[str, Any]]) -> Dict[str, Any]:
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
            geo_data = result.get('geo_data', {})
            sentiment = geo_data.get('sentiment', 0)

            if sentiment > 0.3:
                sentiment_counts['positive'] += 1
            elif sentiment < -0.3:
                sentiment_counts['negative'] += 1
            else:
                sentiment_counts['neutral'] += 1

        return {
            'data': sentiment_counts,
            'total_count': len(results)
        }

    @staticmethod
    def _extract_keywords(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            geo_data = result.get('geo_data', {})
            extracted_keywords = geo_data.get('keywords', [])

            if extracted_keywords and isinstance(extracted_keywords, list):
                for kw in extracted_keywords:
                    word = kw.get('word', '') if isinstance(kw, dict) else str(kw)
                    if word and word not in seen:
                        keywords.append(kw if isinstance(kw, dict) else {'word': kw, 'count': 1})
                        seen.add(word)

        return keywords

    @staticmethod
    def _create_empty_report() -> Dict[str, Any]:
        """
        创建空报告数据结构

        返回:
            空报告
        """
        return {
            'report': {},
            'results': [],
            'analysis': {
                'competitive_analysis': {},
                'brand_scores': {},
                'semantic_drift': {},
                'source_purity': {},
                'recommendations': {}
            },
            'brandDistribution': {
                'data': {},
                'total_count': 0
            },
            'sentimentDistribution': {
                'data': {
                    'positive': 0,
                    'neutral': 0,
                    'negative': 0
                },
                'total_count': 0
            },
            'keywords': [],
            'meta': {
                'generated_at': datetime.now().isoformat(),
                'execution_id': '',
                'version': '2.0.0'
            },
            'validation': {
                'is_valid': False,
                'errors': ['报告不存在或为空'],
                'warnings': []
            }
        }

    @staticmethod
    def format_for_chart(data: Dict[str, Any], chart_type: str) -> List[Dict[str, Any]]:
        """
        格式化数据为图表格式

        参数:
            data: 原始数据
            chart_type: 图表类型 (pie, bar, line, word_cloud)

        返回:
            图表数据
        """
        if chart_type == 'pie':
            # 饼图数据格式
            return [
                {'name': name, 'value': value}
                for name, value in data.get('data', {}).items()
            ]

        elif chart_type == 'bar':
            # 柱状图数据格式
            return [
                {'name': name, 'value': value}
                for name, value in data.get('data', {}).items()
            ]

        elif chart_type == 'word_cloud':
            # 词云数据格式
            keywords = data if isinstance(data, list) else []
            max_count = max((kw.get('count', 1) for kw in keywords), default=1)
            min_count = min((kw.get('count', 1) for kw in keywords), default=1)

            formatted = []
            for kw in keywords:
                count = kw.get('count', 1)
                # 归一化大小（12-48 像素）
                normalized = 0.5 if max_count == min_count else (count - min_count) / (max_count - min_count)
                size = int(12 + normalized * 36)

                # 根据情感设置颜色
                sentiment = kw.get('sentiment', 0)
                if sentiment > 0.3:
                    color = '#28a745'  # 绿色（正面）
                elif sentiment < -0.3:
                    color = '#dc3545'  # 红色（负面）
                else:
                    color = '#6c757d'  # 灰色（中性）

                formatted.append({
                    'word': kw.get('word', ''),
                    'size': size,
                    'color': color,
                    'count': count,
                    'sentiment': sentiment
                })

            return formatted

        return []


# ==================== 工具函数 ====================

def get_server_version() -> str:
    """获取服务器版本号"""
    import os
    return os.getenv('SERVER_VERSION', '2.0.0')


def calculate_checksum(data: Dict[str, Any]) -> str:
    """计算数据 SHA256 校验和"""
    import json
    import hashlib
    json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(json_str.encode('utf-8')).hexdigest()


# ==================== 导出 ====================

__all__ = [
    'ReportTransformer',
    'get_server_version',
    'calculate_checksum'
]
