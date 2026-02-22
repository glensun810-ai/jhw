"""
管理后台入口 - 重构简化版

重构说明:
- 用户管理 → admin_user_management.py
- 测试管理 → admin_test_management.py
- 系统管理 → admin_system.py

本文件保留:
- 蓝图注册
- 模块导入协调
"""

from flask import Blueprint
from wechat_backend.logging_config import api_logger

# 创建管理员蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def init_admin_routes(app):
    """
    初始化所有管理后台路由
    
    参数:
    - app: Flask 应用实例
    """
    api_logger.info("Initializing admin routes...")

    # 导入并注册子模块
    from wechat_backend.admin_user_management import init_user_management_routes
    from wechat_backend.admin_test_management import init_test_management_routes
    from wechat_backend.admin_system import init_system_management_routes

    # 注册所有子模块
    init_user_management_routes(app)
    init_test_management_routes(app)
    init_system_management_routes(app)

    # 注册主蓝图（用于通用管理功能）
    app.register_blueprint(admin_bp)

    api_logger.info("Admin routes initialized successfully")


# 导出蓝图供其他模块使用
__all__ = ['admin_bp', 'init_admin_routes']
