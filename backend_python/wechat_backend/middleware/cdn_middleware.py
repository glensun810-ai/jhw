"""
CDN 中间件模块

功能：
- 静态资源 CDN 加速
- 缓存控制头设置
- OSS 文件服务

参考：P2-5: CDN 加速未配置
"""

import os
from flask import request, send_file, send_from_directory
from pathlib import Path
from wechat_backend.logging_config import app_logger


def setup_cdn_middleware(app):
    """
    设置 CDN 中间件
    
    Args:
        app: Flask 应用实例
    """
    from config.config_cdn import CDNConfig
    from utils.cdn_helper import get_cache_headers, get_static_url
    
    @app.before_request
    def cdn_request_handler():
        """处理 CDN 相关的请求"""
        # 仅在启用 CDN 时处理
        if not CDNConfig.CDN_ENABLED:
            return None
        
        # 记录 CDN 状态
        request.cdn_enabled = True
        return None
    
    @app.after_request
    def add_cdn_cache_headers(response):
        """
        添加 CDN 缓存控制头
        
        Args:
            response: Flask 响应对象
            
        Returns:
            添加缓存头后的响应
        """
        if not CDNConfig.CACHE_CONTROL_ENABLED:
            return response
        
        # 跳过已有缓存头的响应
        if 'Cache-Control' in response.headers:
            return response
        
        # 根据内容类型确定缓存策略
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'text/html' in content_type:
            cache_headers = get_cache_headers('html')
        elif 'application/json' in content_type:
            cache_headers = get_cache_headers('api')
        elif 'text/css' in content_type or 'javascript' in content_type:
            cache_headers = get_cache_headers('static')
        else:
            cache_headers = get_cache_headers('static')
        
        # 添加缓存头
        for header, value in cache_headers.items():
            response.headers[header] = value
        
        # 如果是静态资源，添加 CDN URL 头
        if request.path.startswith('/static/'):
            cdn_url = get_static_url(request.path)
            if cdn_url != request.path:
                response.headers['X-CDN-URL'] = cdn_url
        
        return response
    
    # 注册静态文件路由（如果使用了本地静态文件）
    if os.path.exists('static'):
        @app.route('/static/<path:filename>')
        def serve_static(filename):
            """提供静态文件服务"""
            static_folder = Path('static')
            file_path = static_folder / filename
            
            # 确定文件类型
            file_ext = os.path.splitext(filename)[1].lower()
            
            # 获取缓存头
            if file_ext in ['.html', '.htm']:
                cache_headers = get_cache_headers('html')
            else:
                cache_headers = get_cache_headers('static')
            
            # 发送文件
            response = send_from_directory(str(static_folder), filename)
            
            # 添加缓存头
            for header, value in cache_headers.items():
                response.headers[header] = value
            
            return response
    
    # 注册报告文件路由
    @app.route('/reports/<path:filename>')
    def serve_report(filename):
        """提供报告文件服务"""
        report_dir = Path(CDNConfig.REPORT_STORAGE_DIR)
        file_path = report_dir / filename
        
        if not file_path.exists():
            from flask import jsonify
            return jsonify({'error': 'Report not found'}), 404
        
        # 获取缓存头
        cache_headers = get_cache_headers('report')
        
        # 发送文件
        response = send_file(str(file_path))
        
        # 添加缓存头
        for header, value in cache_headers.items():
            response.headers[header] = value
        
        return response
    
    app_logger.info('CDN 中间件已加载')


def register_cdn_routes(app):
    """
    注册 CDN 相关的路由
    
    Args:
        app: Flask 应用实例
    """
    from flask import jsonify
    from config.config_cdn import CDNConfig
    from utils.cdn_helper import (
        upload_to_oss,
        prefetch_cdn_urls,
        refresh_cdn_cache,
    )
    
    @app.route('/api/cdn/config', methods=['GET'])
    def get_cdn_config():
        """获取 CDN 配置信息"""
        return jsonify({
            'enabled': CDNConfig.CDN_ENABLED,
            'domain': CDNConfig.CDN_DOMAIN if CDNConfig.CDN_ENABLED else None,
            'protocol': CDNConfig.CDN_PROTOCOL,
            'static_version': CDNConfig.STATIC_VERSION,
            'oss_provider': CDNConfig.OSS_PROVIDER,
            'oss_configured': CDNConfig.is_oss_configured(),
            'storage_type': CDNConfig.REPORT_STORAGE_TYPE,
        })
    
    @app.route('/api/cdn/upload', methods=['POST'])
    def upload_file_to_cdn():
        """
        上传文件到 CDN/OSS
        
        请求体：
            file: 文件对象
            object_key: OSS 对象键（可选）
        """
        from flask import request
        
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        object_key = request.form.get('object_key', file.filename)
        
        if not file.filename:
            return jsonify({'error': 'No file selected'}), 400
        
        # 保存临时文件
        temp_path = f'/tmp/{file.filename}'
        file.save(temp_path)
        
        # 上传到 OSS
        if upload_to_oss(temp_path, object_key):
            # 删除临时文件
            os.remove(temp_path)
            
            # 返回 CDN URL
            cdn_url = f"{CDNConfig.CDN_PROTOCOL}://{CDNConfig.OSS_CDN_DOMAIN}/{object_key}"
            return jsonify({
                'success': True,
                'cdn_url': cdn_url,
                'object_key': object_key
            })
        else:
            os.remove(temp_path)
            return jsonify({'error': 'Upload failed'}), 500
    
    @app.route('/api/cdn/prefetch', methods=['POST'])
    def prefetch_cdn():
        """
        预热 CDN 缓存
        
        请求体：
            urls: URL 列表
        """
        data = request.get_json()
        urls = data.get('urls', [])
        
        if not urls:
            return jsonify({'error': 'No URLs provided'}), 400
        
        if prefetch_cdn_urls(urls):
            return jsonify({
                'success': True,
                'message': f'Prefetched {len(urls)} URLs'
            })
        else:
            return jsonify({'error': 'Prefetch failed'}), 500
    
    @app.route('/api/cdn/refresh', methods=['POST'])
    def refresh_cdn():
        """
        刷新 CDN 缓存
        
        请求体：
            paths: 路径列表
        """
        data = request.get_json()
        paths = data.get('paths', [])
        
        if not paths:
            return jsonify({'error': 'No paths provided'}), 400
        
        if refresh_cdn_cache(paths):
            return jsonify({
                'success': True,
                'message': f'Refreshed {len(paths)} paths'
            })
        else:
            return jsonify({'error': 'Refresh failed'}), 500
    
    @app.route('/api/cdn/validate', methods=['GET'])
    def validate_cdn_config():
        """验证 CDN 配置"""
        is_valid, errors = CDNConfig.validate_config()
        
        return jsonify({
            'valid': is_valid,
            'errors': errors,
            'config': {
                'cdn_enabled': CDNConfig.CDN_ENABLED,
                'cdn_domain': CDNConfig.CDN_DOMAIN,
                'oss_provider': CDNConfig.OSS_PROVIDER,
                'oss_configured': CDNConfig.is_oss_configured(),
                'storage_type': CDNConfig.REPORT_STORAGE_TYPE,
            }
        })
    
    app_logger.info('CDN 路由已注册')


def init_cdn(app):
    """
    初始化 CDN 服务
    
    Args:
        app: Flask 应用实例
    """
    setup_cdn_middleware(app)
    register_cdn_routes(app)
