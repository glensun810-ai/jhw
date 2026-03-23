/**
 * 诊断问题模板库服务
 * 
 * 功能:
 * - 获取预定义模板列表
 * - 按分类/行业筛选模板
 * - 搜索模板
 * - 保存/删除自定义模板
 * 
 * @author: 系统架构组
 * @date: 2026-03-14
 * @version: 1.0.0
 */

import { request } from '../../utils/request';

class QuestionTemplateService {
  /**
   * 获取所有模板
   * @returns {Promise<Object>} 模板数据
   */
  async getAllTemplates() {
    try {
      const res = await request({
        url: '/api/diagnosis/templates',
        method: 'GET'
      });
      
      return res.data || res;
    } catch (error) {
      console.error('[QuestionTemplate] 获取模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 按分类获取模板
   * @param {string} category - 分类名称
   * @returns {Promise<Array>} 模板列表
   */
  async getTemplatesByCategory(category) {
    try {
      const res = await request({
        url: '/api/diagnosis/templates',
        method: 'GET',
        data: { category }
      });
      
      const allTemplates = res.data || res;
      return allTemplates.templates?.filter(tpl => tpl.category === category) || [];
    } catch (error) {
      console.error('[QuestionTemplate] 按分类获取模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 按行业获取模板
   * @param {string} industry - 行业名称
   * @returns {Promise<Array>} 模板列表
   */
  async getTemplatesByIndustry(industry) {
    try {
      const res = await request({
        url: '/api/diagnosis/templates',
        method: 'GET',
        data: { industry }
      });
      
      const allTemplates = res.data || res;
      return allTemplates.templates?.filter(tpl => tpl.industry === industry) || [];
    } catch (error) {
      console.error('[QuestionTemplate] 按行业获取模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 搜索模板
   * @param {string} keyword - 搜索关键词
   * @returns {Promise<Array>} 匹配的模板列表
   */
  async searchTemplates(keyword) {
    try {
      const res = await request({
        url: '/api/diagnosis/templates/search',
        method: 'POST',
        data: { keyword }
      });
      
      return res.data || res;
    } catch (error) {
      console.error('[QuestionTemplate] 搜索模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 根据 ID 获取模板
   * @param {string} templateId - 模板 ID
   * @returns {Promise<Object>} 模板数据
   */
  async getTemplateById(templateId) {
    try {
      const res = await request({
        url: `/api/diagnosis/templates/${templateId}`,
        method: 'GET'
      });
      
      return res.data || res;
    } catch (error) {
      console.error('[QuestionTemplate] 获取模板详情失败:', error);
      throw error;
    }
  }
  
  /**
   * 保存自定义模板
   * @param {Object} templateData - 模板数据
   * @returns {Promise<Object>} 保存后的模板
   */
  async saveCustomTemplate(templateData) {
    try {
      const res = await request({
        url: '/api/diagnosis/templates/custom',
        method: 'POST',
        data: templateData
      });
      
      return res.data || res;
    } catch (error) {
      console.error('[QuestionTemplate] 保存自定义模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 删除自定义模板
   * @param {string} templateId - 模板 ID
   * @returns {Promise<boolean>} 是否删除成功
   */
  async deleteCustomTemplate(templateId) {
    try {
      const res = await request({
        url: `/api/diagnosis/templates/custom/${templateId}`,
        method: 'DELETE'
      });
      
      return res.success || false;
    } catch (error) {
      console.error('[QuestionTemplate] 删除自定义模板失败:', error);
      throw error;
    }
  }
  
  /**
   * 获取所有分类
   * @returns {Promise<Array>} 分类列表
   */
  async getCategories() {
    try {
      const templates = await this.getAllTemplates();
      return templates.categories || [];
    } catch (error) {
      console.error('[QuestionTemplate] 获取分类失败:', error);
      return [];
    }
  }
  
  /**
   * 获取所有行业
   * @returns {Promise<Array>} 行业列表
   */
  async getIndustries() {
    try {
      const templates = await this.getAllTemplates();
      return templates.industries || [];
    } catch (error) {
      console.error('[QuestionTemplate] 获取行业失败:', error);
      return [];
    }
  }
  
  /**
   * 替换问题中的品牌占位符
   * @param {Array} questions - 问题列表
   * @param {string} brandName - 品牌名称
   * @returns {Array} 替换后的问题列表
   */
  replaceBrandPlaceholder(questions, brandName) {
    if (!Array.isArray(questions)) {
      return [];
    }
    return questions.map(q => q.replace(/{brand}/g, brandName));
  }
}

export default new QuestionTemplateService();
