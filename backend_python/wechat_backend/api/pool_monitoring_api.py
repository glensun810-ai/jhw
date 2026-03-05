"""
连接池监控 API

提供连接池监控相关的 REST API 端点:
- GET /api/monitoring/pool/metrics - 获取实时指标
- GET /api/monitoring/pool/history - 获取历史记录
- GET /api/monitoring/pool/status - 获取监控状态
- GET /api/monitoring/pool/health - 健康检查
- POST /api/monitoring/pool/alerts/test - 测试告警
- GET /api/monitoring/pool/prometheus - Prometheus 指标
- POST /api/monitoring/pool/config - 配置热更新

【P0 实现 - 2026-03-05】
【P2 增强 - 2026-03-05】Prometheus 导出、配置热更新
"""

from flask import Blueprint, jsonify, request, Response
from datetime import datetime
from typing import Dict, Any
from wechat_backend.logging_config import api_logger

# 创建蓝图
pool_monitoring_bp = Blueprint('pool_monitoring', __name__, url_prefix='/api/monitoring/pool')


@pool_monitoring_bp.route('/metrics', methods=['GET'])
def get_pool_metrics():
    """
    获取连接池实时指标

    返回:
        {
            "success": true,
            "data": {
                "database": {...},  # 数据库连接池指标
                "http": {...},      # HTTP 连接池指标
                "timestamp": "..."
            }
        }
    """
    try:
        from wechat_backend.database_connection_pool import get_db_pool_metrics
        from wechat_backend.network.connection_pool import get_connection_pool_manager
        from wechat_backend.monitoring.connection_pool_monitor import get_connection_pool_metrics

        # 数据库连接池指标
        db_metrics = None
        try:
            db_metrics = get_db_pool_metrics()
        except Exception as e:
            api_logger.warning(f"获取数据库连接池指标失败：{e}")

        # HTTP 连接池指标
        http_metrics = None
        try:
            manager = get_connection_pool_manager()
            http_metrics = {
                'pool_connections': manager.pool_connections,
                'pool_maxsize': manager.pool_maxsize,
                'active_sessions': len(manager.sessions),
                'health_status': 'healthy',
                'health_message': 'HTTP 连接池运行正常'
            }
        except Exception as e:
            api_logger.warning(f"获取 HTTP 连接池指标失败：{e}")

        # 监控指标
        monitor_metrics = get_connection_pool_metrics()

        response_data = {
            'database': db_metrics,
            'http': http_metrics,
            'monitor': monitor_metrics,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        api_logger.error(f"获取连接池指标失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/history', methods=['GET'])
def get_pool_history():
    """
    获取连接池监控历史记录

    查询参数:
        limit: 返回数量限制 (默认 100)
        type: 类型 (database/http, 默认全部)

    返回:
        {
            "success": true,
            "data": {
                "database": [...],
                "http": [...],
                "total": 100
            }
        }
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        history_type = request.args.get('type', 'all')

        from wechat_backend.monitoring.connection_pool_monitor import get_connection_pool_history

        history = get_connection_pool_history(limit=limit)

        response_data = {
            'history': history,
            'count': len(history),
            'limit': limit,
            'timestamp': datetime.now().isoformat()
        }

        return jsonify({
            'success': True,
            'data': response_data
        })

    except Exception as e:
        api_logger.error(f"获取连接池历史失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/status', methods=['GET'])
def get_pool_monitor_status():
    """
    获取监控器状态

    返回:
        {
            "success": true,
            "data": {
                "started": true,
                "monitors": {
                    "database": {"running": true, "latest_metrics": {...}},
                    "http": {"running": true, "latest_metrics": {...}}
                }
            }
        }
    """
    try:
        from wechat_backend.monitoring.connection_pool_monitor_launcher import (
            get_pool_monitor_status
        )

        status = get_pool_monitor_status()

        return jsonify({
            'success': True,
            'data': status
        })

    except Exception as e:
        api_logger.error(f"获取监控器状态失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/health', methods=['GET'])
def get_pool_health():
    """
    连接池健康检查

    返回:
        {
            "success": true,
            "data": {
                "status": "healthy",  # healthy/warning/critical
                "database": {...},
                "http": {...},
                "alerts": [...],
                "timestamp": "..."
            }
        }
    """
    try:
        from wechat_backend.database_connection_pool import get_db_pool_metrics
        from wechat_backend.network.connection_pool import get_connection_pool_manager
        from wechat_backend.monitoring.enhanced_alert_manager import get_alert_summary

        # 数据库连接池健康状态
        db_status = 'healthy'
        db_metrics = None
        try:
            db_metrics = get_db_pool_metrics()
            if db_metrics:
                db_status = db_metrics.get('health_status', 'healthy')
        except Exception as e:
            db_status = 'unhealthy'
            api_logger.warning(f"获取数据库连接池健康状态失败：{e}")

        # HTTP 连接池健康状态
        http_status = 'healthy'
        http_metrics = None
        try:
            manager = get_connection_pool_manager()
            http_metrics = {
                'pool_connections': manager.pool_connections,
                'pool_maxsize': manager.pool_maxsize,
                'active_sessions': len(manager.sessions)
            }
        except Exception as e:
            http_status = 'unhealthy'
            api_logger.warning(f"获取 HTTP 连接池健康状态失败：{e}")

        # 总体健康状态
        overall_status = 'healthy'
        if db_status == 'critical' or http_status == 'unhealthy':
            overall_status = 'critical'
        elif db_status == 'warning':
            overall_status = 'warning'

        # 告警统计
        alert_summary = None
        try:
            from wechat_backend.monitoring.enhanced_alert_manager import (
                get_enhanced_alert_manager
            )
            alert_manager = get_enhanced_alert_manager()
            alert_summary = alert_manager.get_alert_summary()
        except Exception as e:
            api_logger.warning(f"获取告警统计失败：{e}")

        response_data = {
            'status': overall_status,
            'database': {
                'status': db_status,
                'metrics': db_metrics
            },
            'http': {
                'status': http_status,
                'metrics': http_metrics
            },
            'alerts': alert_summary,
            'timestamp': datetime.now().isoformat()
        }

        # 根据健康状态返回不同的 HTTP 状态码
        status_code = 200
        if overall_status == 'critical':
            status_code = 503
        elif overall_status == 'warning':
            status_code = 200  # 警告仍然返回 200，但包含警告信息

        return jsonify({
            'success': True,
            'data': response_data
        }), status_code

    except Exception as e:
        api_logger.error(f"健康检查失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/alerts/test', methods=['POST'])
def test_pool_alerts():
    """
    测试告警通知

    请求体:
        {
            "severity": "warning",  # warning/error/critical
            "channels": ["log", "webhook"]  # 可选，指定渠道
        }

    返回:
        {
            "success": true,
            "data": {
                "results": {...},
                "message": "告警测试已发送"
            }
        }
    """
    try:
        data = request.get_json() or {}
        severity = data.get('severity', 'warning')
        channels = data.get('channels')

        from wechat_backend.monitoring.enhanced_alert_manager import (
            get_enhanced_alert_manager,
            AlertNotification,
            AlertSeverity
        )

        alert_manager = get_enhanced_alert_manager()

        # 创建测试告警
        notification = AlertNotification(
            title="🧪 连接池告警测试",
            message="这是一条测试告警，用于验证通知渠道是否正常工作",
            severity=severity,
            metric_name='test_connection_pool_alert',
            current_value=0.75,
            threshold=0.8,
            metadata={'test': True}
        )

        # 发送告警
        results = alert_manager.send_alert(notification, channels)

        return jsonify({
            'success': True,
            'data': {
                'results': results,
                'message': '告警测试已发送',
                'channels': channels or ['log', 'webhook', 'email', 'sms']
            }
        })

    except Exception as e:
        api_logger.error(f"测试告警失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/alerts/history', methods=['GET'])
def get_alert_history():
    """
    获取告警历史

    查询参数:
        limit: 返回数量限制 (默认 50)
        severity: 严重程度过滤 (info/warning/error/critical)

    返回:
        {
            "success": true,
            "data": {
                "alerts": [...],
                "summary": {...},
                "count": 50
            }
        }
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        severity = request.args.get('severity')

        from wechat_backend.monitoring.enhanced_alert_manager import (
            get_enhanced_alert_manager
        )

        alert_manager = get_enhanced_alert_manager()
        history = alert_manager.get_alert_history(limit=limit, severity=severity)
        summary = alert_manager.get_alert_summary()

        return jsonify({
            'success': True,
            'data': {
                'alerts': history,
                'summary': summary,
                'count': len(history)
            }
        })

    except Exception as e:
        api_logger.error(f"获取告警历史失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/alerts/summary', methods=['GET'])
def get_alert_summary():
    """
    获取告警统计摘要

    返回:
        {
            "success": true,
            "data": {
                "total": 100,
                "by_severity": {...},
                "by_metric": {...},
                "last_24h": 10,
                "channels_usage": {...}
            }
        }
    """
    try:
        from wechat_backend.monitoring.enhanced_alert_manager import (
            get_enhanced_alert_manager
        )

        alert_manager = get_enhanced_alert_manager()
        summary = alert_manager.get_alert_summary()

        return jsonify({
            'success': True,
            'data': summary
        })

    except Exception as e:
        api_logger.error(f"获取告警统计失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 【P2 新增】Prometheus 指标导出 ====================

@pool_monitoring_bp.route('/prometheus', methods=['GET'])
def get_prometheus_metrics():
    """
    获取 Prometheus 格式指标

    返回:
        Prometheus 格式的纯文本指标
    """
    try:
        from wechat_backend.monitoring.prometheus_exporter import (
            get_prometheus_exporter,
            update_prometheus_metrics
        )
        from wechat_backend.database_connection_pool import get_db_pool_metrics
        from wechat_backend.monitoring.enhanced_alert_manager import get_enhanced_alert_manager

        exporter = get_prometheus_exporter()

        if not exporter or not exporter.enabled:
            return Response(
                "# Prometheus metrics not available (prometheus_client not installed)\n",
                mimetype='text/plain'
            )

        # 获取最新指标并更新
        pool_metrics = {
            'database': get_db_pool_metrics(),
            'http': None
        }

        try:
            from wechat_backend.network.connection_pool import get_connection_pool_manager
            manager = get_connection_pool_manager()
            pool_metrics['http'] = {
                'active_sessions': len(manager.sessions),
                'pool_maxsize': manager.pool_maxsize
            }
        except:
            pass

        # 获取告警统计
        alert_summary = None
        try:
            alert_manager = get_enhanced_alert_manager()
            alert_summary = alert_manager.get_alert_summary()
        except:
            pass

        # 更新 Prometheus 指标
        update_prometheus_metrics(pool_metrics, alert_summary)

        # 返回 Prometheus 格式数据
        metrics_data = exporter.get_metrics()

        return Response(
            metrics_data,
            mimetype=exporter.get_content_type()
        )

    except Exception as e:
        api_logger.error(f"生成 Prometheus 指标失败：{e}", exc_info=True)
        return Response(
            f"# Error generating metrics: {e}\n",
            mimetype='text/plain',
            status=500
        )


# ==================== 【P2 新增】配置热更新 ====================

@pool_monitoring_bp.route('/config', methods=['POST'])
def update_pool_config():
    """
    更新连接池配置（热更新，无需重启）

    请求体:
        {
            "auto_scale": {
                "enabled": true,
                "scale_up_threshold": 0.85,
                "scale_down_threshold": 0.3,
                "scale_step": 10,
                "min_connections": 10,
                "max_connections_hard": 100,
                "cooldown_seconds": 60
            },
            OR
            "alerts": {
                "webhook": {
                    "enabled": true,
                    "url": "https://hooks.slack.com/xxx"
                }
            }
        }

    返回:
        {
            "success": true,
            "data": {
                "updated": ["auto_scale", ...],
                "message": "配置已更新"
            }
        }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': '请求体不能为空'
            }), 400

        updated = []

        # 更新自动扩容配置
        if 'auto_scale' in data:
            from wechat_backend.database_connection_pool import get_db_pool
            pool = get_db_pool()

            config = data['auto_scale']
            pool.configure_auto_scale(
                enabled=config.get('enabled', True),
                scale_up_threshold=config.get('scale_up_threshold', 0.85),
                scale_down_threshold=config.get('scale_down_threshold', 0.3),
                scale_step=config.get('scale_step', 10),
                min_connections=config.get('min_connections', 10),
                max_connections_hard=config.get('max_connections_hard', 100),
                cooldown_seconds=config.get('cooldown_seconds', 60)
            )
            updated.append('auto_scale')
            api_logger.info(f"[配置热更新] 自动扩容配置已更新：{config}")

        # 更新告警配置
        if 'alerts' in data:
            from wechat_backend.monitoring.enhanced_alert_manager import get_enhanced_alert_manager
            alert_manager = get_enhanced_alert_manager()

            alerts_config = data['alerts']

            # 更新 Webhook 配置
            if 'webhook' in alerts_config:
                alert_manager.config['channels']['webhook'].update(alerts_config['webhook'])
                updated.append('alerts.webhook')

            # 更新邮件配置
            if 'email' in alerts_config:
                alert_manager.config['channels']['email'].update(alerts_config['email'])
                updated.append('alerts.email')

            # 更新短信配置
            if 'sms' in alerts_config:
                alert_manager.config['channels']['sms'].update(alerts_config['sms'])
                updated.append('alerts.sms')

            # 更新抑制配置
            if 'suppression' in alerts_config:
                alert_manager.config['suppression'].update(alerts_config['suppression'])
                updated.append('alerts.suppression')

            # 保存配置
            alert_manager._save_config()
            api_logger.info(f"[配置热更新] 告警配置已更新：{alerts_config}")

        if not updated:
            return jsonify({
                'success': False,
                'error': '未提供有效的配置项'
            }), 400

        return jsonify({
            'success': True,
            'data': {
                'updated': updated,
                'message': f'配置已更新：{", ".join(updated)}'
            }
        })

    except Exception as e:
        api_logger.error(f"更新配置失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@pool_monitoring_bp.route('/config', methods=['GET'])
def get_pool_config():
    """
    获取当前连接池配置

    返回:
        {
            "success": true,
            "data": {
                "auto_scale": {...},
                "alerts": {...}
            }
        }
    """
    try:
        from wechat_backend.database_connection_pool import get_db_pool
        from wechat_backend.monitoring.enhanced_alert_manager import get_enhanced_alert_manager

        pool = get_db_pool()
        alert_manager = get_enhanced_alert_manager()

        config = {
            'auto_scale': {
                'enabled': pool.auto_scale_enabled,
                'scale_up_threshold': pool.scale_up_threshold,
                'scale_down_threshold': pool.scale_down_threshold,
                'scale_step': pool.scale_step,
                'min_connections': pool.min_connections,
                'max_connections_hard': pool.max_connections_hard,
                'cooldown_seconds': pool._scale_cooldown_seconds
            },
            'alerts': alert_manager.config
        }

        return jsonify({
            'success': True,
            'data': config
        })

    except Exception as e:
        api_logger.error(f"获取配置失败：{e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def create_pool_monitoring_routes() -> Blueprint:
    """创建并返回连接池监控蓝图"""
    return pool_monitoring_bp
