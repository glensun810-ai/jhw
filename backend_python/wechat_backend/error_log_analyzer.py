#!/usr/bin/env python3
"""
错误日志分析工具

功能:
- 分析错误日志文件
- 统计错误频率和分布
- 识别常见错误模式
- 生成错误分析报告
- 支持时间范围过滤
- 支持错误分类过滤

使用示例:
    # 命令行使用
    python -m wechat_backend.error_log_analyzer --log-dir logs --days 7 --output report.json
    
    # Python 代码使用
    from wechat_backend.error_log_analyzer import ErrorLogAnalyzer
    
    analyzer = ErrorLogAnalyzer('logs')
    report = analyzer.analyze(days=7)
    print(report.summary())
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
import argparse


@dataclass
class ErrorEntry:
    """错误条目"""
    timestamp: datetime
    level: str
    logger: str
    message: str
    category: str
    exception_type: Optional[str] = None
    exception_message: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    function: Optional[str] = None
    trace_id: Optional[str] = None
    raw_data: Optional[Dict] = None


@dataclass
class ErrorStats:
    """错误统计"""
    total_errors: int = 0
    errors_by_level: Dict[str, int] = defaultdict(int)
    errors_by_category: Dict[str, int] = defaultdict(int)
    errors_by_exception_type: Dict[str, int] = defaultdict(int)
    errors_by_file: Dict[str, int] = defaultdict(int)
    errors_by_hour: Dict[int, int] = defaultdict(int)
    errors_by_day: Dict[str, int] = defaultdict(int)
    top_messages: Counter = None
    unique_errors: int = 0
    time_range: Tuple[datetime, datetime] = None
    
    def __post_init__(self):
        if self.top_messages is None:
            self.top_messages = Counter()


@dataclass
class ErrorReport:
    """错误分析报告"""
    generated_at: datetime
    log_dir: str
    time_range: Dict[str, str]
    total_errors: int
    unique_errors: int
    errors_by_level: Dict[str, int]
    errors_by_category: Dict[str, int]
    top_exception_types: List[Tuple[str, int]]
    top_error_messages: List[Tuple[str, int]]
    errors_by_hour: Dict[int, int]
    errors_by_day: Dict[str, int]
    top_error_files: List[Tuple[str, int]]
    error_trends: Dict[str, Any]
    recommendations: List[str]
    
    def summary(self) -> str:
        """生成摘要文本"""
        lines = [
            "=" * 60,
            "错误日志分析报告",
            "=" * 60,
            f"生成时间：{self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"日志目录：{self.log_dir}",
            f"时间范围：{self.time_range.get('start', 'N/A')} 至 {self.time_range.get('end', 'N/A')}",
            "",
            "错误统计:",
            f"  总错误数：{self.total_errors}",
            f"  唯一错误数：{self.unique_errors}",
            "",
            "按级别分布:",
        ]
        
        for level, count in sorted(self.errors_by_level.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / self.total_errors * 100) if self.total_errors > 0 else 0
            lines.append(f"  {level}: {count} ({percentage:.1f}%)")
        
        lines.extend([
            "",
            "按分类分布:",
        ])
        for category, count in sorted(self.errors_by_category.items(), key=lambda x: x[1], reverse=True)[:10]:
            percentage = (count / self.total_errors * 100) if self.total_errors > 0 else 0
            lines.append(f"  {category}: {count} ({percentage:.1f}%)")
        
        lines.extend([
            "",
            "Top 异常类型:",
        ])
        for exc_type, count in self.top_exception_types[:10]:
            lines.append(f"  {exc_type}: {count}")
        
        lines.extend([
            "",
            "Top 错误消息:",
        ])
        for msg, count in self.top_error_messages[:10]:
            truncated_msg = msg[:80] + "..." if len(msg) > 80 else msg
            lines.append(f"  [{count}x] {truncated_msg}")
        
        if self.recommendations:
            lines.extend([
                "",
                "建议:",
            ])
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"  {i}. {rec}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


class ErrorLogAnalyzer:
    """错误日志分析器"""
    
    def __init__(self, log_dir: str):
        """
        Args:
            log_dir: 日志目录路径
        """
        self.log_dir = Path(log_dir)
        self.errors: List[ErrorEntry] = []
        self.stats = ErrorStats()
        
    def load_logs(
        self,
        days: int = 7,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        categories: Optional[List[str]] = None,
    ) -> int:
        """
        加载日志文件
        
        Args:
            days: 分析最近多少天的日志
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
            categories: 要分析的错误分类列表
            
        Returns:
            加载的错误数量
        """
        self.errors = []
        
        # 确定时间范围
        now = datetime.now()
        if start_date is None:
            start_date = now - timedelta(days=days)
        if end_date is None:
            end_date = now
        
        # 查找日志文件
        log_files = self._find_log_files(categories)
        
        for log_file in log_files:
            try:
                errors = self._parse_log_file(
                    log_file, 
                    start_date, 
                    end_date
                )
                self.errors.extend(errors)
            except Exception as e:
                print(f"Warning: Failed to parse {log_file}: {e}", file=sys.stderr)
        
        # 按时间排序
        self.errors.sort(key=lambda x: x.timestamp)
        
        # 计算统计信息
        self._calculate_stats()
        
        return len(self.errors)
    
    def _find_log_files(
        self, 
        categories: Optional[List[str]] = None
    ) -> List[Path]:
        """查找所有错误日志文件"""
        patterns = ['errors.log*', 'errors_*.log*']
        
        if categories:
            patterns = [f'errors_{cat}.log*' for cat in categories]
        
        files = []
        for pattern in patterns:
            files.extend(self.log_dir.glob(pattern))
        
        return sorted(files, reverse=True)
    
    def _parse_log_file(
        self,
        file_path: Path,
        start_date: datetime,
        end_date: datetime,
    ) -> List[ErrorEntry]:
        """解析日志文件"""
        errors = []
        
        # 处理压缩文件
        if file_path.suffix == '.gz':
            import gzip
            open_func = lambda p: gzip.open(p, 'rt', encoding='utf-8')
        else:
            open_func = lambda p: open(p, 'r', encoding='utf-8')
        
        try:
            with open_func(file_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    error = self._parse_log_line(line)
                    if error and start_date <= error.timestamp <= end_date:
                        errors.append(error)
        except Exception as e:
            print(f"Error reading {file_path}: {e}", file=sys.stderr)
        
        return errors
    
    def _parse_log_line(self, line: str) -> Optional[ErrorEntry]:
        """解析日志行"""
        try:
            # 尝试解析 JSON 格式
            data = json.loads(line)
            
            # 解析时间戳
            timestamp_str = data.get('timestamp', '')
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                return None
            
            # 提取错误信息
            message = data.get('message', '')
            level = data.get('level', 'ERROR')
            logger_name = data.get('logger', '')
            
            # 确定分类
            category = self._extract_category(logger_name, message, data)
            
            # 提取异常信息
            exception_info = data.get('exception', {})
            exception_type = exception_info.get('type') if exception_info else None
            exception_message = exception_info.get('message') if exception_info else None
            
            # 提取位置信息
            location = data.get('location', {})
            file_name = location.get('file') if location else None
            line_no = location.get('line') if location else None
            function = location.get('function') if location else None
            
            # 提取追踪 ID
            trace = data.get('trace', {})
            trace_id = trace.get('trace_id') if trace else None
            
            return ErrorEntry(
                timestamp=timestamp,
                level=level,
                logger=logger_name,
                message=message,
                category=category,
                exception_type=exception_type,
                exception_message=exception_message,
                file=file_name,
                line=line_no,
                function=function,
                trace_id=trace_id,
                raw_data=data,
            )
        except json.JSONDecodeError:
            # 非 JSON 格式，尝试正则解析
            return self._parse_text_log_line(line)
        except Exception:
            return None
    
    def _parse_text_log_line(self, line: str) -> Optional[ErrorEntry]:
        """解析文本格式的日志行"""
        # 标准格式：2026-03-05 10:30:00 - logger.name - ERROR - message
        pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - ([\w.]+) - (\w+) - (.+)'
        match = re.match(pattern, line)
        
        if not match:
            return None
        
        timestamp_str, logger, level, message = match.groups()
        
        try:
            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            return None
        
        return ErrorEntry(
            timestamp=timestamp,
            level=level,
            logger=logger,
            message=message,
            category=self._extract_category(logger, message),
            raw_data={'raw_line': line},
        )
    
    def _extract_category(
        self, 
        logger_name: str, 
        message: str,
        data: Optional[Dict] = None
    ) -> str:
        """提取错误分类"""
        # 从日志器名称提取
        if 'api' in logger_name.lower():
            return 'api'
        if 'database' in logger_name.lower() or 'db' in logger_name.lower():
            return 'database'
        if 'ai' in logger_name.lower():
            return 'ai'
        if 'security' in logger_name.lower():
            return 'security'
        if 'network' in logger_name.lower():
            return 'network'
        
        # 从消息内容提取
        message_lower = message.lower()
        if 'sql' in message_lower or 'database' in message_lower:
            return 'database'
        if 'api' in message_lower or 'request' in message_lower:
            return 'api'
        if 'ai' in message_lower or 'model' in message_lower or 'llm' in message_lower:
            return 'ai'
        if 'auth' in message_lower or 'permission' in message_lower or 'token' in message_lower:
            return 'security'
        if 'network' in message_lower or 'connection' in message_lower or 'timeout' in message_lower:
            return 'network'
        
        return 'system'
    
    def _calculate_stats(self):
        """计算统计信息"""
        self.stats = ErrorStats()
        
        if not self.errors:
            return
        
        # 时间范围
        self.stats.time_range = (
            self.errors[0].timestamp,
            self.errors[-1].timestamp,
        )
        
        # 统计
        message_counter = Counter()
        
        for error in self.errors:
            self.stats.total_errors += 1
            self.stats.errors_by_level[error.level] += 1
            self.stats.errors_by_category[error.category] += 1
            
            if error.exception_type:
                self.stats.errors_by_exception_type[error.exception_type] += 1
            
            if error.file:
                self.stats.errors_by_file[error.file] += 1
            
            self.stats.errors_by_hour[error.timestamp.hour] += 1
            
            day_key = error.timestamp.strftime('%Y-%m-%d')
            self.stats.errors_by_day[day_key] += 1
            
            # 标准化消息用于计数
            normalized_msg = self._normalize_message(error.message)
            message_counter[normalized_msg] += 1
        
        self.stats.top_messages = message_counter
        self.stats.unique_errors = len(message_counter)
    
    def _normalize_message(self, message: str) -> str:
        """标准化错误消息（用于聚合）"""
        # 替换具体值为占位符
        normalized = re.sub(r'\b\d+\b', '<NUM>', message)
        normalized = re.sub(r"'[^']*'", "'<STR>'", normalized)
        normalized = re.sub(r'"[^"]*"', '"<STR>"', normalized)
        normalized = re.sub(r'\b[0-9a-f]{8,}\b', '<ID>', normalized, flags=re.IGNORECASE)
        return normalized[:200]  # 截断长消息
    
    def analyze(self) -> ErrorReport:
        """生成分析报告"""
        now = datetime.now()
        
        # 生成建议
        recommendations = self._generate_recommendations()
        
        # 构建报告
        report = ErrorReport(
            generated_at=now,
            log_dir=str(self.log_dir),
            time_range={
                'start': self.stats.time_range[0].isoformat() if self.stats.time_range else None,
                'end': self.stats.time_range[1].isoformat() if self.stats.time_range else None,
            },
            total_errors=self.stats.total_errors,
            unique_errors=self.stats.unique_errors,
            errors_by_level=dict(self.stats.errors_by_level),
            errors_by_category=dict(self.stats.errors_by_category),
            top_exception_types=list(self.stats.errors_by_exception_type.items())[:10],
            top_error_messages=list(self.stats.top_messages.items())[:10],
            errors_by_hour=dict(self.stats.errors_by_hour),
            errors_by_day=dict(self.stats.errors_by_day),
            top_error_files=list(self.stats.errors_by_file.items())[:10],
            error_trends=self._calculate_trends(),
            recommendations=recommendations,
        )
        
        return report
    
    def _calculate_trends(self) -> Dict[str, Any]:
        """计算错误趋势"""
        if not self.stats.errors_by_day:
            return {}
        
        days = sorted(self.stats.errors_by_day.keys())
        counts = [self.stats.errors_by_day[d] for d in days]
        
        if len(counts) < 2:
            return {'daily_counts': dict(self.stats.errors_by_day)}
        
        # 计算平均值和趋势
        avg = sum(counts) / len(counts)
        
        # 简单线性趋势
        if len(counts) >= 3:
            first_half_avg = sum(counts[:len(counts)//2]) / (len(counts)//2)
            second_half_avg = sum(counts[len(counts)//2:]) / (len(counts) - len(counts)//2)
            trend = 'increasing' if second_half_avg > first_half_avg * 1.1 else (
                'decreasing' if second_half_avg < first_half_avg * 0.9 else 'stable'
            )
        else:
            trend = 'unknown'
        
        return {
            'daily_counts': dict(self.stats.errors_by_day),
            'average_per_day': avg,
            'trend': trend,
            'peak_day': max(self.stats.errors_by_day.items(), key=lambda x: x[1])[0] if self.stats.errors_by_day else None,
            'peak_count': max(self.stats.errors_by_day.values()) if self.stats.errors_by_day else 0,
        }
    
    def _generate_recommendations(self) -> List[str]:
        """生成建议"""
        recommendations = []
        
        if self.stats.total_errors == 0:
            return ["没有发现错误，系统运行正常"]
        
        # 检查错误频率
        if self.stats.time_range:
            duration_hours = (self.stats.time_range[1] - self.stats.time_range[0]).total_seconds() / 3600
            if duration_hours > 0:
                errors_per_hour = self.stats.total_errors / duration_hours
                if errors_per_hour > 100:
                    recommendations.append(
                        f"错误频率过高 ({errors_per_hour:.1f}/小时)，建议立即检查系统状态"
                    )
        
        # 检查特定错误类型
        if 'ConnectionError' in self.stats.errors_by_exception_type:
            recommendations.append("检测到连接错误，检查网络和数据库连接配置")
        
        if 'TimeoutError' in self.stats.errors_by_exception_type:
            recommendations.append("检测到超时错误，考虑增加超时阈值或优化性能")
        
        # 检查错误分布
        if self.stats.errors_by_category.get('database', 0) > self.stats.total_errors * 0.3:
            recommendations.append("数据库错误占比过高，建议检查数据库性能和查询优化")
        
        if self.stats.errors_by_category.get('ai', 0) > self.stats.total_errors * 0.3:
            recommendations.append("AI 调用错误占比过高，建议检查 API 配额和错误处理")
        
        # 检查时间分布
        peak_hour = max(self.stats.errors_by_hour.items(), key=lambda x: x[1])[0] if self.stats.errors_by_hour else None
        if peak_hour is not None:
            recommendations.append(f"错误高发时段为 {peak_hour:02d}:00，建议关注该时段的系统负载")
        
        # 检查趋势
        if self.stats.unique_errors < 10 and self.stats.total_errors > 100:
            recommendations.append("少数错误重复出现，建议优先修复这些高频错误")
        
        if not recommendations:
            recommendations.append("错误分布正常，持续监控即可")
        
        return recommendations
    
    def export_report(
        self,
        output_path: str,
        format: str = 'json',
    ) -> str:
        """
        导出报告
        
        Args:
            output_path: 输出文件路径
            format: 输出格式 (json, text)
            
        Returns:
            输出文件路径
        """
        report = self.analyze()
        output_path = Path(output_path)
        
        if format == 'json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, ensure_ascii=False, indent=2, default=str)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report.summary())
        
        return str(output_path)


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='错误日志分析工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析最近 7 天的日志
  python -m wechat_backend.error_log_analyzer --log-dir logs
  
  # 分析指定日期范围
  python -m wechat_backend.error_log_analyzer --log-dir logs --start 2026-03-01 --end 2026-03-05
  
  # 只分析特定分类
  python -m wechat_backend.error_log_analyzer --log-dir logs --categories api,database
  
  # 导出 JSON 报告
  python -m wechat_backend.error_log_analyzer --log-dir logs --output report.json --format json
        """
    )
    
    parser.add_argument(
        '--log-dir',
        type=str,
        default='logs',
        help='日志目录路径 (默认：logs)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='分析最近多少天的日志 (默认：7)'
    )
    parser.add_argument(
        '--start',
        type=str,
        help='开始日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end',
        type=str,
        help='结束日期 (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--categories',
        type=str,
        help='错误分类列表，逗号分隔 (如：api,database,ai)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='输出报告文件路径'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'text'],
        default='text',
        help='输出格式 (默认：text)'
    )
    
    args = parser.parse_args()
    
    # 解析日期
    start_date = None
    end_date = None
    
    if args.start:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    if args.end:
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    
    # 解析分类
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(',')]
    
    # 创建分析器
    analyzer = ErrorLogAnalyzer(args.log_dir)
    
    # 加载日志
    print(f"Loading logs from {args.log_dir}...")
    count = analyzer.load_logs(
        days=args.days,
        start_date=start_date,
        end_date=end_date,
        categories=categories,
    )
    print(f"Loaded {count} errors")
    
    # 生成报告
    report = analyzer.analyze()
    
    # 输出
    if args.output:
        analyzer.export_report(args.output, format=args.format)
        print(f"Report exported to {args.output}")
    else:
        print(report.summary())


if __name__ == '__main__':
    main()
