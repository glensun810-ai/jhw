# 导入app实例
from .app import app

def create_app():
    """延迟导入以避免循环导入问题"""
    return app

__all__ = ['app', 'create_app']