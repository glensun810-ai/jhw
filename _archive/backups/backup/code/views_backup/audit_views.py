"""
Audit 相关视图模块
"""

# 从__init__.py 导入共享的蓝图实例
from . import wechat_bp

from flask import request, jsonify
from wechat_backend.logging_config import api_logger

# Global store for execution progress (in production, use Redis or database)
execution_store = {}

# ============================================================================
# 健康检查 API（临时测试端点）
# ============================================================================

@wechat_bp.route('/api/test', methods=['GET', 'OPTIONS'])
def test_api():
    """
    健康检查接口
    用于测试后端服务是否正常运行
    """
    # 处理 CORS 预检请求
    if request.method == 'OPTIONS':
        response = jsonify({'status': 'ok'})
        return response, 200

    api_logger.info('Health check: /api/test called')
    return jsonify({
        'message': 'Backend is working correctly!',
        'status': 'success'
    }), 200
