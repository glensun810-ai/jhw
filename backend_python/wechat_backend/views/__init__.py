"""
视图模块 - 路由拆分后的蓝图注册

重构版本：v2.0
将原 views.py (4,440 行) 拆分为以下模块：
- diagnosis_views: 诊断相关路由 (品牌诊断、测试执行、进度查询)
- user_views: 用户相关路由 (登录、注册、用户资料)
- report_views: 报告相关路由 (PDF 导出、高管报告)
- admin_views: 管理后台路由 (测试记录、仪表盘)
- analytics_views: 分析相关路由 (AI 平台、巡航任务、市场基准)
- audit_views: 审计相关路由 (测试 API)
- sync_views: 同步相关路由 (数据同步、下载)
"""

from flask import Blueprint

# 创建主蓝图
wechat_bp = Blueprint('wechat', __name__)

# 导入所有视图模块（模块加载时会自动注册路由）
# 注意：所有子模块共享同一个 wechat_bp 蓝图实例
from . import diagnosis_views
from . import user_views
from . import report_views
from . import admin_views
from . import analytics_views
from . import audit_views
from . import sync_views

# 导出主蓝图供 app.py 使用
__all__ = ['wechat_bp']
