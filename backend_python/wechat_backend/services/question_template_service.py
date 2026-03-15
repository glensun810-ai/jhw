"""
诊断问题模板库服务

功能:
- 加载和管理问题模板
- 支持模板分类和搜索
- 支持自定义模板保存

@author: 系统架构组
@date: 2026-03-14
@version: 1.0.0
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from wechat_backend.logging_config import api_logger


class QuestionTemplateService:
    """
    问题模板库服务（P1-10 实现版 - 2026-03-14）
    
    功能:
    1. 加载预定义模板
    2. 按分类/行业筛选
    3. 支持模板搜索
    4. 支持自定义模板保存
    """
    
    def __init__(self, data_dir: str = None):
        """
        初始化模板服务
        
        参数:
            data_dir: 数据目录，默认使用项目 data/diagnosis 目录
        """
        if data_dir is None:
            # 默认数据目录
            base_dir = Path(__file__).parent.parent.parent
            data_dir = str(base_dir / 'data' / 'diagnosis')
        
        self.data_dir = data_dir
        self.templates_file = os.path.join(data_dir, 'question_templates.json')
        self.custom_file = os.path.join(data_dir, 'custom_templates.json')
        
        # 内存缓存
        self._templates_cache: Optional[Dict] = None
        self._custom_templates_cache: Optional[Dict] = None
        
        api_logger.info(f"[QuestionTemplate] 初始化完成，数据目录：{data_dir}")
    
    def get_all_templates(self) -> Dict[str, Any]:
        """
        获取所有模板（预定义 + 自定义）
        
        返回:
            Dict: 包含所有模板的数据
        """
        # 加载预定义模板
        templates_data = self._load_templates()
        
        # 加载自定义模板
        custom_data = self._load_custom_templates()
        
        # 合并模板列表
        all_templates = templates_data.get('templates', []) + custom_data.get('templates', [])
        
        return {
            'templates': all_templates,
            'categories': templates_data.get('categories', []),
            'industries': templates_data.get('industries', []),
            'version': templates_data.get('version', '1.0.0')
        }
    
    def _load_templates(self) -> Dict[str, Any]:
        """加载预定义模板"""
        if self._templates_cache is not None:
            return self._templates_cache
        
        try:
            if os.path.exists(self.templates_file):
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    self._templates_cache = json.load(f)
                api_logger.info(f"[QuestionTemplate] 加载预定义模板：{len(self._templates_cache.get('templates', []))} 个")
            else:
                api_logger.warning(f"[QuestionTemplate] 模板文件不存在：{self.templates_file}")
                self._templates_cache = {'templates': [], 'categories': [], 'industries': []}
        except Exception as e:
            api_logger.error(f"[QuestionTemplate] 加载模板失败：{e}")
            self._templates_cache = {'templates': [], 'categories': [], 'industries': []}
        
        return self._templates_cache
    
    def _load_custom_templates(self) -> Dict[str, Any]:
        """加载自定义模板"""
        if self._custom_templates_cache is not None:
            return self._custom_templates_cache
        
        try:
            if os.path.exists(self.custom_file):
                with open(self.custom_file, 'r', encoding='utf-8') as f:
                    self._custom_templates_cache = json.load(f)
                api_logger.info(f"[QuestionTemplate] 加载自定义模板：{len(self._custom_templates_cache.get('templates', []))} 个")
            else:
                self._custom_templates_cache = {'templates': []}
        except Exception as e:
            api_logger.error(f"[QuestionTemplate] 加载自定义模板失败：{e}")
            self._custom_templates_cache = {'templates': []}
        
        return self._custom_templates_cache
    
    def get_templates_by_category(self, category: str) -> List[Dict]:
        """
        按分类获取模板
        
        参数:
            category: 分类名称
            
        返回:
            List[Dict]: 模板列表
        """
        all_data = self.get_all_templates()
        return [
            tpl for tpl in all_data.get('templates', [])
            if tpl.get('category') == category
        ]
    
    def get_templates_by_industry(self, industry: str) -> List[Dict]:
        """
        按行业获取模板
        
        参数:
            industry: 行业名称
            
        返回:
            List[Dict]: 模板列表
        """
        all_data = self.get_all_templates()
        return [
            tpl for tpl in all_data.get('templates', [])
            if tpl.get('industry') == industry
        ]
    
    def search_templates(self, keyword: str) -> List[Dict]:
        """
        搜索模板
        
        参数:
            keyword: 搜索关键词
            
        返回:
            List[Dict]: 匹配的模板列表
        """
        all_data = self.get_all_templates()
        keyword_lower = keyword.lower()
        
        results = []
        for tpl in all_data.get('templates', []):
            # 搜索名称、描述、标签
            name_match = keyword_lower in tpl.get('name', '').lower()
            desc_match = keyword_lower in tpl.get('description', '').lower()
            tags_match = any(keyword_lower in tag.lower() for tag in tpl.get('tags', []))
            
            if name_match or desc_match or tags_match:
                results.append(tpl)
        
        return results
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """
        根据 ID 获取模板
        
        参数:
            template_id: 模板 ID
            
        返回:
            Optional[Dict]: 模板数据，不存在则返回 None
        """
        all_data = self.get_all_templates()
        for tpl in all_data.get('templates', []):
            if tpl.get('id') == template_id:
                return tpl
        return None
    
    def save_custom_template(self, template_data: Dict, user_id: str) -> Dict:
        """
        保存自定义模板
        
        参数:
            template_data: 模板数据
            user_id: 用户 ID
            
        返回:
            Dict: 保存后的模板数据
        """
        # 生成模板 ID
        template_id = f"custom_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 构建完整模板数据
        new_template = {
            'id': template_id,
            'name': template_data.get('name', '自定义模板'),
            'category': template_data.get('category', '自定义'),
            'industry': template_data.get('industry', '通用'),
            'description': template_data.get('description', ''),
            'questions': template_data.get('questions', []),
            'tags': template_data.get('tags', []),
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'usage_count': 0,
            'is_default': False
        }
        
        # 加载现有自定义模板
        custom_data = self._load_custom_templates()
        
        # 添加新模板
        if 'templates' not in custom_data:
            custom_data['templates'] = []
        custom_data['templates'].append(new_template)
        
        # 保存到文件
        try:
            with open(self.custom_file, 'w', encoding='utf-8') as f:
                json.dump(custom_data, f, ensure_ascii=False, indent=2)
            
            # 清除缓存
            self._custom_templates_cache = None
            
            api_logger.info(f"[QuestionTemplate] ✅ 保存自定义模板：{template_id}")
            
            return new_template
            
        except Exception as e:
            api_logger.error(f"[QuestionTemplate] ❌ 保存自定义模板失败：{e}")
            raise
    
    def delete_custom_template(self, template_id: str, user_id: str) -> bool:
        """
        删除自定义模板
        
        参数:
            template_id: 模板 ID
            user_id: 用户 ID
            
        返回:
            bool: 是否删除成功
        """
        # 加载自定义模板
        custom_data = self._load_custom_templates()
        
        # 查找并删除
        original_count = len(custom_data.get('templates', []))
        custom_data['templates'] = [
            tpl for tpl in custom_data.get('templates', [])
            if not (tpl.get('id') == template_id and tpl.get('user_id') == user_id)
        ]
        
        if len(custom_data['templates']) < original_count:
            # 保存到文件
            try:
                with open(self.custom_file, 'w', encoding='utf-8') as f:
                    json.dump(custom_data, f, ensure_ascii=False, indent=2)
                
                # 清除缓存
                self._custom_templates_cache = None
                
                api_logger.info(f"[QuestionTemplate] ✅ 删除自定义模板：{template_id}")
                return True
                
            except Exception as e:
                api_logger.error(f"[QuestionTemplate] ❌ 删除自定义模板失败：{e}")
                return False
        
        return False
    
    def increment_template_usage(self, template_id: str) -> None:
        """
        增加模板使用次数
        
        参数:
            template_id: 模板 ID
        """
        # 只处理预定义模板
        templates_data = self._load_templates()
        
        for tpl in templates_data.get('templates', []):
            if tpl.get('id') == template_id:
                tpl['usage_count'] = tpl.get('usage_count', 0) + 1
                
                # 保存回文件
                try:
                    with open(self.templates_file, 'w', encoding='utf-8') as f:
                        json.dump(templates_data, f, ensure_ascii=False, indent=2)
                    
                    # 清除缓存
                    self._templates_cache = None
                    
                    api_logger.debug(f"[QuestionTemplate] 模板使用次数 +1: {template_id}")
                except Exception as e:
                    api_logger.error(f"[QuestionTemplate] 更新使用次数失败：{e}")
                break
    
    def get_categories(self) -> List[str]:
        """获取所有分类"""
        templates_data = self._load_templates()
        return templates_data.get('categories', [])
    
    def get_industries(self) -> List[str]:
        """获取所有行业"""
        templates_data = self._load_templates()
        return templates_data.get('industries', [])
    
    def replace_brand_placeholder(self, questions: List[str], brand_name: str) -> List[str]:
        """
        替换问题中的品牌占位符
        
        参数:
            questions: 问题列表
            brand_name: 品牌名称
            
        返回:
            List[str]: 替换后的问题列表
        """
        return [q.replace('{brand}', brand_name) for q in questions]


# 全局单例
_template_service: Optional[QuestionTemplateService] = None


def get_template_service() -> QuestionTemplateService:
    """获取模板服务单例"""
    global _template_service
    if _template_service is None:
        _template_service = QuestionTemplateService()
    return _template_service
