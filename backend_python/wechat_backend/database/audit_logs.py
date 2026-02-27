from wechat_backend.log_config import get_logger

#!/usr/bin/env python3
"""
审计日志模块（差距 1 修复）

功能:
1. 记录所有 API 访问
2. 记录安全事件
3. 记录用户操作
4. 支持审计查询
"""

from datetime import datetime
from typing import Dict, Optional, List
import json
import logging

logger = logging.getLogger(__name__

try:
    from wechat_backend.database import db
    from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, BigInteger
    from sqlalchemy.ext.declarative import declarative_base
    
    Base = declarative_base(
    
    class AuditLog(Base):
        """审计日志模型"""
        __tablename__ = 'audit_logs'
        
        id = Column(Integer, primary_key=True, autoincrement=True
        user_id = Column(String(255), nullable=False, index=True
        action = Column(String(100), nullable=False, index=True
        resource = Column(String(255), index=True
        ip_address = Column(String(45))  # IPv6 max length
        user_agent = Column(String(512)
        request_method = Column(String(10)
        response_status = Column(Integer
        details = Column(JSON, nullable=True
        created_at = Column(DateTime, default=datetime.utcnow, index=True
        
        def to_dict(self) -> Dict:
            """转换为字典"""
            return {
                'id': self.id,
                'user_id': self.user_id,
                'action': self.action,
                'resource': self.resource,
                'ip_address': self.ip_address,
                'user_agent': self.user_agent,
                'request_method': self.request_method,
                'response_status': self.response_status,
                'details': self.details,
                'created_at': self.created_at.isoformat() if self.created_at else None
            }
    
    # 创建数据库表
    def init_audit_logs_db():
        """初始化审计日志数据库表"""
        try:
            Base.metadata.create_all(db.engine
            logger.info("审计日志数据库表初始化成功"
        except Exception as e:
            logger.error(f"审计日志数据库表初始化失败：{e}"
    
    # 数据库会话管理
    def get_db_session():
        """获取数据库会话"""
        from wechat_backend.database import db
        return db.session
    
except ImportError as e:
    logger.warning(f"数据库模块导入失败，审计日志将使用内存存储：{e}"
    AuditLog = None
    
    # 内存存储作为后备方案
    _memory_audit_logs = []
    
    def init_audit_logs_db():
        """初始化审计日志（内存版本）"""
        logger.info("审计日志系统已初始化（内存模式）"
    
    def get_db_session():
        """获取会话（内存版本）"""
        class MemorySession:
            def add(self, obj):
                pass
            def commit(self):
                pass
            def rollback(self):
                pass
        return MemorySession(


def create_audit_log(
    user_id: str,
    action: str,
    resource: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    request_method: Optional[str] = None,
    response_status: Optional[int] = None,
    details: Optional[Dict] = None
) -> Optional[int]:
    """
    创建审计日志记录
    
    Args:
        user_id: 用户 ID
        action: 操作类型 (api_access, security_event, data_access, etc.
        resource: 资源名称 (API 端点，数据表等
        ip_address: IP 地址
        user_agent: 用户代理
        request_method: 请求方法
        response_status: 响应状态码
        details: 详细信息 (JSON
    
    Returns:
        日志记录 ID，如果失败返回 None
    """
    try:
        if AuditLog is None:
            # 内存模式
            log_entry = {
                'user_id': user_id,
                'action': action,
                'resource': resource,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'request_method': request_method,
                'response_status': response_status,
                'details': details,
                'created_at': datetime.utcnow().isoformat(
            }
            _memory_audit_logs.append(log_entry
            logger.info(f"[Audit] {action}: {resource} by {user_id}"
            return len(_memory_audit_logs
        
        # 数据库模式
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            ip_address=ip_address,
            user_agent=user_agent[:512] if user_agent else None,
            request_method=request_method,
            response_status=response_status,
            details=details
        
        
        session = get_db_session(
        session.add(audit_log
        session.commit(
        
        logger.info(f"[Audit] {action}: {resource} by {user_id} from {ip_address}"
        return audit_log.id
        
    except Exception as e:
        logger.error(f"[Audit] 创建审计日志失败：{e}")
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"[Audit] 回滚审计日志失败：{rollback_error}", exc_info=True)
        return None


def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """
    查询审计日志
    
    Args:
        user_id: 用户 ID 过滤
        action: 操作类型过滤
        resource: 资源名称过滤
        start_date: 开始日期
        end_date: 结束日期
        limit: 返回数量限制
        offset: 偏移量
    
    Returns:
        审计日志列表
    """
    try:
        if AuditLog is None:
            # 内存模式
            logs = _memory_audit_logs
            
            # 过滤
            if user_id:
                logs = [l for l in logs if l['user_id'] == user_id]
            if action:
                logs = [l for l in logs if l['action'] == action]
            if resource:
                logs = [l for l in logs if l['resource'] == resource]
            
            # 按时间排序
            logs = sorted(logs, key=lambda x: x['created_at'], reverse=True
            
            return logs[offset:offset+limit]
        
        # 数据库模式
        session = get_db_session(
        query = session.query(AuditLog
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id
        if action:
            query = query.filter(AuditLog.action == action
        if resource:
            query = query.filter(AuditLog.resource == resource
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date
        
        # 按时间倒序排序
        query = query.order_by(AuditLog.created_at.desc()
        
        # 分页
        logs = query.offset(offset).limit(limit).all(
        
        return [log.to_dict() for log in logs]
        
    except Exception as e:
        logger.error(f"[Audit] 查询审计日志失败：{e}"
        return []


def get_audit_log_by_id(log_id: int) -> Optional[Dict]:
    """
    根据 ID 获取审计日志
    
    Args:
        log_id: 日志 ID
    
    Returns:
        审计日志记录，如果不存在返回 None
    """
    try:
        if AuditLog is None:
            # 内存模式
            if 0 < log_id <= len(_memory_audit_logs):
                return _memory_audit_logs[log_id - 1]
            return None
        
        # 数据库模式
        session = get_db_session(
        log = session.query(AuditLog).filter(AuditLog.id == log_id).first(
        
        return log.to_dict() if log else None
        
    except Exception as e:
        logger.error(f"[Audit] 获取审计日志失败：{e}"
        return None


def clear_old_audit_logs(days: int = 90) -> int:
    """
    清理旧的审计日志
    
    Args:
        days: 保留的天数
    
    Returns:
        清理的日志数量
    """
    try:
        if AuditLog is None:
            # 内存模式
            cutoff_date = datetime.utcnow() - timedelta(days=days
            original_count = len(_memory_audit_logs
            
            _memory_audit_logs[:] = [
                log for log in _memory_audit_logs
                if datetime.fromisoformat(log['created_at']) > cutoff_date
            ]
            
            cleared = original_count - len(_memory_audit_logs
            logger.info(f"[Audit] 清理了 {cleared} 条旧审计日志"
            return cleared
        
        # 数据库模式
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days
        
        session = get_db_session(
        count = session.query(AuditLog).filter(AuditLog.created_at < cutoff_date).count(
        session.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete(
        session.commit(
        
        logger.info(f"[Audit] 清理了 {count} 条旧审计日志"
        return count
        
    except Exception as e:
        logger.error(f"[Audit] 清理审计日志失败：{e}")
        try:
            session.rollback()
        except Exception as rollback_error:
            logger.error(f"[Audit] 回滚清理审计日志失败：{rollback_error}", exc_info=True)
        return 0


# 便捷函数
def log_api_access(user_id: str, endpoint: str, method: str, status: int, ip: str = None):
    """记录 API 访问日志"""
    return create_audit_log(
        user_id=user_id,
        action='api_access',
        resource=endpoint,
        request_method=method,
        response_status=status,
        ip_address=ip
    


def log_security_event(user_id: str, event_type: str, description: str, ip: str = None):
    """记录安全事件"""
    return create_audit_log(
        user_id=user_id,
        action='security_event',
        resource=event_type,
        details={'description': description},
        ip_address=ip
    


def log_data_access(user_id: str, data_type: str, data_id: str, operation: str):
    """记录数据访问"""
    return create_audit_log(
        user_id=user_id,
        action='data_access',
        resource=f"{data_type}:{data_id}",
        details={'operation': operation}
    


# 初始化
if __name__ == '__main__':
    print("="*60
    print("审计日志模块测试"
    print("="*60
    
    # 初始化数据库
    init_audit_logs_db(
    
    # 测试创建日志
    log_id = create_audit_log(
        user_id='test_user',
        action='api_access',
        resource='/api/test',
        ip_address='127.0.0.1',
        request_method='GET',
        response_status=200
    
    f"✅ 创建审计日志成功，ID: {log_id}"
    
    # 测试查询日志
    logs = get_audit_logs(user_id='test_user', limit=10
    f"✅ 查询到 {len(logs)} 条审计日志"
    
    print("="*60
