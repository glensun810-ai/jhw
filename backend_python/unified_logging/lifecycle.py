"""
日志生命周期管理模块

提供完整的日志生命周期管理功能，包括:
- 日志轮转 (基于大小/时间)
- 日志压缩 (GZIP)
- 日志清理 (过期删除)
- 日志归档
- 自动调度任务

使用示例:
    from backend_python.unified_logging.lifecycle import (
        LogLifecycleManager,
        LogRotator,
        LogCompressor,
        LogCleaner,
    )
    
    # 方式 1: 使用生命周期管理器
    manager = LogLifecycleManager(
        log_dir='logs',
        retention_days=30,
        max_size_mb=100,
        enable_compression=True,
    )
    manager.rotate()
    manager.compress_old_logs()
    manager.cleanup_old_logs()
    
    # 方式 2: 使用调度器
    from backend_python.unified_logging.lifecycle import LogScheduler
    
    scheduler = LogScheduler(manager)
    scheduler.start()
"""

import os
import sys
import gzip
import shutil
import time
import threading
import logging
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import argparse
import signal


# ============================================================================
# 枚举和常量
# ============================================================================

class RotationStrategy(Enum):
    """轮转策略"""
    SIZE = "size"  # 基于大小
    TIME = "time"  # 基于时间
    BOTH = "both"  # 两者都考虑


class CompressionAlgorithm(Enum):
    """压缩算法"""
    GZIP = "gzip"
    BZ2 = "bz2"
    LZMA = "lzma"


@dataclass
class LogFileInfo:
    """日志文件信息"""
    path: Path
    size: int
    created_time: float
    modified_time: float
    is_compressed: bool
    hash: Optional[str] = None
    
    @property
    def age_days(self) -> float:
        """文件年龄 (天)"""
        return (time.time() - self.created_time) / 86400
    
    @property
    def size_mb(self) -> float:
        """文件大小 (MB)"""
        return self.size / (1024 * 1024)
    
    @classmethod
    def from_path(cls, path: Path) -> 'LogFileInfo':
        """从路径创建"""
        stat = path.stat()
        is_compressed = path.suffix in ['.gz', '.bz2', '.xz']
        
        # 计算哈希
        file_hash = None
        try:
            with open(path, 'rb') as f:
                file_hash = hashlib.md5(f.read(8192)).hexdigest()
        except Exception:
            pass
        
        return cls(
            path=path,
            size=stat.st_size,
            created_time=stat.st_ctime,
            modified_time=stat.st_mtime,
            is_compressed=is_compressed,
            hash=file_hash,
        )


@dataclass
class LifecycleStats:
    """生命周期统计"""
    total_files: int = 0
    total_size_bytes: int = 0
    compressed_files: int = 0
    uncompressed_files: int = 0
    oldest_file_age_days: float = 0
    newest_file_age_days: float = 0
    files_by_age: Dict[str, int] = field(default_factory=dict)
    
    @property
    def total_size_mb(self) -> float:
        return self.total_size_bytes / (1024 * 1024)
    
    @property
    def total_size_gb(self) -> float:
        return self.total_size_bytes / (1024 * 1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_files': self.total_files,
            'total_size_mb': round(self.total_size_mb, 2),
            'total_size_gb': round(self.total_size_gb, 4),
            'compressed_files': self.compressed_files,
            'uncompressed_files': self.uncompressed_files,
            'oldest_file_age_days': round(self.oldest_file_age_days, 1),
            'compression_ratio': round(self.compressed_files / max(1, self.total_files) * 100, 1),
        }


# ============================================================================
# 日志轮转器
# ============================================================================

class LogRotator:
    """
    日志轮转器
    
    支持基于大小和时间的轮转策略。
    """
    
    def __init__(
        self,
        log_dir: str,
        max_size_mb: float = 100,
        max_backup_count: int = 10,
        rotation_strategy: RotationStrategy = RotationStrategy.BOTH,
        rotation_time: str = "00:00",  # HH:MM 格式
        file_pattern: str = "*.log",
    ):
        """
        初始化轮转器
        
        Args:
            log_dir: 日志目录
            max_size_mb: 单个文件最大大小 (MB)
            max_backup_count: 最大备份数量
            rotation_strategy: 轮转策略
            rotation_time: 轮转时间 (HH:MM)
            file_pattern: 文件匹配模式
        """
        self.log_dir = Path(log_dir)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.max_backup_count = max_backup_count
        self.rotation_strategy = rotation_strategy
        self.rotation_time = rotation_time
        self.file_pattern = file_pattern
        self._logger = logging.getLogger(__name__)
    
    def should_rotate(self, file_path: Path) -> bool:
        """判断是否需要轮转"""
        if not file_path.exists():
            return False
        
        # 基于大小的轮转
        if self.rotation_strategy in [RotationStrategy.SIZE, RotationStrategy.BOTH]:
            if file_path.stat().st_size >= self.max_size_bytes:
                return True
        
        # 基于时间的轮转
        if self.rotation_strategy in [RotationStrategy.TIME, RotationStrategy.BOTH]:
            if self._should_rotate_by_time(file_path):
                return True
        
        return False
    
    def _should_rotate_by_time(self, file_path: Path) -> bool:
        """判断是否需要基于时间轮转"""
        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime)
        
        # 解析轮转时间
        hour, minute = map(int, self.rotation_time.split(':'))
        
        # 如果文件修改时间早于今天的轮转时间，则需要轮转
        today_rotation_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        return mtime < today_rotation_time
    
    def rotate(self, file_path: Path) -> Optional[Path]:
        """
        轮转日志文件
        
        Returns:
            轮转后的文件路径
        """
        if not file_path.exists():
            return None
        
        # 生成新文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_path = file_path.parent / f"{file_path.stem}.{timestamp}{file_path.suffix}"
        
        # 移动文件
        shutil.move(str(file_path), str(rotated_path))
        
        self._logger.info(f"Rotated: {file_path.name} -> {rotated_path.name}")
        
        # 清理旧备份
        self._cleanup_old_backups(file_path.parent, file_path.stem, file_path.suffix)
        
        # 创建新的空文件
        file_path.touch()
        
        return rotated_path
    
    def _cleanup_old_backups(self, directory: Path, stem: str, suffix: str):
        """清理旧备份文件"""
        pattern = f"{stem}.*{suffix}"
        backup_files = sorted(directory.glob(pattern))
        
        # 删除超出备份数量的文件
        while len(backup_files) > self.max_backup_count:
            oldest = backup_files.pop(0)
            oldest.unlink()
            self._logger.info(f"Removed old backup: {oldest.name}")
    
    def rotate_all(self) -> List[Path]:
        """轮转所有匹配的日志文件"""
        rotated = []
        
        for file_path in self.log_dir.glob(self.file_pattern):
            if self.should_rotate(file_path):
                result = self.rotate(file_path)
                if result:
                    rotated.append(result)
        
        return rotated


# ============================================================================
# 日志压缩器
# ============================================================================

class LogCompressor:
    """
    日志压缩器
    
    支持 GZIP、BZ2、LZMA 压缩算法。
    """
    
    def __init__(
        self,
        log_dir: str,
        algorithm: CompressionAlgorithm = CompressionAlgorithm.GZIP,
        min_age_days: float = 1,  # 至少多少天前的文件才压缩
        min_size_mb: float = 10,  # 至少多大的文件才压缩
        remove_original: bool = True,
    ):
        """
        初始化压缩器
        
        Args:
            log_dir: 日志目录
            algorithm: 压缩算法
            min_age_days: 最小文件年龄 (天)
            min_size_mb: 最小文件大小 (MB)
            remove_original: 压缩后是否删除原文件
        """
        self.log_dir = Path(log_dir)
        self.algorithm = algorithm
        self.min_age_seconds = min_age_days * 86400
        self.min_size_bytes = int(min_size_mb * 1024 * 1024)
        self.remove_original = remove_original
        self._logger = logging.getLogger(__name__)
    
    def compress(self, file_path: Path) -> Optional[Path]:
        """
        压缩单个文件
        
        Returns:
            压缩后的文件路径
        """
        if not file_path.exists():
            return None
        
        # 检查是否应该压缩
        if not self._should_compress(file_path):
            return None
        
        # 生成压缩文件路径
        if self.algorithm == CompressionAlgorithm.GZIP:
            compressed_path = file_path.with_suffix(file_path.suffix + '.gz')
            compress_func = self._gzip_compress
        elif self.algorithm == CompressionAlgorithm.BZ2:
            compressed_path = file_path.with_suffix(file_path.suffix + '.bz2')
            compress_func = self._bz2_compress
        else:  # LZMA
            compressed_path = file_path.with_suffix(file_path.suffix + '.xz')
            compress_func = self._lzma_compress
        
        try:
            compress_func(file_path, compressed_path)
            
            if self.remove_original:
                file_path.unlink()
            
            original_size = file_path.stat().st_size
            compressed_size = compressed_path.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            self._logger.info(
                f"Compressed: {file_path.name} -> {compressed_path.name} "
                f"({original_size/1024/1024:.2f}MB -> {compressed_size/1024/1024:.2f}MB, "
                f"压缩率：{ratio:.1f}%)"
            )
            
            return compressed_path
            
        except Exception as e:
            self._logger.error(f"Compression failed for {file_path}: {e}")
            # 清理失败的压缩文件
            if compressed_path.exists():
                compressed_path.unlink()
            return None
    
    def _should_compress(self, file_path: Path) -> bool:
        """判断是否应该压缩"""
        # 已经是压缩文件
        if file_path.suffix in ['.gz', '.bz2', '.xz']:
            return False
        
        # 检查文件大小
        if file_path.stat().st_size < self.min_size_bytes:
            return False
        
        # 检查文件年龄
        age = time.time() - file_path.stat().st_mtime
        if age < self.min_age_seconds:
            return False
        
        return True
    
    def _gzip_compress(self, src: Path, dst: Path):
        """GZIP 压缩"""
        with open(src, 'rb') as f_in:
            with gzip.open(dst, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _bz2_compress(self, src: Path, dst: Path):
        """BZ2 压缩"""
        import bz2
        with open(src, 'rb') as f_in:
            with bz2.open(dst, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def _lzma_compress(self, src: Path, dst: Path):
        """LZMA 压缩"""
        import lzma
        with open(src, 'rb') as f_in:
            with lzma.open(dst, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
    
    def compress_all(self, pattern: str = "*.log") -> List[Path]:
        """压缩所有匹配的文件"""
        compressed = []
        
        for file_path in self.log_dir.glob(pattern):
            result = self.compress(file_path)
            if result:
                compressed.append(result)
        
        return compressed
    
    def compress_old_logs(self, min_age_days: float = 7) -> List[Path]:
        """压缩指定年龄以上的日志文件"""
        compressed = []
        current_time = time.time()
        min_age_seconds = min_age_days * 86400
        
        for file_path in self.log_dir.glob("*.log"):
            if file_path.suffix in ['.gz', '.bz2', '.xz']:
                continue
            
            age = current_time - file_path.stat().st_mtime
            if age >= min_age_seconds:
                result = self.compress(file_path)
                if result:
                    compressed.append(result)
        
        return compressed


# ============================================================================
# 日志清理器
# ============================================================================

class LogCleaner:
    """
    日志清理器
    
    清理过期的日志文件。
    """
    
    def __init__(
        self,
        log_dir: str,
        retention_days: int = 30,
        file_pattern: str = "*.log*",
        dry_run: bool = False,
    ):
        """
        初始化清理器
        
        Args:
            log_dir: 日志目录
            retention_days: 保留天数
            file_pattern: 文件匹配模式
            dry_run: 仅模拟，不实际删除
        """
        self.log_dir = Path(log_dir)
        self.retention_days = retention_days
        self.file_pattern = file_pattern
        self.dry_run = dry_run
        self._logger = logging.getLogger(__name__)
    
    def cleanup(self) -> List[Path]:
        """
        清理过期日志文件
        
        Returns:
            被删除的文件列表
        """
        deleted = []
        cutoff_time = time.time() - (self.retention_days * 86400)
        
        for file_path in self.log_dir.glob(self.file_pattern):
            try:
                stat = file_path.stat()
                if stat.st_mtime < cutoff_time:
                    if self.dry_run:
                        self._logger.info(f"[DRY RUN] Would delete: {file_path}")
                    else:
                        file_path.unlink()
                        self._logger.info(f"Deleted: {file_path} (age: {stat.st_mtime - cutoff_time + self.retention_days * 86400:.0f} days)")
                    deleted.append(file_path)
            except Exception as e:
                self._logger.error(f"Error processing {file_path}: {e}")
        
        return deleted
    
    def cleanup_empty_dirs(self) -> List[Path]:
        """清理空目录"""
        deleted = []
        
        for dir_path in sorted(self.log_dir.rglob('*'), reverse=True):
            if dir_path.is_dir():
                try:
                    if not any(dir_path.iterdir()):
                        if self.dry_run:
                            self._logger.info(f"[DRY RUN] Would delete empty dir: {dir_path}")
                        else:
                            dir_path.rmdir()
                            self._logger.info(f"Deleted empty dir: {dir_path}")
                        deleted.append(dir_path)
                except Exception as e:
                    self._logger.error(f"Error processing dir {dir_path}: {e}")
        
        return deleted
    
    def get_cleanup_preview(self) -> Dict[str, Any]:
        """获取清理预览信息"""
        cutoff_time = time.time() - (self.retention_days * 86400)
        
        preview = {
            'total_files': 0,
            'files_to_delete': 0,
            'size_to_free_bytes': 0,
            'files': [],
        }
        
        for file_path in self.log_dir.glob(self.file_pattern):
            preview['total_files'] += 1
            stat = file_path.stat()
            
            if stat.st_mtime < cutoff_time:
                preview['files_to_delete'] += 1
                preview['size_to_free_bytes'] += stat.st_size
                preview['files'].append({
                    'path': str(file_path),
                    'size_mb': stat.st_size / 1024 / 1024,
                    'age_days': (time.time() - stat.st_mtime) / 86400,
                })
        
        preview['size_to_free_mb'] = preview['size_to_free_bytes'] / 1024 / 1024
        preview['size_to_free_gb'] = preview['size_to_free_bytes'] / 1024 / 1024 / 1024
        
        return preview


# ============================================================================
# 日志生命周期管理器
# ============================================================================

class LogLifecycleManager:
    """
    日志生命周期管理器
    
    统一管理日志的轮转、压缩、清理。
    """
    
    def __init__(
        self,
        log_dir: str,
        retention_days: int = 30,
        max_size_mb: float = 100,
        max_backup_count: int = 10,
        enable_compression: bool = True,
        compression_min_age_days: float = 1,
        compression_algorithm: str = "gzip",
    ):
        """
        初始化生命周期管理器
        
        Args:
            log_dir: 日志目录
            retention_days: 保留天数
            max_size_mb: 单个文件最大大小 (MB)
            max_backup_count: 最大备份数量
            enable_compression: 是否启用压缩
            compression_min_age_days: 压缩最小年龄 (天)
            compression_algorithm: 压缩算法
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建组件
        self.rotator = LogRotator(
            log_dir=str(log_dir),
            max_size_mb=max_size_mb,
            max_backup_count=max_backup_count,
        )
        
        self.compressor = LogCompressor(
            log_dir=str(log_dir),
            algorithm=CompressionAlgorithm(compression_algorithm),
            min_age_days=compression_min_age_days,
        ) if enable_compression else None
        
        self.cleaner = LogCleaner(
            log_dir=str(log_dir),
            retention_days=retention_days,
        )
        
        self._logger = logging.getLogger(__name__)
    
    def run_full_lifecycle(self) -> Dict[str, Any]:
        """
        执行完整的生命周期管理
        
        Returns:
            执行统计信息
        """
        stats = {
            'timestamp': datetime.now().isoformat(),
            'rotated': [],
            'compressed': [],
            'deleted': [],
            'stats_before': self.get_stats().to_dict(),
        }
        
        self._logger.info("Starting full lifecycle management...")
        
        # 1. 轮转
        rotated = self.rotator.rotate_all()
        stats['rotated'] = [str(f) for f in rotated]
        self._logger.info(f"Rotated {len(rotated)} files")
        
        # 2. 压缩
        if self.compressor:
            compressed = self.compressor.compress_old_logs(min_age_days=1)
            stats['compressed'] = [str(f) for f in compressed]
            self._logger.info(f"Compressed {len(compressed)} files")
        
        # 3. 清理
        deleted = self.cleaner.cleanup()
        stats['deleted'] = [str(f) for f in deleted]
        self._logger.info(f"Deleted {len(deleted)} files")
        
        # 4. 清理空目录
        empty_dirs = self.cleaner.cleanup_empty_dirs()
        stats['empty_dirs_deleted'] = len(empty_dirs)
        
        # 5. 最终统计
        stats['stats_after'] = self.get_stats().to_dict()
        
        self._logger.info(f"Lifecycle management completed. Stats: {stats['stats_after']}")
        
        return stats
    
    def get_stats(self) -> LifecycleStats:
        """获取日志目录统计信息"""
        stats = LifecycleStats()
        
        files = []
        for file_path in self.log_dir.glob("**/*"):
            if file_path.is_file():
                info = LogFileInfo.from_path(file_path)
                files.append(info)
                stats.total_files += 1
                stats.total_size_bytes += info.size
                
                if info.is_compressed:
                    stats.compressed_files += 1
                else:
                    stats.uncompressed_files += 1
        
        if files:
            ages = [f.age_days for f in files]
            stats.oldest_file_age_days = max(ages)
            stats.newest_file_age_days = min(ages)
        
        return stats
    
    def get_preview(self) -> Dict[str, Any]:
        """获取生命周期管理预览"""
        return {
            'log_dir': str(self.log_dir),
            'retention_days': self.retention_days if hasattr(self, 'retention_days') else 30,
            'stats': self.get_stats().to_dict(),
            'cleanup_preview': self.cleaner.get_cleanup_preview(),
        }


# ============================================================================
# 日志调度器
# ============================================================================

class LogScheduler:
    """
    日志生命周期调度器
    
    定期执行日志生命周期管理任务。
    """
    
    def __init__(
        self,
        manager: LogLifecycleManager,
        interval_hours: float = 24,
        run_at: str = None,  # HH:MM 格式
    ):
        """
        初始化调度器
        
        Args:
            manager: 生命周期管理器
            interval_hours: 执行间隔 (小时)
            run_at: 固定执行时间 (HH:MM)
        """
        self.manager = manager
        self.interval_seconds = int(interval_hours * 3600)
        self.run_at = run_at
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._logger = logging.getLogger(__name__)
    
    def start(self, blocking: bool = False):
        """启动调度器"""
        if self._running:
            self._logger.warning("Scheduler already running")
            return
        
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        self._logger.info(f"Scheduler started (interval={self.interval_seconds}s)")
        
        if blocking:
            try:
                self._thread.join()
            except KeyboardInterrupt:
                self.stop()
    
    def stop(self):
        """停止调度器"""
        self._running = False
        self._stop_event.set()
        
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        
        self._logger.info("Scheduler stopped")
    
    def _run_loop(self):
        """运行循环"""
        while self._running and not self._stop_event.is_set():
            try:
                # 计算下次执行时间
                if self.run_at:
                    next_run = self._calculate_next_run_time()
                    wait_seconds = (next_run - datetime.now()).total_seconds()
                else:
                    wait_seconds = self.interval_seconds
                
                # 等待
                if wait_seconds > 0 and not self._stop_event.wait(wait_seconds):
                    # 执行任务
                    self._execute_task()
                    
            except Exception as e:
                self._logger.error(f"Scheduler error: {e}")
    
    def _calculate_next_run_time(self) -> datetime:
        """计算下次执行时间"""
        hour, minute = map(int, self.run_at.split(':'))
        now = datetime.now()
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run
    
    def _execute_task(self):
        """执行生命周期管理任务"""
        self._logger.info("Executing lifecycle management task...")
        
        try:
            stats = self.manager.run_full_lifecycle()
            self._logger.info(f"Task completed: {stats['stats_after']}")
        except Exception as e:
            self._logger.error(f"Task execution failed: {e}")


# ============================================================================
# CLI 工具
# ============================================================================

def main():
    """CLI 入口点"""
    parser = argparse.ArgumentParser(description='日志生命周期管理工具')
    parser.add_argument('command', choices=['rotate', 'compress', 'cleanup', 'stats', 'run', 'schedule'],
                       help='命令')
    parser.add_argument('--log-dir', '-d', default='logs', help='日志目录')
    parser.add_argument('--retention-days', '-r', type=int, default=30, help='保留天数')
    parser.add_argument('--max-size-mb', '-s', type=float, default=100, help='单个文件最大大小 (MB)')
    parser.add_argument('--dry-run', '-n', action='store_true', help='仅模拟')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 创建管理器
    manager = LogLifecycleManager(
        log_dir=args.log_dir,
        retention_days=args.retention_days,
        max_size_mb=args.max_size_mb,
    )
    
    if args.command == 'stats':
        stats = manager.get_stats()
        print(json.dumps(stats.to_dict(), indent=2))
    
    elif args.command == 'rotate':
        rotated = manager.rotator.rotate_all()
        print(f"Rotated {len(rotated)} files")
        for f in rotated:
            print(f"  {f}")
    
    elif args.command == 'compress':
        compressed = manager.compressor.compress_all() if manager.compressor else []
        print(f"Compressed {len(compressed)} files")
        for f in compressed:
            print(f"  {f}")
    
    elif args.command == 'cleanup':
        cleaner = LogCleaner(
            log_dir=args.log_dir,
            retention_days=args.retention_days,
            dry_run=args.dry_run,
        )
        
        if args.dry_run:
            preview = cleaner.get_cleanup_preview()
            print(f"Would delete {preview['files_to_delete']} files")
            print(f"Would free {preview['size_to_free_mb']:.2f} MB")
        else:
            deleted = cleaner.cleanup()
            print(f"Deleted {len(deleted)} files")
    
    elif args.command == 'run':
        stats = manager.run_full_lifecycle()
        print(json.dumps(stats, indent=2, default=str))
    
    elif args.command == 'schedule':
        scheduler = LogScheduler(manager, interval_hours=24)
        
        def signal_handler(sig, frame):
            scheduler.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        print(f"Scheduler started. Press Ctrl+C to stop.")
        scheduler.start(blocking=True)


if __name__ == '__main__':
    main()
