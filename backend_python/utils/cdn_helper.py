"""
CDN 工具函数模块

功能：
- 静态资源 URL 生成
- OSS 文件上传
- 缓存控制头设置
- CDN 预热和刷新

参考：P2-5: CDN 加速未配置
"""

import os
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)


def get_static_url(path: str, use_cdn: bool = True) -> str:
    """
    获取静态资源的 URL
    
    Args:
        path: 静态资源相对路径
        use_cdn: 是否使用 CDN
        
    Returns:
        完整的 URL
    """
    from config.config_cdn import CDNConfig
    
    if use_cdn and CDNConfig.CDN_ENABLED:
        return CDNConfig.get_static_url(path)
    return path


def get_report_url(filename: str) -> str:
    """
    获取报告文件的访问 URL
    
    Args:
        filename: 报告文件名
        
    Returns:
        完整的访问 URL
    """
    from config.config_cdn import CDNConfig
    return CDNConfig.get_report_url(filename)


def get_cache_headers(file_type: str = 'static') -> Dict[str, str]:
    """
    获取缓存控制头
    
    Args:
        file_type: 文件类型（static, html, api, report）
        
    Returns:
        缓存控制头字典
    """
    from config.config_cdn import CDNConfig
    return CDNConfig.get_cache_headers(file_type)


def generate_file_hash(file_path: str) -> str:
    """
    生成文件的 MD5 哈希值（用于版本控制）
    
    Args:
        file_path: 文件路径
        
    Returns:
        MD5 哈希值（前 8 位）
    """
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()[:8]


def versioned_static_path(path: str) -> str:
    """
    生成带版本号的静态资源路径
    
    Args:
        path: 原始路径
        
    Returns:
        带版本号的路径
    """
    from config.config_cdn import CDNConfig
    
    # 获取文件扩展名
    file_ext = os.path.splitext(path)[1]
    
    # 只对特定类型的文件添加版本号
    if file_ext in CDNConfig.STATIC_FILE_TYPES:
        # 在文件名后添加版本号
        base_name = os.path.splitext(path)[0]
        return f"{base_name}.{CDNConfig.STATIC_VERSION}{file_ext}"
    
    return path


def upload_to_oss(
    file_path: str,
    object_key: str,
    bucket_name: Optional[str] = None
) -> bool:
    """
    上传文件到 OSS
    
    Args:
        file_path: 本地文件路径
        object_key: OSS 对象键
        bucket_name: 存储桶名称（可选，使用默认配置）
        
    Returns:
        bool: 是否成功
    """
    from config.config_cdn import CDNConfig
    
    if not CDNConfig.is_oss_configured():
        logger.warning('OSS 未配置，无法上传文件')
        return False
    
    try:
        provider = CDNConfig.OSS_PROVIDER
        
        if provider == 'aliyun':
            return _upload_to_aliyun(file_path, object_key, bucket_name)
        elif provider == 'tencent':
            return _upload_to_tencent(file_path, object_key, bucket_name)
        elif provider == 'qiniu':
            return _upload_to_qiniu(file_path, object_key, bucket_name)
        else:
            logger.error(f'不支持的 OSS 提供商：{provider}')
            return False
            
    except Exception as e:
        logger.error(f'上传文件到 OSS 失败：{e}')
        return False


def _upload_to_aliyun(
    file_path: str,
    object_key: str,
    bucket_name: Optional[str] = None
) -> bool:
    """上传到阿里云 OSS"""
    try:
        import oss2
        
        from config.config_cdn import CDNConfig
        
        bucket = bucket_name or CDNConfig.OSS_BUCKET_NAME
        
        # 认证
        auth = oss2.Auth(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET
        )
        
        # 创建 Bucket 对象
        bucket_obj = oss2.Bucket(
            auth,
            CDNConfig.OSS_ENDPOINT,
            bucket
        )
        
        # 上传文件
        bucket_obj.put_object(object_key, open(file_path, 'rb'))
        
        logger.info(f'文件已上传到阿里云 OSS: {object_key}')
        return True
        
    except ImportError:
        logger.error('未安装 oss2 库，请运行：pip install oss2')
        return False
    except Exception as e:
        logger.error(f'上传到阿里云 OSS 失败：{e}')
        return False


def _upload_to_tencent(
    file_path: str,
    object_key: str,
    bucket_name: Optional[str] = None
) -> bool:
    """上传到腾讯云 COS"""
    try:
        from qcloud_cos import CosConfig
        from qcloud_cos import CosS3Client
        
        from config.config_cdn import CDNConfig
        
        bucket = bucket_name or CDNConfig.OSS_BUCKET_NAME
        region = CDNConfig.OSS_BUCKET_REGION
        
        # 配置
        config = CosConfig(
            Region=region,
            SecretId=CDNConfig.OSS_ACCESS_KEY_ID,
            SecretKey=CDNConfig.OSS_ACCESS_KEY_SECRET
        )
        
        # 创建客户端
        client = CosS3Client(config)
        
        # 上传文件
        with open(file_path, 'rb') as f:
            client.put_object(
                Bucket=bucket,
                Body=f,
                Key=object_key
            )
        
        logger.info(f'文件已上传到腾讯云 COS: {object_key}')
        return True
        
    except ImportError:
        logger.error('未安装 qcloud_cos 库，请运行：pip install qcloud-cos')
        return False
    except Exception as e:
        logger.error(f'上传到腾讯云 COS 失败：{e}')
        return False


def _upload_to_qiniu(
    file_path: str,
    object_key: str,
    bucket_name: Optional[str] = None
) -> bool:
    """上传到七牛云 Kodo"""
    try:
        import qiniu
        
        from config.config_cdn import CDNConfig
        
        bucket = bucket_name or CDNConfig.OSS_BUCKET_NAME
        
        # 构建鉴权对象
        auth = qiniu.Auth(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET
        )
        
        # 创建 Bucket 管理器
        bucket_manager = qiniu.BucketManager(auth)
        
        # 上传文件
        token = auth.upload_token(bucket)
        ret, info = qiniu.put_file(
            token,
            object_key,
            file_path
        )
        
        if info.status_code == 200:
            logger.info(f'文件已上传到七牛云 Kodo: {object_key}')
            return True
        else:
            logger.error(f'上传到七牛云 Kodo 失败：{info.error}')
            return False
        
    except ImportError:
        logger.error('未安装 qiniu 库，请运行：pip install qiniu')
        return False
    except Exception as e:
        logger.error(f'上传到七牛云 Kodo 失败：{e}')
        return False


def upload_report_to_oss(
    report_id: str,
    report_data: Dict[str, Any],
    report_dir: Optional[str] = None
) -> Optional[str]:
    """
    上传诊断报告到 OSS
    
    Args:
        report_id: 报告 ID
        report_data: 报告数据
        report_dir: 报告目录（可选）
        
    Returns:
        OSS 对象键，如果失败则返回 None
    """
    import json
    from config.config_cdn import CDNConfig
    
    if not CDNConfig.is_oss_configured():
        return None
    
    try:
        # 生成报告文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{report_id}_{timestamp}.json"
        
        # 构建对象键
        prefix = report_dir or CDNConfig.REPORT_OSS_PREFIX
        object_key = f"{prefix}/{filename}"
        
        # 创建临时文件
        temp_dir = Path(CDNConfig.REPORT_STORAGE_DIR)
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file_path = temp_dir / filename
        
        # 写入报告数据
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 上传到 OSS
        if upload_to_oss(str(temp_file_path), object_key):
            # 删除临时文件
            temp_file_path.unlink()
            return object_key
        else:
            return None
            
    except Exception as e:
        logger.error(f'上传报告到 OSS 失败：{e}')
        return None


def prefetch_cdn_urls(urls: List[str]) -> bool:
    """
    预热 CDN URL
    
    Args:
        urls: 需要预热的 URL 列表
        
    Returns:
        bool: 是否成功
    """
    from config.config_cdn import CDNConfig
    
    if not CDNConfig.CDN_ENABLED:
        return False
    
    provider = CDNConfig.OSS_PROVIDER
    
    try:
        if provider == 'aliyun':
            return _prefetch_aliyun(urls)
        elif provider == 'tencent':
            return _prefetch_tencent(urls)
        elif provider == 'qiniu':
            return _prefetch_qiniu(urls)
        else:
            logger.warning(f'不支持的 CDN 提供商：{provider}')
            return False
            
    except Exception as e:
        logger.error(f'CDN 预热失败：{e}')
        return False


def _prefetch_aliyun(urls: List[str]) -> bool:
    """预热阿里云 CDN"""
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcdn.request.v20180510 import RefreshObjectCachesRequest
        
        from config.config_cdn import CDNConfig
        
        # 创建客户端
        client = AcsClient(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET,
            CDNConfig.OSS_BUCKET_REGION.replace('oss-', '')
        )
        
        # 创建请求
        request = RefreshObjectCachesRequest.RefreshObjectCachesRequest()
        request.set_ObjectPath(','.join(urls))
        request.set_ObjectType('File')
        
        # 发送请求
        response = client.do_action_with_exception(request)
        
        logger.info(f'阿里云 CDN 预热成功：{len(urls)} 个 URL')
        return True
        
    except ImportError:
        logger.error('未安装 aliyunsdk 库')
        return False
    except Exception as e:
        logger.error(f'阿里云 CDN 预热失败：{e}')
        return False


def _prefetch_tencent(urls: List[str]) -> bool:
    """预热腾讯云 CDN"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.cdn.v20180606 import cdn_client, models
        
        from config.config_cdn import CDNConfig
        
        # 创建凭证
        cred = credential.DefaultCredentialProvider().get_credential()
        
        # 创建客户端
        client = cdn_client.CdnClient(cred, CDNConfig.OSS_BUCKET_REGION)
        
        # 创建请求
        req = models.PushUrlsCacheRequest()
        req.Params = json.dumps({'Urls': urls})
        
        # 发送请求
        resp = client.PushUrlsCache(req)
        
        logger.info(f'腾讯云 CDN 预热成功：{len(urls)} 个 URL')
        return True
        
    except ImportError:
        logger.error('未安装 tencentcloud-sdk-python 库')
        return False
    except Exception as e:
        logger.error(f'腾讯云 CDN 预热失败：{e}')
        return False


def _prefetch_qiniu(urls: List[str]) -> bool:
    """预热七牛云 CDN"""
    try:
        from qiniu.services.cdn import cdn
        
        from config.config_cdn import CDNConfig
        
        # 创建鉴权
        auth = qiniu.Auth(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET
        )
        
        # 预热 URL
        ret, info = cdn.prefetch_urls(auth, urls)
        
        if info.status_code == 200:
            logger.info(f'七牛云 CDN 预热成功：{len(urls)} 个 URL')
            return True
        else:
            logger.error(f'七牛云 CDN 预热失败：{info.error}')
            return False
        
    except ImportError:
        logger.error('未安装 qiniu 库')
        return False
    except Exception as e:
        logger.error(f'七牛云 CDN 预热失败：{e}')
        return False


def refresh_cdn_cache(paths: List[str]) -> bool:
    """
    刷新 CDN 缓存
    
    Args:
        paths: 需要刷新的路径列表
        
    Returns:
        bool: 是否成功
    """
    from config.config_cdn import CDNConfig
    
    if not CDNConfig.CDN_ENABLED:
        return False
    
    provider = CDNConfig.OSS_PROVIDER
    
    try:
        if provider == 'aliyun':
            return _refresh_aliyun(paths)
        elif provider == 'tencent':
            return _refresh_tencent(paths)
        elif provider == 'qiniu':
            return _refresh_qiniu(paths)
        else:
            logger.warning(f'不支持的 CDN 提供商：{provider}')
            return False
            
    except Exception as e:
        logger.error(f'CDN 缓存刷新失败：{e}')
        return False


def _refresh_aliyun(paths: List[str]) -> bool:
    """刷新阿里云 CDN 缓存"""
    try:
        from aliyunsdkcore.client import AcsClient
        from aliyunsdkcdn.request.v20180510 import RefreshObjectCachesRequest
        
        from config.config_cdn import CDNConfig
        
        client = AcsClient(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET,
            CDNConfig.OSS_BUCKET_REGION.replace('oss-', '')
        )
        
        request = RefreshObjectCachesRequest.RefreshObjectCachesRequest()
        request.set_ObjectPath(','.join(paths))
        request.set_ObjectType('File')
        
        response = client.do_action_with_exception(request)
        
        logger.info(f'阿里云 CDN 缓存刷新成功：{len(paths)} 个路径')
        return True
        
    except Exception as e:
        logger.error(f'阿里云 CDN 缓存刷新失败：{e}')
        return False


def _refresh_tencent(paths: List[str]) -> bool:
    """刷新腾讯云 CDN 缓存"""
    try:
        from tencentcloud.common import credential
        from tencentcloud.cdn.v20180606 import cdn_client, models
        
        from config.config_cdn import CDNConfig
        
        cred = credential.DefaultCredentialProvider().get_credential()
        client = cdn_client.CdnClient(cred, CDNConfig.OSS_BUCKET_REGION)
        
        req = models.PurgeUrlsCacheRequest()
        req.Params = json.dumps({'Urls': paths})
        
        resp = client.PurgeUrlsCache(req)
        
        logger.info(f'腾讯云 CDN 缓存刷新成功：{len(paths)} 个路径')
        return True
        
    except Exception as e:
        logger.error(f'腾讯云 CDN 缓存刷新失败：{e}')
        return False


def _refresh_qiniu(paths: List[str]) -> bool:
    """刷新七牛云 CDN 缓存"""
    try:
        from qiniu.services.cdn import cdn
        
        from config.config_cdn import CDNConfig
        
        auth = qiniu.Auth(
            CDNConfig.OSS_ACCESS_KEY_ID,
            CDNConfig.OSS_ACCESS_KEY_SECRET
        )
        
        ret, info = cdn.refresh_urls(auth, paths)
        
        if info.status_code == 200:
            logger.info(f'七牛云 CDN 缓存刷新成功：{len(paths)} 个路径')
            return True
        else:
            logger.error(f'七牛云 CDN 缓存刷新失败：{info.error}')
            return False
        
    except Exception as e:
        logger.error(f'七牛云 CDN 缓存刷新失败：{e}')
        return False


# 导出主要函数
__all__ = [
    'get_static_url',
    'get_report_url',
    'get_cache_headers',
    'generate_file_hash',
    'versioned_static_path',
    'upload_to_oss',
    'upload_report_to_oss',
    'prefetch_cdn_urls',
    'refresh_cdn_cache',
]
