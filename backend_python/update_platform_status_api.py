#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
更新 platform-status API 的脚本
"""
import re

file_path = '/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/views/diagnosis_views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 定义新的 get_platform_status 函数
new_function = '''@wechat_bp.route('/api/platform-status', methods=['GET'])
@require_auth_optional  # 可选身份验证，支持微信会话
@rate_limit(limit=20, window=60, per='endpoint')  # 限制每分钟 20 次请求
@monitored_endpoint('/api/platform-status', require_auth=False, validate_inputs=False)
def get_platform_status():
    """获取所有 AI 平台的状态信息（前端用于显示可用性和配置状态）"""
    try:
        # 从配置管理器获取平台状态
        from wechat_backend.config_manager import ConfigurationManager as PlatformConfigManager
        config_manager = PlatformConfigManager()
        
        # 从健康检查模块获取详细状态
        from wechat_backend.ai_adapters.platform_health_monitor import PlatformHealthMonitor
        health_results = PlatformHealthMonitor.run_health_check()

        status_info = {}

        # 预定义支持的平台（按前端显示顺序）
        domestic_platforms = [
            {'id': 'deepseek', 'name': 'DeepSeek'},
            {'id': 'doubao', 'name': '豆包'},
            {'id': 'qwen', 'name': '通义千问'},
            {'id': 'wenxin', 'name': '文心一言'},
        ]
        
        overseas_platforms = [
            {'id': 'chatgpt', 'name': 'ChatGPT'},
            {'id': 'gemini', 'name': 'Gemini'},
            {'id': 'zhipu', 'name': '智谱 AI'},
        ]

        # 处理国内平台
        for platform_info in domestic_platforms:
            platform = platform_info['id']
            config = config_manager.get_platform_config(platform)
            health_data = health_results.get('platforms', {}).get(platform, {})
            
            is_configured = bool(config and config.api_key)
            
            status_info[platform] = {
                'id': platform,
                'name': platform_info['name'],
                'isConfigured': is_configured,  # 【前端需要】是否已配置
                'status': 'active' if is_configured else 'inactive',
                'has_api_key': is_configured,
                'category': 'domestic',  # 【新增】平台类别
                'quota': {
                    'daily_limit': getattr(config, 'daily_limit', None) if config else None,
                    'used_today': getattr(config, 'used_today', 0) if config else 0,
                } if config and is_configured else None,
            }

        # 处理海外平台
        for platform_info in overseas_platforms:
            platform = platform_info['id']
            config = config_manager.get_platform_config(platform)
            health_data = health_results.get('platforms', {}).get(platform, {})
            
            is_configured = bool(config and config.api_key)
            
            status_info[platform] = {
                'id': platform,
                'name': platform_info['name'],
                'isConfigured': is_configured,  # 【前端需要】是否已配置
                'status': 'active' if is_configured else 'inactive',
                'has_api_key': is_configured,
                'category': 'overseas',  # 【新增】平台类别
            }

        return jsonify({
            'status': 'success',
            'platforms': status_info,
            'summary': {
                'total': len(domestic_platforms) + len(overseas_platforms),
                'configured': sum(1 for p in status_info.values() if p['isConfigured']),
                'unconfigured': sum(1 for p in status_info.values() if not p['isConfigured']),
            }
        })

    except Exception as e:
        api_logger.error(f"Error getting platform status: {e}")
        import traceback
        api_logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'status': 'error', 'message': str(e)}), 500'''

# 使用正则表达式替换旧函数
old_pattern = r"@wechat_bp\.route\('/api/platform-status'.*?return jsonify\(\{'status': 'error', 'message': str\(e\)\}\), 500"

content = re.sub(old_pattern, new_function, content, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated get_platform_status function")
