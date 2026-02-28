"""
品牌分析服务

P0 修复：后置品牌提及分析模块
P2 修复：批量品牌提取（严禁在 for 循环中针对每个品牌单独调用 LLM！）

职责：
1. 从 AI 客观回答中提取品牌提及（批量提取，单次 LLM 调用）
2. 提取 TOP3 品牌作为竞品
3. 对比用户品牌与竞品表现

使用场景：
- NxM 执行引擎获取客观回答后
- 需要分析用户品牌在 AI 回答中的表现
- 需要生成竞品对比报告

性能优化：
- 使用 BATCH_BRAND_EXTRACTION_TEMPLATE 一次性提取所有品牌
- 每个回答仅需 1 次 LLM 调用，而非 N 次（N=品牌数量）

裁判模型选择策略：
- 优先使用调用方传入的 judge_model
- 若未指定，优先选择有配额的豆包模型（通过 DoubaoPriorityAdapter）
- 其次选择其他已配置的平台模型（qwen, deepseek, kimi 等）
- 支持传入用户选择的模型列表，从中选择第一个可用的
"""

import json
import re
from typing import List, Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.ai_adapters.base_adapter import (
    BRAND_ANALYSIS_TEMPLATE,
    BATCH_BRAND_EXTRACTION_TEMPLATE
)
from wechat_backend.ai_adapters.factory import AIAdapterFactory
from legacy_config import Config


class BrandAnalysisService:
    """品牌分析服务"""

    # 裁判模型优先级列表（从高到低）
    JUDGE_MODEL_PRIORITY = ['doubao', 'qwen', 'deepseek', 'kimi', 'chatgpt', 'gemini', 'zhipu', 'wenxin']

    def __init__(self, judge_model: Optional[str] = None, user_selected_models: Optional[List[str]] = None):
        """
        初始化品牌分析服务

        Args:
            judge_model: 用于分析的裁判模型，若为 None 则自动选择
            user_selected_models: 用户选择的模型列表，若提供则优先从中选择
        """
        self.judge_model = self._select_judge_model(judge_model, user_selected_models)
    
    def _select_judge_model(
        self, 
        judge_model: Optional[str] = None,
        user_selected_models: Optional[List[str]] = None
    ) -> str:
        """
        智能选择裁判模型
        
        选择策略：
        1. 优先使用调用方明确指定的 judge_model
        2. 若未指定，优先从用户选择的模型中选择第一个可用的
        3. 若用户未选择模型，则按优先级列表选择已配置的平台
        4. 豆包平台使用优先级适配器，自动选择有配额的模型
        
        Args:
            judge_model: 调用方指定的模型
            user_selected_models: 用户选择的模型列表
            
        Returns:
            选定的模型名称
        """
        # 策略 1: 使用调用方明确指定的模型
        if judge_model:
            api_logger.info(f"[BrandAnalysis] 使用指定的裁判模型：{judge_model}")
            return judge_model
        
        # 策略 2: 从用户选择的模型中选择第一个可用的
        if user_selected_models:
            for model in user_selected_models:
                model_lower = model.lower() if isinstance(model, str) else ''
                # 检查模型是否已配置
                if Config.is_api_key_configured(model_lower):
                    api_logger.info(f"[BrandAnalysis] 从用户选择的模型中使用：{model_lower}")
                    return model_lower
            # 如果用户选择的模型都不可用，记录警告
            api_logger.warning(
                f"[BrandAnalysis] 用户选择的模型均不可用：{user_selected_models}，将使用默认优先级"
            )
        
        # 策略 3: 按优先级列表选择已配置的平台
        for platform in self.JUDGE_MODEL_PRIORITY:
            if Config.is_api_key_configured(platform):
                # 豆包平台特殊处理：使用优先级适配器自动选择有配额的模型
                if platform == 'doubao':
                    api_logger.info(f"[BrandAnalysis] 使用豆包优先级适配器（自动选择有配额的模型）")
                    return 'doubao'
                # 其他平台直接返回
                api_logger.info(f"[BrandAnalysis] 使用裁判模型：{platform}")
                return platform
        
        # 降级方案：返回 doubao（即使可能未配置，让上层处理错误）
        api_logger.warning("[BrandAnalysis] 无可用模型，降级使用 doubao")
        return 'doubao'

    def _ensure_string_input(self, input_data) -> str:
        """
        确保输入为字符串类型，处理 dict 等非标输入
        
        Args:
            input_data: 输入数据，可能是 dict、str 或其他类型
            
        Returns:
            处理后的字符串
        """
        if isinstance(input_data, dict):
            # 优先提取常见文本字段
            text = input_data.get('response') or input_data.get('content') or input_data.get('text') or str(input_data)
            api_logger.warning(f"[BrandAnalysis] 检测到 dict 类型输入，已提取文本字段：{type(input_data)}")
            return str(text) if text else ''
        elif isinstance(input_data, (str, bytes)):
            return str(input_data)
        else:
            # 其他类型转换为字符串
            api_logger.warning(f"[BrandAnalysis] 非字符串输入类型：{type(input_data)}")
            return str(input_data) if input_data else ''

    def analyze_brand_mentions(
        self,
        results: List[Dict[str, Any]],
        user_brand: str,
        competitor_brands: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        分析品牌提及情况

        Args:
            results: AI 回答列表（客观回答）
            user_brand: 用户品牌
            competitor_brands: 竞品品牌列表（可选，若为 None 则从回答中提取）

        Returns:
            分析结果字典，包含：
            - user_brand_analysis: 用户品牌分析
            - competitor_analysis: 竞品分析
            - comparison: 对比分析
            - top3_brands: 从回答中提取的 TOP3 品牌

        性能说明：
            使用批量提取策略，每个回答仅需 1 次 LLM 调用即可提取所有品牌，
            避免了为每个品牌单独调用 LLM 的低效做法。
        """
        analysis = {
            'user_brand_analysis': {},
            'competitor_analysis': [],
            'comparison': {},
            'top3_brands': []
        }

        # 步骤 1: 使用批量提取从每个回答中提取所有品牌（每个回答仅 1 次 LLM 调用）
        all_brands_map = {}  # {brand_name: [brand_data_per_response]}
        for result in results:
            response = result.get('response', '')
            question = result.get('question', '')
            brands_in_response = self._batch_extract_brands(response, question)
            
            # 构建品牌到其提及数据的映射
            for brand_data in brands_in_response:
                brand_name = brand_data.get('brand_name', '')
                if brand_name:
                    if brand_name not in all_brands_map:
                        all_brands_map[brand_name] = []
                    all_brands_map[brand_name].append(brand_data)

        # 步骤 2: 提取 TOP3 品牌作为竞品
        all_top3_brands = []
        for result in results:
            top3 = self._extract_top3_brands(result.get('response', ''))
            if top3:
                all_top3_brands.extend(top3)

        # 去重 TOP3 品牌
        seen_brands = set()
        unique_top3 = []
        for brand in all_top3_brands:
            brand_name = brand.get('name', '')
            if brand_name and brand_name not in seen_brands and brand_name != user_brand:
                seen_brands.add(brand_name)
                unique_top3.append(brand)

        analysis['top3_brands'] = unique_top3[:3]  # 只取前 3 个竞品

        # 步骤 3: 若未指定竞品，使用提取的 TOP3 品牌作为竞品
        if not competitor_brands:
            competitor_brands = [b['name'] for b in unique_top3[:3]]
            api_logger.info(f"[BrandAnalysis] 未指定竞品，使用提取的 TOP3: {competitor_brands}")

        total_responses = len(results)

        # 步骤 4: 分析用户品牌
        user_brand_mentions = self._build_brand_mentions(
            brand_name=user_brand,
            brands_map=all_brands_map,
            total_responses=total_responses
        )

        analysis['user_brand_analysis'] = {
            'brand': user_brand,
            'mentions': user_brand_mentions,
            'mentioned_count': sum(1 for m in user_brand_mentions if m.get('brand_mentioned', False)),
            'total_responses': total_responses,
            'mention_rate': sum(1 for m in user_brand_mentions if m.get('brand_mentioned', False)) / total_responses if total_responses > 0 else 0,
            'average_rank': self._calc_average_rank(user_brand_mentions),
            'average_sentiment': self._calc_average_sentiment(user_brand_mentions),
            'is_top3': any(m.get('is_top3', False) for m in user_brand_mentions)
        }

        # 步骤 5: 分析竞品品牌（不再调用 LLM，直接从批量提取结果中获取）
        for competitor in competitor_brands:
            competitor_mentions = self._build_brand_mentions(
                brand_name=competitor,
                brands_map=all_brands_map,
                total_responses=total_responses
            )
            
            comp_mentioned_count = sum(1 for m in competitor_mentions if m.get('brand_mentioned', False))
            analysis['competitor_analysis'].append({
                'brand': competitor,
                'mentions': competitor_mentions,
                'mentioned_count': comp_mentioned_count,
                'mention_rate': comp_mentioned_count / total_responses if total_responses > 0 else 0,
                'average_rank': self._calc_average_rank(competitor_mentions),
                'average_sentiment': self._calc_average_sentiment(competitor_mentions),
                'is_top3': any(m.get('is_top3', False) for m in competitor_mentions)
            })

        # 步骤 6: 生成对比分析
        analysis['comparison'] = self._generate_comparison(
            user_analysis=analysis['user_brand_analysis'],
            competitor_analyses=analysis['competitor_analysis']
        )

        api_logger.info(
            f"[BrandAnalysis] 分析完成：{user_brand}, "
            f"提及率={analysis['user_brand_analysis']['mention_rate']:.1%}, "
            f"竞品数={len(analysis['competitor_analysis'])}"
        )

        return analysis

    def _extract_top3_brands(self, response: str) -> List[Dict[str, Any]]:
        """
        从回答中提取 TOP3 品牌

        Args:
            response: AI 回答文本

        Returns:
            TOP3 品牌列表
        """
        # 防御性编程：确保 response 是字符串
        text_to_process = self._ensure_string_input(response)
        
        # 尝试解析 JSON 格式的 top3_brands
        try:
            # 查找 JSON 部分（支持多种格式）
            json_patterns = [
                r'\{\s*"top3_brands"\s*:\s*\[.*?\]\s*\}',  # 完整 JSON 对象
                r'\[\s*\{.*?"name".*?"rank".*?\}\s*\]',    # 直接是数组
            ]

            for pattern in json_patterns:
                json_match = re.search(pattern, text_to_process, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)

                    # 如果是完整对象，提取 top3_brands 字段
                    if isinstance(data, dict) and 'top3_brands' in data:
                        return data['top3_brands']
                    # 如果直接是数组，返回
                    elif isinstance(data, list):
                        return data

        except (json.JSONDecodeError, AttributeError) as e:
            api_logger.warning(f"[BrandAnalysis] JSON 解析失败：{e}")

        # 降级：使用正则提取品牌名（简单匹配）
        # 匹配模式："name": "品牌名" 或 "name":"品牌名"
        brand_pattern = r'"name"\s*:\s*"([^"]+)"'
        matches = re.findall(brand_pattern, text_to_process)

        if matches:
            api_logger.warning(f"[BrandAnalysis] 使用降级方案提取品牌：{matches[:3]}")
            return [{'name': name, 'rank': i+1, 'reason': ''} for i, name in enumerate(matches[:3])]

        return []

    def _batch_extract_brands(
        self,
        response: str,
        question: str
    ) -> List[Dict[str, Any]]:
        """
        批量提取回答中的所有品牌（P2 修复：严禁在 for 循环中针对每个品牌单独调用 LLM！）

        Args:
            response: AI 回答文本
            question: 原始问题

        Returns:
            品牌数据列表，每个品牌包含：
            - brand_name: 品牌名称
            - rank: 排名
            - sentiment: 情感分数
            - is_top3: 是否 TOP3
            - mention_context: 提及上下文
        """
        # 防御性编程：确保 response 是字符串
        text_to_process = self._ensure_string_input(response)
        
        # 使用 AI 批量提取所有品牌（单次调用）
        try:
            client = AIAdapterFactory.create(self.judge_model)
            prompt = BATCH_BRAND_EXTRACTION_TEMPLATE.format(
                ai_response=text_to_process[:3000],  # 限制长度避免超时
            )

            result = client.send_prompt(prompt)

            # 解析批量提取结果
            if result and result.success and result.content:
                brands_data = self._parse_batch_brand_extraction(result.content)
                if brands_data:
                    return brands_data

        except Exception as e:
            api_logger.warning(f"[BrandAnalysis] 批量提取失败：{e}，使用降级方案")

        # 降级方案：简单文本匹配提取品牌
        return self._fallback_extract_brands(text_to_process)

    def _parse_batch_brand_extraction(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """
        解析批量品牌提取的 AI 响应

        Args:
            text: AI 响应文本

        Returns:
            解析后的品牌列表，失败返回 None
        """
        try:
            # 清理 Markdown 代码块标记（如果 LLM 仍然输出了）
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```\s*', '', text)
            
            # 查找 JSON 部分
            json_match = re.search(r'\{.*"brands"\s*:\s*\[.*?\]\s*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                brands = data.get('brands', [])
                
                # 验证并转换格式
                result = []
                for brand in brands:
                    validated = self._validate_brand_data(brand)
                    if validated:
                        result.append({
                            'brand_name': validated['brand_name'],
                            'brand_mentioned': True,  # 能提取到说明被提及
                            'rank': validated['rank'],
                            'sentiment': validated['sentiment'],
                            'is_top3': validated['is_top3'],
                            'mention_context': validated.get('mention_context', '')
                        })
                
                if result:
                    api_logger.info(f"[BrandAnalysis] 成功提取 {len(result)} 个品牌：{[b['brand_name'] for b in result]}")
                return result

        except (json.JSONDecodeError, AttributeError) as e:
            api_logger.warning(f"[BrandAnalysis] 解析批量提取结果失败：{e}")

        return None
    
    def _validate_brand_data(self, brand: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        验证品牌数据字段的类型和范围
        
        Args:
            brand: 品牌数据字典
            
        Returns:
            验证后的品牌数据，若验证失败返回 None
        """
        try:
            # 验证 brand_name
            brand_name = brand.get('brand_name', '')
            if not brand_name or not isinstance(brand_name, str):
                return None
            
            # 验证 rank（必须是数字）
            rank = brand.get('rank', -1)
            if isinstance(rank, str):
                rank = int(rank)
            if not isinstance(rank, (int, float)) or rank < -1 or rank > 10:
                rank = -1
            
            # 验证 sentiment（必须是 -1.0 到 1.0 之间的数字）
            sentiment = brand.get('sentiment', 0)
            if isinstance(sentiment, str):
                sentiment = float(sentiment)
            if not isinstance(sentiment, (int, float)):
                sentiment = 0
            sentiment = max(-1.0, min(1.0, sentiment))  # 限制在 [-1, 1] 范围
            
            # 验证 is_top3（必须是布尔值）
            is_top3 = brand.get('is_top3', False)
            if isinstance(is_top3, str):
                is_top3 = is_top3.lower() == 'true'
            if not isinstance(is_top3, bool):
                # 根据 rank 推断
                is_top3 = 1 <= rank <= 3
            
            # 验证 mention_context
            mention_context = brand.get('mention_context', '')
            if not isinstance(mention_context, str):
                mention_context = str(mention_context) if mention_context else ''
            mention_context = mention_context[:100]  # 限制长度
            
            return {
                'brand_name': brand_name,
                'rank': rank,
                'sentiment': sentiment,
                'is_top3': is_top3,
                'mention_context': mention_context
            }
            
        except (ValueError, TypeError) as e:
            api_logger.warning(f"[BrandAnalysis] 品牌数据验证失败：{e}, brand={brand}")
            return None

    def _fallback_extract_brands(self, response: str) -> List[Dict[str, Any]]:
        """
        降级方案：从回答中简单提取品牌

        Args:
            response: AI 回答文本

        Returns:
            品牌数据列表
        """
        # 防御性编程：确保 response 是字符串
        text_to_process = self._ensure_string_input(response)
        
        # 尝试从 JSON 中提取
        try:
            json_patterns = [
                r'\{\s*"top3_brands"\s*:\s*\[.*?\]\s*\}',
                r'\[\s*\{.*?"name".*?\}\s*\]',
            ]

            for pattern in json_patterns:
                json_match = re.search(pattern, text_to_process, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    data = json.loads(json_str)

                    if isinstance(data, dict) and 'top3_brands' in data:
                        brands = data['top3_brands']
                    elif isinstance(data, list):
                        brands = data
                    else:
                        continue

                    result = []
                    for brand in brands:
                        result.append({
                            'brand_name': brand.get('name', brand.get('brand_name', '')),
                            'brand_mentioned': True,
                            'rank': brand.get('rank', -1),
                            'sentiment': brand.get('sentiment', 0),
                            'is_top3': brand.get('rank', 99) <= 3,
                            'mention_context': brand.get('reason', '')
                        })
                    return result

        except (json.JSONDecodeError, AttributeError):
            pass

        # 最简单的降级：返回空列表
        return []

    def _build_brand_mentions(
        self,
        brand_name: str,
        brands_map: Dict[str, List[Dict[str, Any]]],
        total_responses: int
    ) -> List[Dict[str, Any]]:
        """
        构建品牌在每个回答中的提及数据

        Args:
            brand_name: 品牌名称
            brands_map: 品牌到其提及数据的映射 {brand_name: [brand_data_per_response]}
            total_responses: 总回答数

        Returns:
            品牌提及列表，长度为 total_responses
        """
        mentions = []
        brand_data_list = brands_map.get(brand_name, [])
        
        # 为每个回答创建提及记录
        # 注意：由于批量提取是按回答进行的，这里需要为每个回答创建一个提及记录
        # 如果品牌在该回答中被提及，使用提取到的数据；否则创建未提及的记录
        for i in range(total_responses):
            if i < len(brand_data_list):
                # 品牌在该回答中被提及
                brand_data = brand_data_list[i]
                mentions.append({
                    'brand_mentioned': True,
                    'rank': brand_data.get('rank', -1),
                    'sentiment': brand_data.get('sentiment', 0),
                    'is_top3': brand_data.get('is_top3', False),
                    'mention_context': brand_data.get('mention_context', '')
                })
            else:
                # 品牌在该回答中未被提及
                mentions.append({
                    'brand_mentioned': False,
                    'rank': -1,
                    'sentiment': 0,
                    'is_top3': False,
                    'mention_context': ''
                })
        
        return mentions

    def _analyze_brand_in_response(
        self,
        response: str,
        brand: str,
        question: str
    ) -> Dict[str, Any]:
        """
        分析品牌在回答中的表现（已废弃，保留用于向后兼容）

        Args:
            response: AI 回答文本
            brand: 品牌名称
            question: 原始问题

        Returns:
            品牌分析结果

        注意：此方法已被 _batch_extract_brands 替代，不再单独调用 LLM
        """
        # 方案 1: 使用 AI 分析（更准确）
        try:
            client = AIAdapterFactory.create(self.judge_model)
            prompt = BRAND_ANALYSIS_TEMPLATE.format(
                ai_response=response[:2000],  # 限制长度避免超时
                user_brand=brand,
                question=question
            )

            result = client.send_prompt(prompt)

            # 解析分析结果
            if result and result.success and result.content:
                analysis_data = self._parse_brand_analysis(result.content)
                if analysis_data:
                    return analysis_data

        except Exception as e:
            api_logger.warning(f"[BrandAnalysis] AI 分析失败：{e}，使用降级方案")

        # 方案 2: 简单文本匹配（降级方案）
        mentioned = brand.lower() in response.lower()

        # 尝试提取排名（匹配 "rank": 数字）
        rank = -1
        rank_match = re.search(r'"rank"\s*:\s*(-?\d+)', response)
        if rank_match:
            rank = int(rank_match.group(1))

        # 尝试提取情感（匹配 "sentiment": 数字）
        sentiment = 0.0
        sentiment_match = re.search(r'"sentiment"\s*:\s*(-?[\d.]+)', response)
        if sentiment_match:
            sentiment = float(sentiment_match.group(1))

        # 判断是否在 TOP3 中
        is_top3 = False
        top3_match = re.search(r'"is_top3"\s*:\s*(true|false)', response, re.IGNORECASE)
        if top3_match:
            is_top3 = top3_match.group(1).lower() == 'true'

        return {
            'brand_mentioned': mentioned,
            'rank': rank,
            'sentiment': sentiment,
            'is_top3': is_top3,
            'mention_context': self._extract_mention_context(response, brand) if mentioned else ''
        }

    def _parse_brand_analysis(self, text: str) -> Optional[Dict[str, Any]]:
        """
        解析品牌分析 AI 响应

        Args:
            text: AI 响应文本

        Returns:
            解析后的分析结果，失败返回 None
        """
        try:
            # 查找 JSON 部分
            json_match = re.search(r'\{.*"brand_analysis".*\}', text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                analysis = data.get('brand_analysis', {})
                return {
                    'brand_mentioned': analysis.get('brand_mentioned', False),
                    'rank': analysis.get('rank', -1),
                    'sentiment': analysis.get('sentiment', 0),
                    'is_top3': analysis.get('is_top3', False),
                    'mention_context': analysis.get('mention_context', '')
                }
        except (json.JSONDecodeError, AttributeError) as e:
            api_logger.warning(f"[BrandAnalysis] 解析 AI 分析结果失败：{e}")

        return None

    def _extract_mention_context(self, response: str, brand: str) -> str:
        """
        提取品牌提及的上下文

        Args:
            response: AI 回答文本
            brand: 品牌名称

        Returns:
            提及上下文字符串
        """
        # 查找品牌名出现的位置
        brand_lower = brand.lower()
        response_lower = response.lower()

        index = response_lower.find(brand_lower)
        if index == -1:
            return ''

        # 提取前后各 50 个字符
        start = max(0, index - 50)
        end = min(len(response), index + len(brand) + 50)

        context = response[start:end].strip()
        return f"...{context}..."

    def _calc_average_rank(self, mentions: List[Dict]) -> float:
        """
        计算平均排名

        Args:
            mentions: 品牌提及列表

        Returns:
            平均排名，未提及返回 -1
        """
        ranks = [m['rank'] for m in mentions if m.get('rank', -1) > 0]
        return sum(ranks) / len(ranks) if ranks else -1

    def _calc_average_sentiment(self, mentions: List[Dict]) -> float:
        """
        计算平均情感分

        Args:
            mentions: 品牌提及列表

        Returns:
            平均情感分
        """
        sentiments = [m['sentiment'] for m in mentions if m.get('brand_mentioned', False)]
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def _generate_comparison(
        self,
        user_analysis: Dict,
        competitor_analyses: List[Dict]
    ) -> Dict[str, Any]:
        """
        生成对比分析

        Args:
            user_analysis: 用户品牌分析
            competitor_analyses: 竞品分析列表

        Returns:
            对比分析结果
        """
        user_mention_rate = user_analysis.get('mention_rate', 0)
        user_avg_rank = user_analysis.get('average_rank', -1)
        user_avg_sentiment = user_analysis.get('average_sentiment', 0)

        vs_competitors = []
        for comp in competitor_analyses:
            comp_mention_rate = comp.get('mention_rate', 0)
            comp_avg_rank = comp.get('average_rank', -1)
            comp_avg_sentiment = comp.get('average_sentiment', 0)

            vs_competitors.append({
                'competitor': comp['brand'],
                'mention_rate_diff': user_mention_rate - comp_mention_rate,
                'rank_diff': user_avg_rank - comp_avg_rank if user_avg_rank > 0 and comp_avg_rank > 0 else 0,
                'sentiment_diff': user_avg_sentiment - comp_avg_sentiment,
                'advantage': self._get_advantage_text(
                    user_mention_rate, comp_mention_rate,
                    user_avg_rank, comp_avg_rank,
                    user_avg_sentiment, comp_avg_sentiment
                )
            })

        return {
            'user_brand': user_analysis.get('brand', ''),
            'mention_rate': user_mention_rate,
            'average_rank': user_avg_rank,
            'average_sentiment': user_avg_sentiment,
            'is_top3': user_analysis.get('is_top3', False),
            'vs_competitors': vs_competitors,
            'summary': self._generate_summary(user_analysis, competitor_analyses)
        }

    def _get_advantage_text(
        self,
        user_rate: float, comp_rate: float,
        user_rank: float, comp_rank: float,
        user_sentiment: float, comp_sentiment: float
    ) -> str:
        """
        生成优势劣势描述

        Returns:
            优势/劣势描述文本
        """
        advantages = []
        disadvantages = []

        if user_rate > comp_rate:
            advantages.append(f"提及率高 {int((user_rate - comp_rate) * 100)}%")
        elif user_rate < comp_rate:
            disadvantages.append(f"提及率低 {int((comp_rate - user_rate) * 100)}%")

        if user_rank > 0 and comp_rank > 0:
            if user_rank < comp_rank:
                advantages.append(f"排名靠前 ({int(user_rank)} vs {int(comp_rank)})")
            elif user_rank > comp_rank:
                disadvantages.append(f"排名靠后 ({int(user_rank)} vs {int(comp_rank)})")

        if user_sentiment > comp_sentiment:
            advantages.append(f"情感更积极")
        elif user_sentiment < comp_sentiment:
            disadvantages.append(f"情感较消极")

        if advantages and disadvantages:
            return f"优势：{', '.join(advantages)}；劣势：{', '.join(disadvantages)}"
        elif advantages:
            return f"优势：{', '.join(advantages)}"
        elif disadvantages:
            return f"劣势：{', '.join(disadvantages)}"
        else:
            return "表现相当"

    def _generate_summary(
        self,
        user_analysis: Dict,
        competitor_analyses: List[Dict]
    ) -> str:
        """
        生成总结性描述

        Args:
            user_analysis: 用户品牌分析
            competitor_analyses: 竞品分析列表

        Returns:
            总结文本
        """
        brand = user_analysis.get('brand', '该品牌')
        mention_rate = user_analysis.get('mention_rate', 0)
        avg_rank = user_analysis.get('average_rank', -1)
        is_top3 = user_analysis.get('is_top3', False)

        summary_parts = []

        # 提及率描述
        if mention_rate >= 0.8:
            summary_parts.append(f"{brand}在 AI 推荐中被高频提及（{int(mention_rate * 100)}%）")
        elif mention_rate >= 0.5:
            summary_parts.append(f"{brand}在 AI 推荐中有一定提及（{int(mention_rate * 100)}%）")
        else:
            summary_parts.append(f"{brand}在 AI 推荐中提及较少（{int(mention_rate * 100)}%）")

        # 排名描述
        if is_top3:
            summary_parts.append("并进入 TOP3 推荐")
        elif avg_rank > 0 and avg_rank <= 5:
            summary_parts.append(f"平均排名第{int(avg_rank)}位")
        elif avg_rank > 5:
            summary_parts.append(f"排名相对靠后（平均第{int(avg_rank)}位）")

        return "，".join(summary_parts)


def get_brand_analysis_service(
    judge_model: Optional[str] = None,
    user_selected_models: Optional[List[str]] = None
) -> BrandAnalysisService:
    """
    获取品牌分析服务实例

    Args:
        judge_model: 用于分析的裁判模型，若为 None 则自动选择
        user_selected_models: 用户选择的模型列表，若提供则优先从中选择

    Returns:
        BrandAnalysisService 实例
    """
    return BrandAnalysisService(
        judge_model=judge_model,
        user_selected_models=user_selected_models
    )
