# 延迟导入以避免循环导入问题
_app = None

def get_app():
    """获取 app 实例"""
    global _app
    if _app is None:
        from wechat_backend.app import app
        _app = app
    return _app

def create_app():
    """创建并返回 app 实例"""
    return get_app()

__all__ = ['get_app', 'create_app']
