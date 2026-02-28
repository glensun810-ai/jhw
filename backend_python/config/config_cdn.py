"""
CDN 加速配置模块

功能：
- CDN 域名配置
- 静态资源版本管理
- OSS 对象存储配置
- CDN 缓存策略

参考：P2-5: CDN 加速未配置
"""

import os
from typing import Optional


class CDNConfig:
    """CDN 配置类"""
    
    # ==================== CDN 基础配置 ====================
    
    # 是否启用 CDN 加速
    CDN_ENABLED = os.environ.get('CDN_ENABLED', 'false').lower() == 'true'
    
    # CDN 域名（替换为你的实际 CDN 域名）
    CDN_DOMAIN = os.environ.get('CDN_DOMAIN', '')  # 例如：cdn.example.com
    
    # CDN 协议（http 或 https）
    CDN_PROTOCOL = os.environ.get('CDN_PROTOCOL', 'https')
    
    # ==================== 静态资源配置 ====================
    
    # 静态资源 CDN 路径
    STATIC_CDN_PATH = os.environ.get('STATIC_CDN_PATH', '/static')
    
    # 静态资源版本号（用于缓存失效）
    STATIC_VERSION = os.environ.get('STATIC_VERSION', 'v2.0.0')
    
    # 需要 CDN 加速的静态文件类型
    STATIC_FILE_TYPES = [
        '.js',
        '.css',
        '.png',
        '.jpg',
        '.jpeg',
        '.gif',
        '.svg',
        '.woff',
        '.woff2',
        '.ttf',
        '.eot',
    ]
    
    # ==================== OSS 对象存储配置 ====================
    
    # OSS 提供商（aliyun, tencent, qiniu）
    OSS_PROVIDER = os.environ.get('OSS_PROVIDER', 'aliyun')
    
    # OSS 访问密钥
    OSS_ACCESS_KEY_ID = os.environ.get('OSS_ACCESS_KEY_ID', '')
    OSS_ACCESS_KEY_SECRET = os.environ.get('OSS_ACCESS_KEY_SECRET', '')
    
    # OSS 存储桶配置
    OSS_BUCKET_NAME = os.environ.get('OSS_BUCKET_NAME', '')
    OSS_BUCKET_REGION = os.environ.get('OSS_BUCKET_REGION', '')  # 例如：oss-cn-hangzhou
    
    # OSS 端点
    OSS_ENDPOINT = os.environ.get('OSS_ENDPOINT', '')  # 例如：oss-cn-hangzhou.aliyuncs.com
    
    # OSS CDN 域名（用于加速文件访问）
    OSS_CDN_DOMAIN = os.environ.get('OSS_CDN_DOMAIN', '')  # 例如：cdn-oss.example.com
    
    # ==================== 报告文件存储配置 ====================
    
    # 报告文件存储路径（本地或 OSS）
    REPORT_STORAGE_TYPE = os.environ.get('REPORT_STORAGE_TYPE', 'local')  # local 或 oss
    
    # 本地报告存储目录
    REPORT_STORAGE_DIR = os.environ.get('REPORT_STORAGE_DIR', 'reports')
    
    # OSS 报告存储路径前缀
    REPORT_OSS_PREFIX = os.environ.get('REPORT_OSS_PREFIX', 'diagnosis-reports')
    
    # ==================== CDN 缓存策略 ====================
    
    # 静态资源缓存时间（秒）
    STATIC_CACHE_MAX_AGE = int(os.environ.get('STATIC_CACHE_MAX_AGE', '2592000'))  # 默认 30 天
    
    # HTML 文件缓存时间（秒）
    HTML_CACHE_MAX_AGE = int(os.environ.get('HTML_CACHE_MAX_AGE', '3600'))  # 默认 1 小时
    
    # API 响应缓存时间（秒）
    API_CACHE_MAX_AGE = int(os.environ.get('API_CACHE_MAX_AGE', '300'))  # 默认 5 分钟
    
    # 报告文件缓存时间（秒）
    REPORT_CACHE_MAX_AGE = int(os.environ.get('REPORT_CACHE_MAX_AGE', '86400'))  # 默认 1 天
    
    # ==================== 缓存控制头配置 ====================
    
    # 是否启用缓存控制头
    CACHE_CONTROL_ENABLED = os.environ.get('CACHE_CONTROL_ENABLED', 'true').lower() == 'true'
    
    # 缓存控制头类型（public, private, no-cache, no-store）
    CACHE_CONTROL_TYPE = os.environ.get('CACHE_CONTROL_TYPE', 'public')
    
    # ==================== 资源预加载配置 ====================
    
    # 是否启用资源预加载
    PRELOAD_ENABLED = os.environ.get('PRELOAD_ENABLED', 'false').lower() == 'true'
    
    # 预加载的关键资源列表
    PRELOAD_RESOURCES = [
        '/static/css/main.css',
        '/static/js/app.js',
        '/static/js/vendor.js',
    ]
    
    # ==================== CDN 提供商特定配置 ====================
    
    @classmethod
    def get_aliyun_config(cls) -> dict:
        """获取阿里云 OSS 配置"""
        return {
            'access_key_id': cls.OSS_ACCESS_KEY_ID,
            'access_key_secret': cls.OSS_ACCESS_KEY_SECRET,
            'bucket_name': cls.OSS_BUCKET_NAME,
            'endpoint': cls.OSS_ENDPOINT,
            'cdn_domain': cls.OSS_CDN_DOMAIN,
        }
    
    @classmethod
    def get_tencent_config(cls) -> dict:
        """获取腾讯云 COS 配置"""
        return {
            'secret_id': cls.OSS_ACCESS_KEY_ID,
            'secret_key': cls.OSS_ACCESS_KEY_SECRET,
            'bucket': cls.OSS_BUCKET_NAME,
            'region': cls.OSS_BUCKET_REGION,
            'cdn_domain': cls.OSS_CDN_DOMAIN,
        }
    
    @classmethod
    def get_qiniu_config(cls) -> dict:
        """获取七牛云 Kodo 配置"""
        return {
            'access_key': cls.OSS_ACCESS_KEY_ID,
            'secret_key': cls.OSS_ACCESS_KEY_SECRET,
            'bucket': cls.OSS_BUCKET_NAME,
            'cdn_domain': cls.OSS_CDN_DOMAIN,
        }
    
    # ==================== 工具方法 ====================
    
    @classmethod
    def get_cdn_base_url(cls) -> str:
        """
        获取 CDN 基础 URL
        
        Returns:
            CDN 基础 URL，如果未配置则返回空字符串
        """
        if cls.CDN_ENABLED and cls.CDN_DOMAIN:
            return f"{cls.CDN_PROTOCOL}://{cls.CDN_DOMAIN}"
        return ''
    
    @classmethod
    def get_oss_base_url(cls) -> str:
        """
        获取 OSS CDN 基础 URL
        
        Returns:
            OSS CDN 基础 URL，如果未配置则返回空字符串
        """
        if cls.CDN_ENABLED and cls.OSS_CDN_DOMAIN:
            return f"{cls.CDN_PROTOCOL}://{cls.OSS_CDN_DOMAIN}"
        return ''
    
    @classmethod
    def get_static_url(cls, path: str) -> str:
        """
        获取静态资源的完整 URL
        
        Args:
            path: 静态资源相对路径（例如：/static/js/app.js）
            
        Returns:
            完整的 URL（CDN 或本地）
        """
        # 如果启用了 CDN 且配置了域名
        if cls.CDN_ENABLED and cls.CDN_DOMAIN:
            # 确保路径以/开头
            if not path.startswith('/'):
                path = '/' + path
            return f"{cls.CDN_PROTOCOL}://{cls.CDN_DOMAIN}{path}"
        
        # 返回本地路径
        return path
    
    @classmethod
    def get_report_url(cls, filename: str) -> str:
        """
        获取报告文件的访问 URL
        
        Args:
            filename: 报告文件名
            
        Returns:
            完整的访问 URL
        """
        if cls.REPORT_STORAGE_TYPE == 'oss' and cls.OSS_CDN_DOMAIN:
            # OSS 存储，使用 CDN 加速
            return f"{cls.CDN_PROTOCOL}://{cls.OSS_CDN_DOMAIN}/{cls.REPORT_OSS_PREFIX}/{filename}"
        else:
            # 本地存储
            return f"/{cls.REPORT_STORAGE_DIR}/{filename}"
    
    @classmethod
    def get_cache_headers(cls, file_type: str = 'static') -> dict:
        """
        获取缓存控制头
        
        Args:
            file_type: 文件类型（static, html, api, report）
            
        Returns:
            缓存控制头字典
        """
        if not cls.CACHE_CONTROL_ENABLED:
            return {}
        
        cache_max_age_map = {
            'static': cls.STATIC_CACHE_MAX_AGE,
            'html': cls.HTML_CACHE_MAX_AGE,
            'api': cls.API_CACHE_MAX_AGE,
            'report': cls.REPORT_CACHE_MAX_AGE,
        }
        
        max_age = cache_max_age_map.get(file_type, cls.STATIC_CACHE_MAX_AGE)
        
        return {
            'Cache-Control': f'{cls.CACHE_CONTROL_TYPE}, max-age={max_age}',
            'Expires': cls._calculate_expires(max_age),
        }
    
    @classmethod
    def _calculate_expires(cls, max_age: int) -> str:
        """
        计算 Expires 头
        
        Args:
            max_age: 缓存最大年龄（秒）
            
        Returns:
            Expires 头的值
        """
        from datetime import datetime, timedelta
        expires_time = datetime.utcnow() + timedelta(seconds=max_age)
        return expires_time.strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    @classmethod
    def is_cdn_enabled(cls) -> bool:
        """
        检查 CDN 是否已启用
        
        Returns:
            bool: 是否启用
        """
        return cls.CDN_ENABLED and bool(cls.CDN_DOMAIN)
    
    @classmethod
    def is_oss_configured(cls) -> bool:
        """
        检查 OSS 是否已配置
        
        Returns:
            bool: 是否已配置
        """
        return bool(cls.OSS_ACCESS_KEY_ID and cls.OSS_BUCKET_NAME)
    
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        验证 CDN 配置是否完整
        
        Returns:
            (是否有效，错误信息列表)
        """
        errors = []
        
        if cls.CDN_ENABLED:
            if not cls.CDN_DOMAIN:
                errors.append('CDN_DOMAIN 未配置')
            
            if cls.REPORT_STORAGE_TYPE == 'oss':
                if not cls.OSS_ACCESS_KEY_ID:
                    errors.append('OSS_ACCESS_KEY_ID 未配置')
                if not cls.OSS_ACCESS_KEY_SECRET:
                    errors.append('OSS_ACCESS_KEY_SECRET 未配置')
                if not cls.OSS_BUCKET_NAME:
                    errors.append('OSS_BUCKET_NAME 未配置')
                if not cls.OSS_ENDPOINT:
                    errors.append('OSS_ENDPOINT 未配置')
        
        return len(errors) == 0, errors


# 导出配置实例
cdn_config = CDNConfig()
