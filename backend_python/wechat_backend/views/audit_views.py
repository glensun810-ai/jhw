"""
Audit 相关视图模块
"""

# 从__init__.py 导入共享的蓝图实例
from . import wechat_bp

from flask import request, jsonify
from wechat_backend.logging_config import api_logger

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

@wechat_bp.route('/api/test', methods=['GET', 'OPTIONS'])
# @rate_limit(limit=50, window=60, per='ip')  # 临时禁用
# @monitored_endpoint('/api/test', require_auth=False, validate_inputs=False)  # 临时禁用
def test_api():
    """
    健康检查接口
    用于测试后端服务是否正常运行
    """
    # 处理 CORS 预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        # CORS 已在 app.py 中统一配置，此处无需重复设置
        return response, 200
    
    api_logger.info('Health check: /api/test called')
    return jsonify({
        'message': 'Backend is working correctly!',
        'status': 'success'
    }), 200
