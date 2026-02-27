#!/usr/bin/env python3
"""
异步导出服务
处理大数据量 PDF 生成的异步任务

版本：v2.0
日期：2026-02-21
"""

import threading
import queue
import time
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional
from wechat_backend.logging_config import api_logger
from wechat_backend.services.report_data_service import get_report_data_service


class AsyncExportService:
    """
    异步导出服务
    处理大数据量 PDF 生成的异步任务
    """
    
    def __init__(self, max_workers: int = 4):
        self.task_queue = queue.Queue()
        self.task_status: Dict[str, Dict[str, Any]] = {}
        self.max_workers = max_workers
        self.workers = []
        self.logger = api_logger
        self._start_workers()
        self.logger.info(f"AsyncExportService started with {max_workers} workers")
    
    def _start_workers(self):
        """启动工作线程"""
        for i in range(self.max_workers):
            worker = threading.Thread(target=self._worker_loop, daemon=True, name=f"ExportWorker-{i}")
            worker.start()
            self.workers.append(worker)
    
    def _worker_loop(self):
        """工作线程循环"""
        thread_name = threading.current_thread().name
        self.logger.info(f"{thread_name} started")
        
        while True:
            try:
                task = self.task_queue.get()
                if task is None:
                    break
                
                self._process_task(task)
                self.task_queue.task_done()
            except Exception as e:
                self.logger.error(f"{thread_name} error: {e}", exc_info=True)
    
    def _process_task(self, task: Dict[str, Any]):
        """处理单个任务"""
        task_id = task['task_id']
        thread_name = threading.current_thread().name
        
        self.logger.info(f"{thread_name} processing task: {task_id}")
        
        try:
            # 更新状态为处理中
            self._update_status(task_id, {
                'status': 'processing',
                'progress': 10,
                'message': '正在初始化...',
                'started_at': datetime.now().isoformat()
            })
            
            # 阶段 1: 获取报告数据 (20%)
            self._update_status(task_id, {
                'progress': 20,
                'message': '正在获取报告数据...'
            })
            
            report_service = get_report_data_service()
            report_data = report_service.generate_full_report(task['execution_id'])
            
            # 阶段 2: 生成 PDF (50%)
            self._update_status(task_id, {
                'progress': 50,
                'message': '正在生成 PDF...'
            })
            
            from wechat_backend.services.pdf_export_service import PDFExportService
            pdf_service = PDFExportService()
            pdf_data = pdf_service.generate_enhanced_report(
                report_data,
                task.get('level', 'full'),
                task.get('sections', 'all')
            )
            
            # 阶段 3: 保存文件 (80%)
            self._update_status(task_id, {
                'progress': 80,
                'message': '正在保存文件...'
            })
            
            file_path = self._save_pdf(pdf_data, task_id, task['execution_id'])
            
            # 阶段 4: 完成 (100%)
            self._update_status(task_id, {
                'progress': 100,
                'message': '完成',
                'status': 'completed',
                'file_path': file_path,
                'file_size': len(pdf_data),
                'completed_at': datetime.now().isoformat()
            })
            
            self.logger.info(f"Task {task_id} completed successfully, file: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            self._update_status(task_id, {
                'status': 'failed',
                'error': str(e),
                'error_type': type(e).__name__,
                'failed_at': datetime.now().isoformat()
            })
    
    def _update_status(self, task_id: str, updates: Dict[str, Any]):
        """更新任务状态"""
        if task_id in self.task_status:
            self.task_status[task_id].update(updates)
        else:
            self.task_status[task_id] = updates
    
    def _save_pdf(self, pdf_data: bytes, task_id: str, execution_id: str) -> str:
        """保存 PDF 文件"""
        output_dir = 'exports/pdf'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{execution_id}_{timestamp}.pdf"
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(pdf_data)
        
        self.logger.info(f"PDF saved to: {file_path}, size: {len(pdf_data)} bytes")
        return file_path
    
    def submit_task(self, execution_id: str, level: str = 'full', sections: str = 'all') -> str:
        """
        提交异步任务
        
        Args:
            execution_id: 执行 ID
            level: 报告级别 (basic, detailed, full)
            sections: 需要的章节 (comma-separated 或 'all')
        
        Returns:
            task_id: 任务 ID
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        task = {
            'task_id': task_id,
            'execution_id': execution_id,
            'level': level,
            'sections': sections,
            'submitted_at': datetime.now().isoformat()
        }
        
        self.task_queue.put(task)
        
        # 初始化任务状态
        self.task_status[task_id] = {
            'status': 'queued',
            'progress': 0,
            'message': '任务已提交，等待处理...',
            'submitted_at': task['submitted_at'],
            'execution_id': execution_id,
            'level': level,
            'sections': sections
        }
        
        self.logger.info(f"Task {task_id} submitted for execution_id={execution_id}")
        return task_id
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return self.task_status.get(task_id, {
            'status': 'not_found',
            'error': 'Task not found'
        })
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        queued = sum(1 for t in self.task_status.values() if t.get('status') == 'queued')
        processing = sum(1 for t in self.task_status.values() if t.get('status') == 'processing')
        completed = sum(1 for t in self.task_status.values() if t.get('status') == 'completed')
        failed = sum(1 for t in self.task_status.values() if t.get('status') == 'failed')
        
        return {
            'queue_size': self.task_queue.qsize(),
            'active_workers': len([w for w in self.workers if w.is_alive()]),
            'total_tasks': len(self.task_status),
            'queued': queued,
            'processing': processing,
            'completed': completed,
            'failed': failed
        }
    
    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """清理旧任务状态"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        tasks_to_remove = []
        for task_id, status in self.task_status.items():
            completed_at = status.get('completed_at') or status.get('failed_at')
            if completed_at:
                try:
                    task_time = datetime.fromisoformat(completed_at).timestamp()
                    if task_time < cutoff_time:
                        tasks_to_remove.append(task_id)
                except Exception as e:
                    self.logger.error(f"Error parsing task completion time for {task_id}: {e}", exc_info=True)
                    # 时间戳解析失败，跳过该任务
        
        for task_id in tasks_to_remove:
            del self.task_status[task_id]
        
        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
        
        return len(tasks_to_remove)


# 全局实例
_async_export_service: Optional[AsyncExportService] = None


def get_async_export_service() -> AsyncExportService:
    """获取异步导出服务实例"""
    global _async_export_service
    if _async_export_service is None:
        _async_export_service = AsyncExportService(max_workers=4)
    return _async_export_service


def queue_pdf_generation(execution_id: str, level: str = 'full', sections: str = 'all') -> str:
    """
    队列化 PDF 生成任务
    
    Args:
        execution_id: 执行 ID
        level: 报告级别
        sections: 需要的章节
    
    Returns:
        task_id: 任务 ID
    """
    service = get_async_export_service()
    return service.submit_task(execution_id, level, sections)


def get_export_task_status(task_id: str) -> Dict[str, Any]:
    """
    获取导出任务状态
    
    Args:
        task_id: 任务 ID
    
    Returns:
        任务状态字典
    """
    service = get_async_export_service()
    return service.get_task_status(task_id)


def start_cleanup_thread(interval_hours: int = 1, max_age_hours: int = 24):
    """启动定期清理线程"""
    def cleanup_loop():
        service = get_async_export_service()
        while True:
            time.sleep(interval_hours * 3600)
            try:
                cleaned = service.cleanup_old_tasks(max_age_hours)
                api_logger.info(f"Cleanup thread: removed {cleaned} old tasks")
            except Exception as e:
                api_logger.error(f"Cleanup thread error: {e}", exc_info=True)
    
    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    api_logger.info(f"Cleanup thread started (interval={interval_hours}h, max_age={max_age_hours}h)")
