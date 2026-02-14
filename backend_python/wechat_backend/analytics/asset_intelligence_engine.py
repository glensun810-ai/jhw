"""
资产智能引擎 - 内容适配性分析
对比用户上传的官方资产与 AI 搜索引擎的采信偏好
"""
import re
from typing import Dict, List, Tuple, Optional
import jieba
import jieba.analyse
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from ..logging_config import api_logger
from ..semantic_analyzer import SemanticAnalyzer


class AssetIntelligenceEngine:
    """
    资产智能引擎 - 分析官方资产与AI搜索引擎采信偏好的匹配度
    """

    def __init__(self):
        self.logger = api_logger
        self.semantic_analyzer = SemanticAnalyzer()
        
        # AI平台权重配置
        self.ai_platform_weights = {
            'doubao': 0.8,      # 豆包
            'deepseek': 0.9,    # DeepSeek
            'qwen': 0.85,      # 通义千问
            'chatgpt': 0.7,    # ChatGPT
            'gemini': 0.75,    # Gemini
            'kimi': 0.8,       # Kimi
            'yuanbao': 0.78    # 元宝
        }
        
        # 内容优化关键词库
        self.optimization_keywords = {
            'doubao': ['智能', '效率', '便捷', '科技', '创新', '实用'],
            'qwen': ['全面', '专业', '权威', '技术', '解决方案', '服务'],
            'deepseek': ['深度', '分析', '技术', '专业', '行业', '趋势'],
            'chatgpt': ['国际', '标准', '最佳实践', '经验', '知识'],
            'gemini': ['创新', '智能', '未来', '科技', '发展', '趋势']
        }

    def analyze_content_matching(self, official_asset: str, ai_preferences: Dict[str, List[str]]) -> Dict[str, any]:
        """
        分析官方资产与AI偏好内容的匹配度

        Args:
            official_asset: 官方资产内容
            ai_preferences: AI平台偏好内容字典，格式为 {platform_name: [content1, content2, ...]}

        Returns:
            匹配度分析结果
        """
        results = {
            'content_hit_rate': 0.0,
            'platform_analyses': {},
            'overall_score': 0.0,
            'optimization_suggestions': [],
            'semantic_gaps': []
        }

        total_hit_score = 0
        platform_count = 0

        for platform, ai_contents in ai_preferences.items():
            # 计算单个平台的匹配度
            platform_analysis = self._analyze_single_platform(
                official_asset, ai_contents, platform
            )
            
            results['platform_analyses'][platform] = platform_analysis
            total_hit_score += platform_analysis['hit_rate'] * self.ai_platform_weights.get(platform, 0.5)
            platform_count += self.ai_platform_weights.get(platform, 0.5)

        # 计算总体得分
        if platform_count > 0:
            results['overall_score'] = total_hit_score / platform_count
        else:
            results['overall_score'] = 0.0

        # 生成优化建议
        results['optimization_suggestions'] = self._generate_optimization_suggestions(
            official_asset, ai_preferences, results['platform_analyses']
        )

        # 识别语义鸿沟
        results['semantic_gaps'] = self._identify_semantic_gaps(
            official_asset, ai_preferences
        )

        return results

    def _analyze_single_platform(self, official_asset: str, ai_contents: List[str], platform: str) -> Dict[str, any]:
        """
        分析单个AI平台的内容匹配度

        Args:
            official_asset: 官方资产内容
            ai_contents: AI平台内容列表
            platform: 平台名称

        Returns:
            单平台分析结果
        """
        # 合并AI内容
        combined_ai_content = " ".join(ai_contents)

        # 计算语义相似度
        semantic_similarity = self.semantic_analyzer.calculate_semantic_similarity(
            official_asset, combined_ai_content
        )

        # 提取关键词
        official_keywords = self.semantic_analyzer.extract_keywords(official_asset, top_k=15)
        ai_keywords = self.semantic_analyzer.extract_keywords(combined_ai_content, top_k=15)

        # 计算关键词重合度
        keyword_overlap = 0
        if official_keywords and ai_keywords:
            official_set = set(official_keywords)
            ai_set = set(ai_keywords)
            overlap = official_set.intersection(ai_set)
            keyword_overlap = len(overlap) / len(official_set) if official_set else 0

        # 计算内容命中率（综合语义相似度和关键词重合度）
        hit_rate = (semantic_similarity * 0.7 + keyword_overlap * 0.3) * 100

        # 分析缺失的关键词
        missing_keywords = [kw for kw in official_keywords if kw not in ai_keywords]

        return {
            'hit_rate': hit_rate,
            'semantic_similarity': semantic_similarity,
            'keyword_overlap': keyword_overlap,
            'official_keywords': official_keywords,
            'ai_keywords': ai_keywords,
            'missing_keywords': missing_keywords,
            'content_length_match': abs(len(official_asset) - len(combined_ai_content)) / max(len(official_asset), 1)
        }

    def _generate_optimization_suggestions(
        self, 
        official_asset: str, 
        ai_preferences: Dict[str, List[str]], 
        platform_analyses: Dict[str, Dict]
    ) -> List[Dict[str, str]]:
        """
        生成内容优化建议

        Args:
            official_asset: 官方资产内容
            ai_preferences: AI平台偏好内容
            platform_analyses: 平台分析结果

        Returns:
            优化建议列表
        """
        suggestions = []

        for platform, ai_contents in ai_preferences.items():
            platform_analysis = platform_analyses[platform]
            hit_rate = platform_analysis['hit_rate']
            
            # 如果匹配度较低，生成针对性建议
            if hit_rate < 60:  # 低于60%认为匹配度较低
                # 获取AI内容的高频关键词
                combined_ai_content = " ".join(ai_contents)
                ai_keywords = self.semantic_analyzer.extract_keywords(combined_ai_content, top_k=10)
                
                # 找出官方资产中缺少但AI内容中重要的关键词
                official_keywords = self.semantic_analyzer.extract_keywords(official_asset, top_k=15)
                missing_important_keywords = [kw for kw in ai_keywords if kw not in official_keywords]
                
                if missing_important_keywords:
                    suggestion = {
                        'platform': platform,
                        'type': 'keyword_addition',
                        'description': f"建议在官方内容中增加关键词以提高在{platform}平台的收录权重",
                        'suggested_keywords': missing_important_keywords[:3],  # 只建议前3个关键词
                        'rationale': f"这些关键词在{platform}的回答中频繁出现，有助于提高内容匹配度"
                    }
                    suggestions.append(suggestion)

        # 添加通用优化建议
        if not suggestions:
            suggestions.append({
                'platform': 'all',
                'type': 'general_optimization',
                'description': '官方内容与AI偏好匹配度良好',
                'suggested_keywords': [],
                'rationale': '继续保持当前内容策略'
            })
        else:
            # 添加内容结构调整建议
            suggestions.append({
                'platform': 'all',
                'type': 'structure_optimization',
                'description': '建议优化内容结构以提高AI理解度',
                'suggested_keywords': ['清晰标题', '要点列表', '结论总结'],
                'rationale': 'AI更倾向于结构化的内容呈现方式'
            })

        return suggestions

    def _identify_semantic_gaps(self, official_asset: str, ai_preferences: Dict[str, List[str]]) -> List[Dict[str, str]]:
        """
        识别语义鸿沟

        Args:
            official_asset: 官方资产内容
            ai_preferences: AI平台偏好内容

        Returns:
            语义鸿沟列表
        """
        gaps = []

        for platform, ai_contents in ai_preferences.items():
            combined_ai_content = " ".join(ai_contents)
            
            # 使用语义分析器分析差异
            analysis = self.semantic_analyzer.analyze_semantic_drift(
                official_asset, [combined_ai_content], platform
            )
            
            # 如果语义偏移较大，记录为语义鸿沟
            if analysis['semantic_drift_score'] > 50:  # 偏移大于50认为存在语义鸿沟
                gap = {
                    'platform': platform,
                    'drift_score': analysis['semantic_drift_score'],
                    'severity': analysis['drift_severity'],
                    'missing_keywords': analysis['missing_keywords'][:5],  # 只取前5个
                    'unexpected_keywords': analysis['unexpected_keywords'][:5],  # 只取前5个
                    'description': f"官方内容与{platform}平台内容存在语义差异"
                }
                gaps.append(gap)

        return gaps

    def calculate_content_hit_rate(self, official_content: str, ai_content: str) -> float:
        """
        计算内容命中率评分

        Args:
            official_content: 官方内容
            ai_content: AI内容

        Returns:
            命中率评分 (0-100)
        """
        # 使用语义相似度作为基础命中率
        semantic_similarity = self.semantic_analyzer.calculate_semantic_similarity(
            official_content, ai_content
        )
        
        # 提取关键词并计算重合度
        official_keywords = self.semantic_analyzer.extract_keywords(official_content, top_k=10)
        ai_keywords = self.semantic_analyzer.extract_keywords(ai_content, top_k=10)
        
        if official_keywords and ai_keywords:
            overlap_count = len(set(official_keywords) & set(ai_keywords))
            keyword_match_rate = overlap_count / len(official_keywords)
        else:
            keyword_match_rate = 0.0
        
        # 综合语义相似度和关键词匹配率
        hit_rate = (semantic_similarity * 0.6 + keyword_match_rate * 0.4) * 100
        
        return hit_rate

    def get_optimization_recommendations(
        self, 
        official_asset: str, 
        ai_preferences: Dict[str, List[str]]
    ) -> List[str]:
        """
        获取优化建议

        Args:
            official_asset: 官方资产内容
            ai_preferences: AI平台偏好内容

        Returns:
            优化建议列表
        """
        recommendations = []
        
        for platform, ai_contents in ai_preferences.items():
            combined_ai_content = " ".join(ai_contents)
            
            # 分析关键词差异
            official_keywords = self.semantic_analyzer.extract_keywords(official_asset, top_k=10)
            ai_keywords = self.semantic_analyzer.extract_keywords(combined_ai_content, top_k=10)
            
            missing_keywords = [kw for kw in ai_keywords if kw not in official_keywords]
            
            if missing_keywords:
                # 获取该平台的推荐关键词
                platform_specific_keywords = self.optimization_keywords.get(platform, [])
                platform_missing = [kw for kw in missing_keywords if kw in platform_specific_keywords]
                
                if platform_missing:
                    recommendations.append(
                        f"建议{platform}平台：在官方内容中增加关键词 '{', '.join(platform_missing[:3])}' "
                        f"以提高收录权重和匹配度"
                    )
        
        # 如果没有特定平台建议，提供通用建议
        if not recommendations:
            recommendations.append(
                "官方内容与AI平台偏好匹配度较高，建议继续保持当前内容策略"
            )
        
        return recommendations


# Example usage
if __name__ == "__main__":
    # Create asset intelligence engine
    engine = AssetIntelligenceEngine()
    
    # Example official asset
    official_asset = """
    我们是一家专注于人工智能技术创新的公司，致力于为客户提供
    高品质的AI解决方案。我们以专业的技术实力和优质的服务
    赢得了市场的认可，持续推动行业发展。
    """
    
    # Example AI preferences (simulated)
    ai_preferences = {
        'doubao': [
            "这家公司在AI领域技术实力不错，特别是在机器学习方面有深厚积累",
            "他们的AI解决方案在业界有一定知名度，客户反馈较好",
            "技术团队专业，产品实用性强，适合企业级应用"
        ],
        'qwen': [
            "这是一家专业的AI技术服务提供商，拥有全面的技术栈",
            "公司在人工智能领域有丰富的实践经验和技术沉淀",
            "提供的解决方案具有权威性和可靠性"
        ],
        'deepseek': [
            "该公司在AI技术方面有深入的研究和分析能力",
            "他们的技术方案经过深度分析，具有行业前瞻性",
            "在AI发展趋势和技术方向上有独到见解"
        ]
    }
    
    # Analyze content matching
    result = engine.analyze_content_matching(official_asset, ai_preferences)
    
    print("内容匹配度分析结果:")
    print(f"总体得分: {result['overall_score']:.2f}")
    print(f"优化建议数量: {len(result['optimization_suggestions'])}")
    print(f"语义鸿沟数量: {len(result['semantic_gaps'])}")
    
    print("\n各平台分析:")
    for platform, analysis in result['platform_analyses'].items():
        print(f"  {platform}: 命中率 {analysis['hit_rate']:.2f}%")
    
    print("\n优化建议:")
    for suggestion in result['optimization_suggestions']:
        print(f"  - {suggestion['description']}")
        if suggestion['suggested_keywords']:
            print(f"    建议关键词: {', '.join(suggestion['suggested_keywords'])}")