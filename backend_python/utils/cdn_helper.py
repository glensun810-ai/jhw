"""
CDN 辅助模块（占位符）

此模块用于 CDN 加速服务的辅助功能
当前为占位实现，实际项目中应使用真实 CDN 服务
"""

import os
from wechat_backend.logging_config import api_logger


def get_cache_headers(resource_type: str = 'static') -> dict:
    """
    获取缓存头配置

    Args:
        resource_type: 资源类型 ('static', 'dynamic', 'api')

    Returns:
        缓存头字典
    """
    cache_configs = {
        'static': {
            'Cache-Control': 'public, max-age=31536000',
            'CDN-Cache-Control': 'public, max-age=31536000'
        },
        'dynamic': {
            'Cache-Control': 'private, no-cache, no-store',
            'CDN-Cache-Control': 'private, no-cache'
        },
        'api': {
            'Cache-Control': 'no-store, no-cache, must-revalidate',
            'CDN-Cache-Control': 'no-cache'
        }
    }

    return cache_configs.get(resource_type, cache_configs['static'])


def get_static_url(path: str, cdn_domain: str = None) -> str:
    """
    生成静态资源 CDN URL

    Args:
        path: 资源路径
        cdn_domain: CDN 域名（可选）

    Returns:
        完整的 CDN URL 或本地路径
    """
    if not cdn_domain:
        # 返回本地路径
        return f"/static/{path.lstrip('/')}"

    # 返回 CDN URL
    return f"https://{cdn_domain}/static/{path.lstrip('/')}"


def upload_to_oss(file_path: str, object_key: str, bucket: str = None) -> bool:
    """
    上传文件到 OSS（占位实现）

    Args:
        file_path: 本地文件路径
        object_key: OSS 对象键
        bucket: 存储桶名称（可选）

    Returns:
        bool: 上传是否成功
    """
    # 占位实现，始终返回 False
    api_logger.warning(f"[CDN] upload_to_oss 未实现：file={file_path}, key={object_key}")
    return False


def get_oss_url(object_key: str, bucket: str = None, expires: int = 3600) -> str:
    """
    获取 OSS 文件 URL（占位实现）

    Args:
        object_key: OSS 对象键
        bucket: 存储桶名称（可选）
        expires: URL 过期时间（秒）

    Returns:
        OSS URL 字符串
    """
    # 占位实现，返回空字符串
    return ""


# 默认配置
DEFAULT_CDN_DOMAIN = None


def init_cdn_helper(app=None):
    """
    初始化 CDN 辅助模块

    Args:
        app: Flask 应用实例（可选）
    """
    if app and hasattr(app, 'config'):
        global DEFAULT_CDN_DOMAIN
        DEFAULT_CDN_DOMAIN = app.config.get('CDN_DOMAIN', None)
