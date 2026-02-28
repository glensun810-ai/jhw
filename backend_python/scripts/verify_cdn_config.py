#!/usr/bin/env python3
"""
CDN 配置验证脚本

用于验证 CDN 配置是否正确，测试 CDN 功能是否正常工作。

使用方法:
    python backend_python/scripts/verify_cdn_config.py

参考：P2-5: CDN 加速未配置
"""

import sys
import os
from pathlib import Path

# 添加 backend_python 到路径
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from config.config_cdn import CDNConfig
from utils.cdn_helper import (
    get_static_url,
    get_report_url,
    get_cache_headers,
    generate_file_hash,
)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_item(name: str, value, status: str = "OK"):
    """打印配置项"""
    status_icon = "✅" if status == "OK" else "❌" if status == "ERROR" else "⚠️"
    print(f"{status_icon} {name}: {value}")


def verify_cdn_config():
    """验证 CDN 基础配置"""
    print_section("CDN 基础配置验证")
    
    print_item("CDN 启用状态", CDNConfig.CDN_ENABLED)
    print_item("CDN 域名", CDNConfig.CDN_DOMAIN or "未配置")
    print_item("CDN 协议", CDNConfig.CDN_PROTOCOL)
    print_item("静态资源版本", CDNConfig.STATIC_VERSION)
    
    # 验证配置完整性
    if CDNConfig.CDN_ENABLED:
        if not CDNConfig.CDN_DOMAIN:
            print_item("CDN 配置状态", "CDN 已启用但域名未配置", "ERROR")
            return False
        else:
            print_item("CDN 配置状态", "配置完整", "OK")
    else:
        print_item("CDN 配置状态", "CDN 未启用（开发模式）", "OK")
    
    return True


def verify_oss_config():
    """验证 OSS 配置"""
    print_section("OSS 对象存储配置验证")
    
    print_item("OSS 提供商", CDNConfig.OSS_PROVIDER)
    print_item("OSS Access Key", "已配置" if CDNConfig.OSS_ACCESS_KEY_ID else "未配置")
    print_item("OSS Secret Key", "已配置" if CDNConfig.OSS_ACCESS_KEY_SECRET else "未配置")
    print_item("OSS 存储桶", CDNConfig.OSS_BUCKET_NAME or "未配置")
    print_item("OSS 区域", CDNConfig.OSS_BUCKET_REGION or "未配置")
    print_item("OSS 端点", CDNConfig.OSS_ENDPOINT or "未配置")
    print_item("OSS CDN 域名", CDNConfig.OSS_CDN_DOMAIN or "未配置")
    
    # 验证 OSS 配置
    is_configured = CDNConfig.is_oss_configured()
    if is_configured:
        print_item("OSS 配置状态", "配置完整", "OK")
    else:
        print_item("OSS 配置状态", "未配置或部分配置缺失", "OK")
    
    return True


def verify_cache_config():
    """验证缓存配置"""
    print_section("缓存配置验证")
    
    print_item("缓存控制启用", CDNConfig.CACHE_CONTROL_ENABLED)
    print_item("缓存类型", CDNConfig.CACHE_CONTROL_TYPE)
    print_item("静态资源缓存时间", f"{CDNConfig.STATIC_CACHE_MAX_AGE}s ({CDNConfig.STATIC_CACHE_MAX_AGE // 86400}天)")
    print_item("HTML 缓存时间", f"{CDNConfig.HTML_CACHE_MAX_AGE}s ({CDNConfig.HTML_CACHE_MAX_AGE // 3600}小时)")
    print_item("API 缓存时间", f"{CDNConfig.API_CACHE_MAX_AGE}s ({CDNConfig.API_CACHE_MAX_AGE // 60}分钟)")
    print_item("报告缓存时间", f"{CDNConfig.REPORT_CACHE_MAX_AGE}s ({CDNConfig.REPORT_CACHE_MAX_AGE // 3600}小时)")
    
    return True


def verify_storage_config():
    """验证存储配置"""
    print_section("存储配置验证")
    
    print_item("存储类型", CDNConfig.REPORT_STORAGE_TYPE)
    print_item("本地存储目录", CDNConfig.REPORT_STORAGE_DIR)
    print_item("OSS 存储前缀", CDNConfig.REPORT_OSS_PREFIX)
    
    # 检查本地存储目录
    if CDNConfig.REPORT_STORAGE_TYPE == 'local':
        report_dir = Path(CDNConfig.REPORT_STORAGE_DIR)
        if report_dir.exists():
            print_item("本地存储目录", "存在", "OK")
        else:
            print_item("本地存储目录", "不存在，将自动创建", "OK")
            report_dir.mkdir(parents=True, exist_ok=True)
    
    return True


def test_url_generation():
    """测试 URL 生成功能"""
    print_section("URL 生成功能测试")
    
    # 测试静态资源 URL
    test_paths = [
        '/static/js/app.js',
        '/static/css/main.css',
        '/static/images/logo.png',
    ]
    
    print("静态资源 URL 生成:")
    for path in test_paths:
        url = get_static_url(path)
        print_item(f"  {path}", url)
    
    # 测试报告 URL
    print("\n报告文件 URL 生成:")
    test_filenames = [
        'report_test-123_20260228_120000.json',
        'report_test-456_20260228_120000.pdf',
    ]
    
    for filename in test_filenames:
        url = get_report_url(filename)
        print_item(f"  {filename}", url)
    
    return True


def test_cache_headers():
    """测试缓存头生成"""
    print_section("缓存头生成测试")
    
    file_types = ['static', 'html', 'api', 'report']
    
    for file_type in file_types:
        headers = get_cache_headers(file_type)
        print(f"\n{file_type} 类型文件缓存头:")
        for header, value in headers.items():
            print_item(f"  {header}", value)
    
    return True


def test_file_hash():
    """测试文件哈希生成"""
    print_section("文件哈希生成测试")
    
    # 创建一个测试文件
    test_file = backend_root / 'test_cdn_temp.txt'
    test_content = b'Test content for CDN verification'
    
    try:
        # 写入测试文件
        with open(test_file, 'wb') as f:
            f.write(test_content)
        
        # 生成哈希
        file_hash = generate_file_hash(str(test_file))
        print_item("测试文件内容", f"{len(test_content)} bytes")
        print_item("生成的 MD5 哈希", file_hash)
        
        # 删除测试文件
        test_file.unlink()
        print_item("测试文件", "已清理", "OK")
        
    except Exception as e:
        print_item("文件哈希测试", f"失败：{e}", "ERROR")
        return False
    
    return True


def validate_full_config():
    """完整配置验证"""
    print_section("完整配置验证")
    
    is_valid, errors = CDNConfig.validate_config()
    
    if is_valid:
        print_item("配置验证结果", "通过", "OK")
    else:
        print_item("配置验证结果", "失败", "ERROR")
        print("\n错误列表:")
        for error in errors:
            print_item(f"  - {error}", "", "ERROR")
    
    return is_valid


def print_summary():
    """打印总结"""
    print_section("验证总结")
    
    print("""
CDN 配置验证完成！

下一步操作:

1. 启用 CDN（生产环境）:
   - 编辑 .env 文件
   - 设置 CDN_ENABLED=true
   - 配置 CDN_DOMAIN=cdn.yourdomain.com

2. 配置 OSS（可选）:
   - 设置 OSS_ACCESS_KEY_ID
   - 设置 OSS_ACCESS_KEY_SECRET
   - 设置 OSS_BUCKET_NAME
   - 设置 OSS_ENDPOINT

3. 重启 Flask 应用:
   cd backend_python
   python main.py

4. 验证 CDN 功能:
   curl http://localhost:5000/api/cdn/config
   curl http://localhost:5000/api/cdn/validate

5. 查看详细文档:
   docs/2026-02-28-P2-5-CDN 加速配置实现报告.md
""")


def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           P2-5: CDN 加速配置验证脚本                        ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
""")
    
    # 执行验证
    results = []
    
    results.append(("CDN 基础配置", verify_cdn_config()))
    results.append(("OSS 配置", verify_oss_config()))
    results.append(("缓存配置", verify_cache_config()))
    results.append(("存储配置", verify_storage_config()))
    results.append(("URL 生成测试", test_url_generation()))
    results.append(("缓存头测试", test_cache_headers()))
    results.append(("文件哈希测试", test_file_hash()))
    results.append(("完整配置验证", validate_full_config()))
    
    # 打印总结
    print_summary()
    
    # 返回结果
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✅ 所有验证通过！")
        return 0
    else:
        print("\n❌ 部分验证失败，请检查上述错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
