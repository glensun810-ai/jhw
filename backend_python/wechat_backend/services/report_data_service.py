#!/usr/bin/env python3
"""
报告数据聚合服务
负责从各数据源聚合完整的报告数据

版本：v2.0
日期：2026-02-21
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from wechat_backend.logging_config import api_logger
from wechat_backend.database import get_connection


class ReportDataService:
    """
    报告数据聚合服务
    负责从各数据源聚合完整的报告数据
    """
    
    def __init__(self):
        self.logger = api_logger
        self.db = None

    def _get_db_connection(self):
        """获取数据库连接"""
        if self.db is None:
            # get_connection 返回上下文管理器，需要获取实际连接
            from wechat_backend.database_core import get_connection as get_db_conn
            import sqlite3
            
            # 直接使用 sqlite3 连接
            db_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/database.db'
            self.db = sqlite3.connect(db_path)
        return self.db
    
    def generate_full_report(self, execution_id: str) -> Dict[str, Any]:
        """
        生成完整报告数据
        
        Args:
            execution_id: 执行 ID
        
        Returns:
            完整报告数据字典
        """
        start_time = time.time()
        self.logger.info(f"开始生成完整报告数据：execution_id={execution_id}")
        
        try:
            # 1. 获取基础诊断数据
            base_data = self._get_base_data(execution_id)
            
            if not base_data:
                raise ValueError(f"未找到执行 ID 对应的数据：{execution_id}")
            
            # 2. 获取或生成竞品对比数据
            competitive_data = self._get_or_generate_competitive_data(execution_id, base_data)
            
            # 3. 获取或生成负面信源数据
            negative_sources = self._get_or_generate_negative_sources(execution_id, base_data)
            
            # 4. 计算 ROI 指标（使用增强的 ROI 计算器）
            from wechat_backend.services.roi_calculator import get_roi_calculator
            roi_metrics = get_roi_calculator().calculate_roi({
                'reportMetadata': {'brandName': base_data.get('brand_name', '未知品牌')},
                'brandHealth': base_data,
                'platformAnalysis': base_data.get('platform_scores', []),
                'negativeSources': negative_sources
            })

            # 5. 生成行动建议（使用增强的行动计划生成器）
            from wechat_backend.services.action_plan_generator import get_action_plan_generator
            action_plan = get_action_plan_generator().generate_action_plan({
                'reportMetadata': {'brandName': base_data.get('brand_name', '未知品牌')},
                'brandHealth': base_data,
                'competitiveAnalysis': competitive_data,
                'negativeSources': negative_sources,
                'roiAnalysis': roi_metrics
            })
            
            # 6. 生成执行摘要
            executive_summary = self._generate_executive_summary(
                base_data, 
                competitive_data, 
                negative_sources,
                roi_metrics,
                action_plan
            )
            
            # 7. 保存到数据库
            self._save_report_data(
                execution_id,
                competitive_data,
                negative_sources,
                roi_metrics,
                action_plan,
                executive_summary
            )
            
            generation_time = time.time() - start_time
            self.logger.info(f"完整报告数据生成完成：execution_id={execution_id}, time={generation_time:.2f}s")
            
            return {
                "reportMetadata": {
                    "executionId": execution_id,
                    "generatedAt": datetime.now().isoformat(),
                    "reportVersion": "2.0",
                    "brandName": base_data.get('brand_name', '未知品牌'),
                    "generationTimeMs": int(generation_time * 1000)
                },
                "executiveSummary": executive_summary,
                "brandHealth": base_data,
                "platformAnalysis": base_data.get('platform_scores', []),
                "competitiveAnalysis": competitive_data,
                "negativeSources": negative_sources,
                "roiAnalysis": roi_metrics,
                "actionPlan": action_plan
            }
            
        except Exception as e:
            self.logger.error(f"生成完整报告数据失败：{e}", exc_info=True)
            raise
    
    def _get_base_data(self, execution_id: str) -> Dict[str, Any]:
        """获取基础诊断数据"""
        import gzip

        conn = self._get_db_connection()
        cursor = conn.cursor()

        # 修复 1: 从 test_records 表获取（实际存在的表）
        # 修复 2: 从 results_summary 中提取 execution_id 进行匹配
        # 修复 3: 使用 test_date 替代 created_at 排序
        cursor.execute("""
            SELECT id, user_id, brand_name, test_date, ai_models_used, questions_used,
                   overall_score, total_tests, results_summary, detailed_results,
                   is_summary_compressed, is_detailed_compressed
            FROM test_records
            ORDER BY test_date DESC
            LIMIT 10
        """)

        rows = cursor.fetchall()
        
        if not rows:
            # 尝试从 deep_intelligence_results 获取
            cursor.execute("""
                SELECT task_id, exposure_analysis, source_intelligence, evidence_chain
                FROM deep_intelligence_results
                WHERE task_id = ?
                LIMIT 1
            """, (execution_id,))
            row = cursor.fetchone()

            if not row:
                return {}

            # 从 deep_intelligence_results 构建基础数据
            columns = [description[0] for description in cursor.description]
            deep_data = dict(zip(columns, row))
            
            # 解析 JSON 字段
            for field in ['exposure_analysis', 'source_intelligence', 'evidence_chain']:
                try:
                    if deep_data.get(field):
                        deep_data[field] = json.loads(deep_data[field])
                except (json.JSONDecodeError, TypeError):
                    deep_data[field] = {} if field in ['exposure_analysis', 'source_intelligence'] else []
            
            return {
                'execution_id': deep_data.get('task_id', execution_id),
                'exposure_analysis': deep_data.get('exposure_analysis', {}),
                'source_intelligence': deep_data.get('source_intelligence', {}),
                'evidence_chain': deep_data.get('evidence_chain', []),
                'overall_score': 0,
                'brand_name': '未知品牌'
            }

        # 修复 3: 查找匹配 execution_id 的记录（从 results_summary 中提取）
        for row in rows:
            columns = [description[0] for description in cursor.description]
            record_data = dict(zip(columns, row))
            
            # 解析 results_summary（可能需要解压）
            results_summary_raw = record_data.get('results_summary')
            is_compressed = record_data.get('is_summary_compressed', 0)
            
            try:
                if is_compressed and results_summary_raw:
                    # 解压缩数据
                    results_summary_bytes = gzip.decompress(results_summary_raw)
                    results_summary = json.loads(results_summary_bytes.decode('utf-8'))
                elif results_summary_raw:
                    results_summary = json.loads(results_summary_raw)
                else:
                    results_summary = {}
            except (json.JSONDecodeError, TypeError, gzip.BadGzipFile) as e:
                self.logger.warning(f"解析 results_summary 失败：{e}")
                results_summary = {}
            
            # 检查是否匹配 execution_id
            summary_exec_id = results_summary.get('execution_id', '')
            if summary_exec_id == execution_id or not execution_id:
                # 解析 detailed_results（可能需要解压）
                detailed_results_raw = record_data.get('detailed_results')
                is_detailed_compressed = record_data.get('is_detailed_compressed', 0)
                
                try:
                    if is_detailed_compressed and detailed_results_raw:
                        detailed_results_bytes = gzip.decompress(detailed_results_raw)
                        detailed_results = json.loads(detailed_results_bytes.decode('utf-8'))
                    elif detailed_results_raw:
                        detailed_results = json.loads(detailed_results_raw)
                    else:
                        detailed_results = []
                except (json.JSONDecodeError, TypeError, gzip.BadGzipFile) as e:
                    self.logger.warning(f"解析 detailed_results 失败：{e}")
                    detailed_results = []

                # 解析其他 JSON 字段
                ai_models_used = record_data.get('ai_models_used', '[]')
                questions_used = record_data.get('questions_used', '[]')
                
                try:
                    ai_models_used = json.loads(ai_models_used) if ai_models_used else []
                    questions_used = json.loads(questions_used) if questions_used else []
                except (json.JSONDecodeError, TypeError):
                    ai_models_used = []
                    questions_used = []

                # 构建完整的 base_data
                base_data = {
                    'execution_id': summary_exec_id or execution_id,
                    'result_id': record_data.get('id'),
                    'brand_name': record_data.get('brand_name', '未知品牌'),
                    'test_date': record_data.get('test_date', ''),
                    'ai_models_used': ai_models_used,
                    'questions_used': questions_used,
                    'overall_score': record_data.get('overall_score', 0) or 0,
                    'total_tests': record_data.get('total_tests', 0) or 0,
                    'results_summary': results_summary,
                    'detailed_results': detailed_results,
                    'is_summary_compressed': is_compressed,
                    'is_detailed_compressed': is_detailed_compressed
                }

                # 构建平台评分
                base_data['platform_scores'] = self._build_platform_scores(base_data)

                # 构建维度评分
                base_data['dimension_scores'] = self._build_dimension_scores(base_data)

                return base_data

        # 如果没有找到匹配的 execution_id，返回空
        return {}
    
    def _build_platform_scores(self, base_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """构建平台评分列表"""
        platform_scores = []
        
        # 从 detailed_results 中提取
        detailed_results = base_data.get('detailed_results', [])
        
        if isinstance(detailed_results, list):
            for result in detailed_results:
                if isinstance(result, dict):
                    platform_scores.append({
                        'platform': result.get('model', result.get('platform', 'Unknown')),
                        'score': result.get('score', result.get('overall_score', 0)),
                        'rank': result.get('rank', 0),
                        'sentiment': result.get('sentiment', 0)
                    })
        
        return platform_scores
    
    def _build_dimension_scores(self, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建维度评分"""
        return {
            'authority': base_data.get('authority_score', 75),
            'visibility': base_data.get('visibility_score', 70),
            'purity': base_data.get('purity_score', 80),
            'consistency': base_data.get('consistency_score', 75)
        }
    
    def _get_or_generate_competitive_data(self, execution_id: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取或生成竞品对比数据"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT * FROM competitive_analysis 
            WHERE execution_id = ?
        """, (execution_id,))
        
        rows = cursor.fetchall()
        
        if rows:
            # 返回已存在的竞品数据
            competitors = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                competitor = dict(zip(columns, row))
                # 解析 JSON 字段
                for field in ['platform_scores', 'strengths', 'weaknesses', 'opportunities', 'threats']:
                    try:
                        if competitor.get(field):
                            competitor[field] = json.loads(competitor[field])
                    except:
                        competitor[field] = []
                competitors.append(competitor)
            
            return {
                'competitors': competitors,
                'radar_data': self._build_radar_data(base_data, competitors),
                'comparison_summary': self._generate_comparison_summary(base_data, competitors)
            }
        
        # 生成模拟竞品数据（实际应调用 AI 分析）
        competitors = self._generate_mock_competitors(base_data)
        
        return {
            'competitors': competitors,
            'radar_data': self._build_radar_data(base_data, competitors),
            'comparison_summary': self._generate_comparison_summary(base_data, competitors),
            'is_mock': True  # 标记为模拟数据
        }
    
    def _generate_mock_competitors(self, base_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成模拟竞品数据"""
        import random
        
        brand_name = base_data.get('brand_name', '品牌')
        base_score = base_data.get('overall_score', 75)
        
        # 生成 3 个竞品
        competitor_names = [
            f'竞品 A',
            f'竞品 B',
            f'竞品 C'
        ]
        
        competitors = []
        for i, name in enumerate(competitor_names):
            # 分数在基础分数上下浮动
            variance = random.uniform(-15, 15)
            overall_score = min(100, max(0, base_score + variance))
            
            competitor = {
                'competitor_name': name,
                'overall_score': round(overall_score, 1),
                'authority_score': round(overall_score + random.uniform(-10, 10), 1),
                'visibility_score': round(overall_score + random.uniform(-10, 10), 1),
                'purity_score': round(overall_score + random.uniform(-10, 10), 1),
                'consistency_score': round(overall_score + random.uniform(-10, 10), 1),
                'platform_scores': [],
                'strengths': [f'{name}的优势 1', f'{name}的优势 2'],
                'weaknesses': [f'{name}的劣势 1'],
                'opportunities': [],
                'threats': []
            }
            
            competitors.append(competitor)
        
        return competitors
    
    def _build_radar_data(self, base_data: Dict[str, Any], competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建雷达图数据"""
        dimensions = ['authority', 'visibility', 'purity', 'consistency', 'overall']
        
        radar_data = {
            'dimensions': dimensions,
            'datasets': [
                {
                    'label': base_data.get('brand_name', '我方品牌'),
                    'data': [
                        base_data.get('authority_score', 75),
                        base_data.get('visibility_score', 70),
                        base_data.get('purity_score', 80),
                        base_data.get('consistency_score', 75),
                        base_data.get('overall_score', 75)
                    ],
                    'borderColor': 'rgb(255, 99, 132)',
                    'backgroundColor': 'rgba(255, 99, 132, 0.2)'
                }
            ]
        }
        
        # 添加竞品数据
        colors = [
            ('rgb(54, 162, 235)', 'rgba(54, 162, 235, 0.2)'),
            ('rgb(255, 206, 86)', 'rgba(255, 206, 86, 0.2)'),
            ('rgb(75, 192, 192)', 'rgba(75, 192, 192, 0.2)')
        ]
        
        for i, competitor in enumerate(competitors):
            color = colors[i % len(colors)]
            radar_data['datasets'].append({
                'label': competitor['competitor_name'],
                'data': [
                    competitor.get('authority_score', 75),
                    competitor.get('visibility_score', 75),
                    competitor.get('purity_score', 75),
                    competitor.get('consistency_score', 75),
                    competitor.get('overall_score', 75)
                ],
                'borderColor': color[0],
                'backgroundColor': color[1]
            })
        
        return radar_data
    
    def _generate_comparison_summary(self, base_data: Dict[str, Any], competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成对比摘要"""
        my_score = base_data.get('overall_score', 75)
        
        # 计算排名
        all_scores = [(base_data.get('brand_name', '我方品牌'), my_score)]
        for comp in competitors:
            all_scores.append((comp['competitor_name'], comp['overall_score']))
        
        all_scores.sort(key=lambda x: x[1], reverse=True)
        my_rank = next(i for i, (name, score) in enumerate(all_scores) if name == base_data.get('brand_name', '我方品牌')) + 1
        
        # 计算差距
        leader_score = all_scores[0][1]
        gap_to_leader = leader_score - my_score
        
        return {
            'my_rank': my_rank,
            'total_competitors': len(competitors),
            'leader': all_scores[0][0],
            'leader_score': leader_score,
            'gap_to_leader': round(gap_to_leader, 1),
            'average_competitor_score': round(sum(s for _, s in all_scores[1:]) / len(all_scores[1:]), 1) if len(all_scores) > 1 else 0
        }
    
    def _get_or_generate_negative_sources(self, execution_id: str, base_data: Dict[str, Any]) -> Dict[str, Any]:
        """获取或生成负面信源数据"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # 检查是否已存在
        cursor.execute("""
            SELECT * FROM negative_sources 
            WHERE execution_id = ?
            ORDER BY priority_score DESC
        """, (execution_id,))
        
        rows = cursor.fetchall()
        
        if rows:
            sources = []
            for row in rows:
                columns = [description[0] for description in cursor.description]
                source = dict(zip(columns, row))
                sources.append(source)
            
            return {
                'sources': sources,
                'summary': self._generate_negative_source_summary(sources)
            }
        
        # 生成模拟负面信源数据
        sources = self._generate_mock_negative_sources(base_data)
        
        return {
            'sources': sources,
            'summary': self._generate_negative_source_summary(sources),
            'is_mock': True
        }
    
    def _generate_mock_negative_sources(self, base_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成模拟负面信源数据"""
        brand_name = base_data.get('brand_name', '品牌')
        
        sources = [
            {
                'source_name': '知乎专栏',
                'source_url': 'https://zhuanlan.zhihu.com/p/example1',
                'source_type': 'article',
                'content_summary': f'用户对{brand_name}的产品质量提出质疑',
                'sentiment_score': -0.6,
                'severity': 'high',
                'impact_scope': 'medium',
                'estimated_reach': 50000,
                'discovered_at': datetime.now().isoformat(),
                'recommendation': '官方回应 + SEO 优化',
                'priority_score': 85,
                'status': 'pending'
            },
            {
                'source_name': '小红书笔记',
                'source_url': 'https://xiaohongshu.com/example2',
                'source_type': 'social_media',
                'content_summary': f'博主分享{brand_name}的负面使用体验',
                'sentiment_score': -0.4,
                'severity': 'medium',
                'impact_scope': 'medium',
                'estimated_reach': 20000,
                'discovered_at': datetime.now().isoformat(),
                'recommendation': '联系博主沟通 + 改进服务',
                'priority_score': 70,
                'status': 'pending'
            },
            {
                'source_name': '百度百科',
                'source_url': 'https://baike.baidu.com/example3',
                'source_type': 'encyclopedia',
                'content_summary': f'{brand_name}词条包含过时信息',
                'sentiment_score': -0.2,
                'severity': 'low',
                'impact_scope': 'high',
                'estimated_reach': 100000,
                'discovered_at': datetime.now().isoformat(),
                'recommendation': '申请编辑更新',
                'priority_score': 55,
                'status': 'pending'
            }
        ]
        
        return sources
    
    def _generate_negative_source_summary(self, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成负面信源摘要"""
        if not sources:
            return {
                'total_count': 0,
                'critical_count': 0,
                'high_count': 0,
                'medium_count': 0,
                'low_count': 0,
                'avg_sentiment': 0,
                'total_estimated_reach': 0
            }
        
        severity_counts = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        for source in sources:
            severity = source.get('severity', 'low')
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        avg_sentiment = sum(s.get('sentiment_score', 0) for s in sources) / len(sources)
        total_reach = sum(s.get('estimated_reach', 0) for s in sources)
        
        return {
            'total_count': len(sources),
            'critical_count': severity_counts.get('critical', 0),
            'high_count': severity_counts.get('high', 0),
            'medium_count': severity_counts.get('medium', 0),
            'low_count': severity_counts.get('low', 0),
            'avg_sentiment': round(avg_sentiment, 2),
            'total_estimated_reach': total_reach
        }
    
    def _calculate_roi(self, base_data: Dict[str, Any], competitive_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算 ROI 指标"""
        # 从基础数据计算 ROI
        overall_score = base_data.get('overall_score', 75)
        platform_scores = base_data.get('platform_scores', [])
        
        # 估算曝光 ROI
        total_mentions = len(platform_scores) * 10  # 简化计算
        estimated_value = total_mentions * 50  # 每次曝光估算价值 50 元
        exposure_roi = round(estimated_value / 1000, 2)  # 假设投入 1000 元
        
        # 情感 ROI
        avg_sentiment = sum(p.get('sentiment', 0) for p in platform_scores) / len(platform_scores) if platform_scores else 0
        sentiment_roi = round((avg_sentiment + 1) * 0.5, 2)  # 归一化到 0-1
        
        # 排名 ROI
        avg_rank = sum(p.get('rank', 10) for p in platform_scores) / len(platform_scores) if platform_scores else 10
        ranking_roi = round(max(0, 100 - avg_rank * 5), 1)
        
        # 综合 ROI
        overall_roi = round((exposure_roi * 0.4 + sentiment_roi * 100 * 0.3 + ranking_roi * 0.3), 1)
        
        # 确定等级
        if overall_roi >= 80:
            roi_grade = 'A+'
        elif overall_roi >= 70:
            roi_grade = 'A'
        elif overall_roi >= 60:
            roi_grade = 'B'
        elif overall_roi >= 50:
            roi_grade = 'C'
        else:
            roi_grade = 'D'
        
        # 行业基准对比
        industry_avg_exposure = 2.5
        industry_avg_sentiment = 0.6
        industry_avg_ranking = 50
        
        return {
            'exposure_roi': exposure_roi,
            'total_impressions': total_mentions,
            'estimated_value': estimated_value,
            'sentiment_roi': sentiment_roi,
            'positive_mentions': int(total_mentions * (avg_sentiment + 1) / 2),
            'negative_mentions': int(total_mentions * (1 - avg_sentiment) / 2),
            'neutral_mentions': int(total_mentions * 0.2),
            'sentiment_score': round(avg_sentiment, 2),
            'ranking_roi': ranking_roi,
            'avg_ranking': round(avg_rank, 1),
            'top_3_count': sum(1 for p in platform_scores if p.get('rank', 10) <= 3),
            'top_10_count': sum(1 for p in platform_scores if p.get('rank', 10) <= 10),
            'overall_roi': overall_roi,
            'roi_grade': roi_grade,
            'industry_comparison': {
                'exposure_roi_vs_industry': round(exposure_roi - industry_avg_exposure, 2),
                'sentiment_roi_vs_industry': round(sentiment_roi - industry_avg_sentiment, 2),
                'ranking_roi_vs_industry': round(ranking_roi - industry_avg_ranking, 1)
            }
        }
    
    def _generate_action_plan(self, base_data: Dict[str, Any], competitive_data: Dict[str, Any],
                             negative_sources: Dict[str, Any], roi_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """生成行动计划"""
        brand_name = base_data.get('brand_name', '品牌')
        overall_score = base_data.get('overall_score', 75)
        
        # 短期行动 (1-4 周)
        short_term = []
        
        # 根据负面信源生成紧急行动
        for source in negative_sources.get('sources', [])[:2]:
            if source.get('severity') in ['critical', 'high']:
                short_term.append({
                    'title': f"处理{source['source_name']}负面内容",
                    'description': source.get('recommendation', '采取应对措施'),
                    'category': 'pr',
                    'phase': 'short_term',
                    'start_week': 1,
                    'duration_weeks': 2,
                    'estimated_hours': 20,
                    'priority': 'critical',
                    'priority_score': 95,
                    'expected_outcome': '降低负面影响',
                    'action_steps': [
                        '监测负面内容传播情况',
                        '准备官方回应声明',
                        '联系平台方沟通处理',
                        '跟踪处理结果'
                    ]
                })
        
        # 中期行动 (1-3 月)
        mid_term = [
            {
                'title': f'加强{brand_name}在主流 AI 平台的内容覆盖',
                'description': '提升品牌在 AI 搜索中的可见性',
                'category': 'content',
                'phase': 'mid_term',
                'start_week': 5,
                'duration_weeks': 8,
                'estimated_hours': 80,
                'priority': 'high',
                'priority_score': 85,
                'expected_outcome': '提升可见性评分 10-15 分',
                'action_steps': [
                    '分析各 AI 平台内容偏好',
                    '制定内容优化策略',
                    '创建高质量品牌内容',
                    '持续监测和优化'
                ]
            },
            {
                'title': '建立 AI 搜索品牌监测机制',
                'description': '定期监测品牌在 AI 搜索中的表现',
                'category': 'monitoring',
                'phase': 'mid_term',
                'start_week': 6,
                'duration_weeks': 4,
                'estimated_hours': 40,
                'priority': 'medium',
                'priority_score': 75,
                'expected_outcome': '建立常态化监测体系',
                'action_steps': [
                    '选择监测工具',
                    '设置监测指标',
                    '建立报告机制',
                    '培训相关人员'
                ]
            }
        ]
        
        # 长期行动 (3-6 月)
        long_term = [
            {
                'title': f'制定{brand_name}GEO 优化战略',
                'description': '制定系统的生成式引擎优化战略',
                'category': 'strategy',
                'phase': 'long_term',
                'start_week': 13,
                'duration_weeks': 12,
                'estimated_hours': 120,
                'priority': 'medium',
                'priority_score': 70,
                'expected_outcome': '建立 GEO 优化体系',
                'action_steps': [
                    '调研行业最佳实践',
                    '制定 GEO 战略框架',
                    '分配资源和预算',
                    '实施和迭代优化'
                ]
            }
        ]
        
        # 计算总体资源需求
        all_actions = short_term + mid_term + long_term
        total_hours = sum(a.get('estimated_hours', 0) for a in all_actions)
        total_budget = total_hours * 500  # 假设每小时 500 元
        
        return {
            'short_term': short_term,
            'mid_term': mid_term,
            'long_term': long_term,
            'all_actions': all_actions,
            'summary': {
                'total_actions': len(all_actions),
                'short_term_count': len(short_term),
                'mid_term_count': len(mid_term),
                'long_term_count': len(long_term),
                'total_estimated_hours': total_hours,
                'total_estimated_budget': total_budget,
                'expected_score_improvement': min(20, overall_score * 0.2)  # 预期提升最多 20 分或 20%
            }
        }
    
    def _generate_executive_summary(self, base_data: Dict[str, Any], competitive_data: Dict[str, Any],
                                   negative_sources: Dict[str, Any], roi_metrics: Dict[str, Any],
                                   action_plan: Dict[str, Any]) -> Dict[str, Any]:
        """生成执行摘要"""
        brand_name = base_data.get('brand_name', '品牌')
        overall_score = base_data.get('overall_score', 75)
        
        # 确定健康等级
        if overall_score >= 90:
            health_grade = 'A+'
        elif overall_score >= 80:
            health_grade = 'A'
        elif overall_score >= 70:
            health_grade = 'B'
        elif overall_score >= 60:
            health_grade = 'C'
        else:
            health_grade = 'D'
        
        # 核心发现 (3-5 条)
        key_findings = []
        
        # 优势
        if overall_score >= 75:
            key_findings.append(f"{brand_name}品牌健康度良好，总体评分{overall_score}分")
        
        # 竞品对比
        comp_summary = competitive_data.get('comparison_summary', {})
        if comp_summary.get('my_rank', 1) <= 2:
            key_findings.append(f"在竞品对比中排名第{comp_summary.get('my_rank', 1)}位，处于领先地位")
        else:
            key_findings.append(f"在竞品对比中排名第{comp_summary.get('my_rank', 1)}位，需加强竞争力")
        
        # 负面信源
        neg_summary = negative_sources.get('summary', {})
        if neg_summary.get('high_count', 0) + neg_summary.get('critical_count', 0) > 0:
            key_findings.append(f"发现{neg_summary.get('high_count', 0) + neg_summary.get('critical_count', 0)}个高风险负面信源，需立即处理")
        
        # ROI
        if roi_metrics.get('overall_roi', 0) >= 70:
            key_findings.append(f"ROI 表现优秀，综合 ROI 评分{roi_metrics.get('overall_roi', 0)}")
        
        # 主要优势
        top_strengths = []
        platform_scores = base_data.get('platform_scores', [])
        if platform_scores:
            best_platform = max(platform_scores, key=lambda x: x.get('score', 0))
            top_strengths.append(f"在{best_platform.get('platform', '某平台')}表现优异")
        
        dimension_scores = base_data.get('dimension_scores', {})
        best_dimension = max(dimension_scores.items(), key=lambda x: x[1])
        top_strengths.append(f"{best_dimension[0]}维度表现突出")
        
        # 主要关注点
        top_concerns = []
        if neg_summary.get('total_count', 0) > 0:
            top_concerns.append("负面信源需要及时处理")
        if comp_summary.get('gap_to_leader', 0) > 10:
            top_concerns.append(f"与行业领导者差距{comp_summary.get('gap_to_leader', 0)}分")
        
        # 优先级建议
        priority_recommendations = []
        if neg_summary.get('high_count', 0) + neg_summary.get('critical_count', 0) > 0:
            priority_recommendations.append({
                'priority': 'critical',
                'action': '立即处理高风险负面信源',
                'timeline': '1-2 周内'
            })
        
        if comp_summary.get('gap_to_leader', 0) > 5:
            priority_recommendations.append({
                'priority': 'high',
                'action': '加强竞品薄弱环节的内容覆盖',
                'timeline': '1 个月内'
            })
        
        priority_recommendations.append({
            'priority': 'medium',
            'action': '建立常态化品牌监测机制',
            'timeline': '2 个月内'
        })
        
        # 快速见效行动
        quick_wins = [
            "优化百度百科等权威平台品牌信息",
            "回应知乎等平台的负面评论",
            "增加主流 AI 平台品牌内容曝光"
        ]
        
        # 估算品牌价值
        estimated_value = roi_metrics.get('estimated_value', 0) * 12  # 年价值
        
        return {
            'overall_health_score': overall_score,
            'health_grade': health_grade,
            'score_change': 0,  # 首次报告，无变化
            'key_findings': key_findings[:5],  # 最多 5 条
            'top_strengths': top_strengths,
            'top_concerns': top_concerns,
            'top_risks': [s['source_name'] for s in negative_sources.get('sources', [])[:3] if s.get('severity') in ['critical', 'high']],
            'priority_recommendations': priority_recommendations,
            'quick_wins': quick_wins,
            'strategic_initiatives': [
                "制定 GEO 优化战略",
                "建立品牌声誉管理体系",
                "持续优化 AI 搜索表现"
            ],
            'estimated_brand_value': estimated_value,
            'value_change': 0,
            'summary_text': self._generate_summary_text(brand_name, overall_score, health_grade, key_findings)
        }
    
    def _generate_summary_text(self, brand_name: str, overall_score: float, health_grade: str, 
                               key_findings: List[str]) -> str:
        """生成摘要文本"""
        findings_text = '\n'.join([f"• {finding}" for finding in key_findings[:3]])
        
        return f"""{brand_name}品牌健康度评分为{overall_score}分，等级{health_grade}。

核心发现：
{findings_text}

建议优先处理高风险负面信源，加强主流 AI 平台内容覆盖，建立常态化监测机制。"""
    
    def _save_report_data(self, execution_id: str, competitive_data: Dict[str, Any],
                         negative_sources: Dict[str, Any], roi_metrics: Dict[str, Any],
                         action_plan: Dict[str, Any], executive_summary: Dict[str, Any]):
        """保存报告数据到数据库"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 更新 test_results 表
            cursor.execute("""
                UPDATE test_results SET
                    competitor_analysis = ?,
                    negative_sources = ?,
                    roi_metrics = ?,
                    action_plan = ?,
                    executive_summary = ?,
                    report_generated_at = ?,
                    report_version = ?
                WHERE execution_id = ? OR result_id = ?
            """, (
                json.dumps(competitive_data, ensure_ascii=False),
                json.dumps(negative_sources, ensure_ascii=False),
                json.dumps(roi_metrics, ensure_ascii=False),
                json.dumps(action_plan, ensure_ascii=False),
                json.dumps(executive_summary, ensure_ascii=False),
                datetime.now().isoformat(),
                '2.0',
                execution_id,
                execution_id
            ))
            
            conn.commit()
            self.logger.info(f"报告数据已保存到数据库：execution_id={execution_id}")
            
        except Exception as e:
            self.logger.error(f"保存报告数据失败：{e}", exc_info=True)
            conn.rollback()
            raise


# 全局服务实例
_report_data_service = None


def get_report_data_service() -> ReportDataService:
    """获取报告数据服务实例"""
    global _report_data_service
    if _report_data_service is None:
        _report_data_service = ReportDataService()
    return _report_data_service
