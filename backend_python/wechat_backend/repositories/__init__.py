"""
数据仓库层

导出所有仓库类和便捷函数
"""

from wechat_backend.repositories.report_snapshot_repository import (
    ReportSnapshotRepository,
    get_snapshot_repository,
    save_report_snapshot,
    get_report_snapshot
)

from wechat_backend.repositories.dimension_result_repository import (
    DimensionResultRepository,
    get_dimension_repository,
    save_dimension_result,
    get_dimension_results,
    save_dimension_results_batch
)

from wechat_backend.repositories.task_status_repository import (
    save_task_status,
    get_task_status,
    update_task_progress
)

__all__ = [
    # Report Snapshot
    'ReportSnapshotRepository',
    'get_snapshot_repository',
    'save_report_snapshot',
    'get_report_snapshot',

    # Dimension Result
    'DimensionResultRepository',
    'get_dimension_repository',
    'save_dimension_result',
    'get_dimension_results',
    
    # Task Status
    'save_task_status',
    'get_task_status',
    'update_task_progress',
]
