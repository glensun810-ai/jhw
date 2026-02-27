"""
状态机模块

包含诊断任务状态机的核心实现：
- DiagnosisState: 状态枚举
- DiagnosisStateMachine: 状态机类
"""

from wechat_backend.v2.state_machine.states import DiagnosisState
from wechat_backend.v2.state_machine.diagnosis_state_machine import DiagnosisStateMachine

__all__ = [
    'DiagnosisState',
    'DiagnosisStateMachine',
]
