#!/usr/bin/env python3
"""
AI 响应日志备份和迁移脚本

功能:
1. 备份当前日志文件
2. 压缩旧日志
3. 清理超出数量的备份
"""

import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path

# 配置
LOG_DIR = Path('/Users/sgl/PycharmProjects/PythonProject/backend_python/wechat_backend/data/ai_responses')
LOG_FILE = LOG_DIR / 'ai_responses.jsonl'
BACKUP_DIR = LOG_DIR / 'backups'
MAX_BACKUP_COUNT = 10
COMPRESSION_ENABLED = True

def create_backup():
    """创建当前日志文件的备份"""
    if not LOG_FILE.exists():
        print("⚠️  日志文件不存在，跳过备份")
        return None
    
    # 创建备份目录
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"ai_responses_{timestamp}.jsonl"
    backup_path = BACKUP_DIR / backup_name
    
    # 移动日志文件到备份目录
    shutil.move(str(LOG_FILE), str(backup_path))
    print(f"✅ 备份完成：{backup_name}")
    
    # 压缩备份
    if COMPRESSION_ENABLED:
        compressed_path = backup_path.with_suffix('.jsonl.gz')
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 删除未压缩文件
        backup_path.unlink()
        
        # 计算压缩率
        original_size = backup_path.stat().st_size if backup_path.exists() else 0
        compressed_size = compressed_path.stat().st_size
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        
        print(f"✅ 压缩完成：{compressed_path.name} (压缩率：{compression_ratio:.1f}%)")
        return compressed_path
    
    return backup_path

def cleanup_old_backups():
    """清理旧备份文件"""
    if not BACKUP_DIR.exists():
        return
    
    # 获取所有备份文件
    backup_files = []
    for pattern in ['ai_responses_*.jsonl', 'ai_responses_*.jsonl.gz']:
        backup_files.extend(BACKUP_DIR.glob(pattern))
    
    # 按修改时间排序
    backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # 删除超出数量的旧文件
    if len(backup_files) > MAX_BACKUP_COUNT:
        files_to_delete = backup_files[MAX_BACKUP_COUNT:]
        for file_path in files_to_delete:
            file_size_mb = file_path.stat().st_size / 1024 / 1024
            file_path.unlink()
            print(f"🗑️  删除旧备份：{file_path.name} ({file_size_mb:.2f}MB)")
    
    # 统计
    remaining = backup_files[:MAX_BACKUP_COUNT]
    total_size = sum(f.stat().st_size for f in remaining)
    print(f"📊 当前备份：{len(remaining)}/{MAX_BACKUP_COUNT} 文件，总计 {total_size / 1024 / 1024:.2f}MB")

def show_stats():
    """显示日志统计信息"""
    print("\n📊 日志统计:")
    print("=" * 50)
    
    # 当前文件
    if LOG_FILE.exists():
        size_mb = LOG_FILE.stat().st_size / 1024 / 1024
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = sum(1 for _ in f)
        print(f"当前文件：{LOG_FILE.name}")
        print(f"  大小：{size_mb:.2f}MB")
        print(f"  记录数：{lines}")
    else:
        print("当前文件：不存在")
    
    # 备份文件
    if BACKUP_DIR.exists():
        backup_files = []
        for pattern in ['ai_responses_*.jsonl', 'ai_responses_*.jsonl.gz']:
            backup_files.extend(BACKUP_DIR.glob(pattern))
        
        total_size = sum(f.stat().st_size for f in backup_files)
        print(f"\n备份文件：{len(backup_files)} 个")
        print(f"  总计：{total_size / 1024 / 1024:.2f}MB")
        
        # 显示最近的备份
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        print("\n最近的备份:")
        for f in backup_files[:5]:
            size_mb = f.stat().st_size / 1024 / 1024
            mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
            print(f"  {f.name} ({size_mb:.2f}MB) - {mtime}")
    else:
        print("\n备份目录：不存在")

if __name__ == "__main__":
    import sys
    
    print("=" * 50)
    print("AI 响应日志备份和迁移工具 V3")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'backup':
            print("\n🔄 创建备份...")
            create_backup()
            cleanup_old_backups()
        
        elif command == 'cleanup':
            print("\n🗑️  清理旧备份...")
            cleanup_old_backups()
        
        elif command == 'stats':
            show_stats()
        
        else:
            print(f"\n❌ 未知命令：{command}")
            print("\n可用命令:")
            print("  backup   - 创建备份")
            print("  cleanup  - 清理旧备份")
            print("  stats    - 显示统计信息")
    else:
        # 默认显示统计信息
        show_stats()
        print("\n💡 提示:")
        print("  运行 'python3 migrate_to_v3.py backup' 创建备份")
        print("  运行 'python3 migrate_to_v3.py cleanup' 清理旧备份")
