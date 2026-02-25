"""
性能监控配置

功能：
- Prometheus 指标收集
- Grafana 仪表盘配置
- 告警规则配置
- 日志收集配置

作者：DevOps 孙工
日期：2026-03-01
"""

# ==================== Prometheus 配置 ====================

prometheus_yml = """
# Prometheus 配置文件
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    monitor: 'brand-diagnosis-monitor'

# 告警管理器
alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

# 规则文件
rule_files:
  - "alerts.yml"
  - "recording-rules.yml"

# 抓取配置
scrape_configs:
  # Prometheus 自监控
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
        labels:
          instance: 'prometheus-server'

  # 品牌诊断后端服务
  - job_name: 'brand-diagnosis-backend'
    static_configs:
      - targets: ['localhost:5000']
        labels:
          instance: 'backend-server'
          environment: 'production'
    metrics_path: '/metrics'
    scrape_interval: 10s

  # 数据库监控
  - job_name: 'sqlite-database'
    static_configs:
      - targets: ['localhost:9187']
        labels:
          instance: 'sqlite-database'
    
  # 节点导出器
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
        labels:
          instance: 'app-server'
"""

# ==================== 告警规则 ====================

alerts_yml = """
groups:
  # API 健康告警
  - name: api_health
    interval: 30s
    rules:
      # AI API 高失败率告警
      - alert: ExternalAPIHighFailureRate
        expr: rate(ai_call_failed_total[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "外部 API 失败率过高"
          description: "{{ $labels.source }} 失败率超过 30%，持续 5 分钟"
          runbook_url: "https://wiki.example.com/runbooks/api-failure"

      # AI API 完全失败告警
      - alert: ExternalAPICompleteFailure
        expr: rate(ai_call_failed_total[5m]) > 0.9
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "外部 API 完全失败"
          description: "{{ $labels.source }} 失败率超过 90%，持续 2 分钟"
          runbook_url: "https://wiki.example.com/runbooks/api-complete-failure"

      # API 响应时间过长告警
      - alert: APIHighLatency
        expr: histogram_quantile(0.95, rate(api_response_time_seconds_bucket[5m])) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 响应时间过长"
          description: "95% 的 API 请求响应时间超过 5 秒"
          runbook_url: "https://wiki.example.com/runbooks/api-latency"

      # API 超时告警
      - alert: APITimeout
        expr: rate(api_timeout_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 超时率过高"
          description: "API 超时率超过 10%，持续 5 分钟"
          runbook_url: "https://wiki.example.com/runbooks/api-timeout"

  # 数据库告警
  - name: database_health
    interval: 30s
    rules:
      # 数据库连接池耗尽告警
      - alert: DatabaseConnectionPoolExhausted
        expr: db_pool_available_connections / db_pool_max_connections < 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接池即将耗尽"
          description: "数据库连接池可用连接少于 10%"
          runbook_url: "https://wiki.example.com/runbooks/db-pool-exhausted"

      # 数据库写入失败告警
      - alert: DatabaseWriteFailure
        expr: rate(db_write_failed_total[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "数据库写入失败"
          description: "数据库写入失败率超过 10%"
          runbook_url: "https://wiki.example.com/runbooks/db-write-failure"

      # 快照保存失败告警
      - alert: SnapshotSaveFailure
        expr: rate(snapshot_save_failed_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "快照保存失败率过高"
          description: "快照保存失败率超过 5%"
          runbook_url: "https://wiki.example.com/runbooks/snapshot-failure"

  # 系统资源告警
  - name: system_resources
    interval: 30s
    rules:
      # CPU 使用率过高告警
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU 使用率过高"
          description: "{{ $labels.instance }} CPU 使用率超过 80%"
          runbook_url: "https://wiki.example.com/runbooks/high-cpu"

      # 内存使用率过高告警
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "{{ $labels.instance }} 内存使用率超过 85%"
          runbook_url: "https://wiki.example.com/runbooks/high-memory"

      # 磁盘使用率过高告警
      - alert: HighDiskUsage
        expr: (1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "磁盘使用率过高"
          description: "{{ $labels.instance }} 磁盘使用率超过 85%"
          runbook_url: "https://wiki.example.com/runbooks/high-disk"

  # 业务指标告警
  - name: business_metrics
    interval: 30s
    rules:
      # 报告生成失败率过高告警
      - alert: ReportGenerationFailureRate
        expr: rate(report_generation_failed_total[5m]) / rate(report_generation_total[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "报告生成失败率过高"
          description: "报告生成失败率超过 10%"
          runbook_url: "https://wiki.example.com/runbooks/report-failure"

      # 重试率过高告警
      - alert: HighRetryRate
        expr: rate(dimension_retry_total[5m]) / rate(dimension_generation_total[5m]) > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "维度重试率过高"
          description: "维度重试率超过 30%，可能 AI 服务不稳定"
          runbook_url: "https://wiki.example.com/runbooks/high-retry"
"""

# ==================== 记录规则 ====================

recording_rules_yml = """
groups:
  # API 指标记录规则
  - name: api_recording_rules
    interval: 30s
    rules:
      # API 请求总数（5 分钟）
      - record: api:requests_total:5m
        expr: sum(rate(api_requests_total[5m]))

      # API 失败率（5 分钟）
      - record: api:failure_rate:5m
        expr: sum(rate(api_requests_failed_total[5m])) / sum(rate(api_requests_total[5m]))

      # API 响应时间 P95（5 分钟）
      - record: api:response_time_p95:5m
        expr: histogram_quantile(0.95, sum(rate(api_response_time_seconds_bucket[5m])) by (le))

      # API 响应时间 P99（5 分钟）
      - record: api:response_time_p99:5m
        expr: histogram_quantile(0.99, sum(rate(api_response_time_seconds_bucket[5m])) by (le))

  # 数据库指标记录规则
  - name: database_recording_rules
    interval: 30s
    rules:
      # 数据库连接池使用率
      - record: db:pool_usage_ratio
        expr: 1 - (db_pool_available_connections / db_pool_max_connections)

      # 数据库查询延迟 P95
      - record: db:query_time_p95:5m
        expr: histogram_quantile(0.95, sum(rate(db_query_time_seconds_bucket[5m])) by (le))

  # 业务指标记录规则
  - name: business_recording_rules
    interval: 30s
    rules:
      # 报告生成成功率
      - record: business:report_success_rate:5m
        expr: 1 - (sum(rate(report_generation_failed_total[5m])) / sum(rate(report_generation_total[5m])))

      # 维度重试率
      - record: business:dimension_retry_rate:5m
        expr: sum(rate(dimension_retry_total[5m])) / sum(rate(dimension_generation_total[5m]))
"""

# ==================== Grafana 仪表盘配置 ====================

grafana_dashboard = """
{
  "dashboard": {
    "title": "品牌诊断系统监控",
    "tags": ["brand-diagnosis"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "API 请求量",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(api_requests_total[5m]))",
            "legendFormat": "Requests/s"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "API 失败率",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(api_requests_failed_total[5m])) / sum(rate(api_requests_total[5m])) * 100",
            "legendFormat": "Failure Rate %"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "API 响应时间",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.50, sum(rate(api_response_time_seconds_bucket[5m])) by (le))",
            "legendFormat": "P50"
          },
          {
            "expr": "histogram_quantile(0.95, sum(rate(api_response_time_seconds_bucket[5m])) by (le))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.99, sum(rate(api_response_time_seconds_bucket[5m])) by (le))",
            "legendFormat": "P99"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "AI 调用统计",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(ai_call_total[5m])) by (source)",
            "legendFormat": "{{source}} - Total"
          },
          {
            "expr": "sum(rate(ai_call_failed_total[5m])) by (source)",
            "legendFormat": "{{source}} - Failed"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      },
      {
        "id": 5,
        "title": "数据库连接池",
        "type": "graph",
        "targets": [
          {
            "expr": "db_pool_max_connections",
            "legendFormat": "Max Connections"
          },
          {
            "expr": "db_pool_available_connections",
            "legendFormat": "Available Connections"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 6,
        "title": "报告生成统计",
        "type": "graph",
        "targets": [
          {
            "expr": "sum(rate(report_generation_total[5m]))",
            "legendFormat": "Total Reports"
          },
          {
            "expr": "sum(rate(report_generation_failed_total[5m]))",
            "legendFormat": "Failed Reports"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      },
      {
        "id": 7,
        "title": "系统资源",
        "type": "graph",
        "targets": [
          {
            "expr": "100 - (avg by(instance) (irate(node_cpu_seconds_total{mode=\"idle\"}[5m])) * 100)",
            "legendFormat": "CPU Usage %"
          },
          {
            "expr": "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100",
            "legendFormat": "Memory Usage %"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24}
      },
      {
        "id": 8,
        "title": "告警状态",
        "type": "alertlist",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24}
      }
    ],
    "refresh": "30s",
    "version": 1
  }
}
"""

# ==================== 应用监控埋点 ====================

app_monitoring_code = """
# 在应用代码中添加监控埋点

# 1. 在 app.py 中添加 Prometheus 指标导出
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
import time
import functools

# 定义指标
API_REQUESTS = Counter('api_requests_total', 'Total API requests', ['endpoint', 'method'])
API_REQUESTS_FAILED = Counter('api_requests_failed_total', 'Total failed API requests', ['endpoint', 'method'])
API_RESPONSE_TIME = Histogram('api_response_time_seconds', 'API response time in seconds', ['endpoint'])

AI_CALLS = Counter('ai_call_total', 'Total AI calls', ['source'])
AI_CALLS_FAILED = Counter('ai_call_failed_total', 'Total failed AI calls', ['source'])

DB_POOL_MAX = Gauge('db_pool_max_connections', 'Maximum database connections')
DB_POOL_AVAILABLE = Gauge('db_pool_available_connections', 'Available database connections')

REPORT_GENERATION = Counter('report_generation_total', 'Total report generations')
REPORT_GENERATION_FAILED = Counter('report_generation_failed_total', 'Total failed report generations')

DIMENSION_GENERATION = Counter('dimension_generation_total', 'Total dimension generations')
DIMENSION_RETRY = Counter('dimension_retry_total', 'Total dimension retries')

# 监控装饰器
def monitored_endpoint(endpoint_name):
    def decorator(f):
        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            API_REQUESTS.labels(endpoint=endpoint_name, method=request.method).inc()
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            except Exception as e:
                API_REQUESTS_FAILED.labels(endpoint=endpoint_name, method=request.method).inc()
                raise
            finally:
                API_RESPONSE_TIME.labels(endpoint=endpoint_name).observe(time.time() - start_time)
        return wrapped
    return decorator

# 添加/metrics 端点
@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

# 2. 在 AI 调用处添加监控
def call_ai_with_monitoring(source, prompt):
    AI_CALLS.labels(source=source).inc()
    try:
        result = ai_client.send_prompt(prompt)
        return result
    except Exception as e:
        AI_CALLS_FAILED.labels(source=source).inc()
        raise

# 3. 在报告生成处添加监控
def generate_report_with_monitoring(...):
    REPORT_GENERATION.inc()
    try:
        result = generate_report(...)
        return result
    except Exception as e:
        REPORT_GENERATION_FAILED.inc()
        raise

# 4. 在维度重试处添加监控
def retry_dimension_with_monitoring(...):
    DIMENSION_RETRY.inc()
    return retry_dimension(...)
"""

# ==================== 日志收集配置 ====================

fluentd_config = """
# Fluentd 配置文件
<source>
  @type tail
  path /var/log/brand-diagnosis/*.log
  pos_file /var/log/fluentd/brand-diagnosis.log.pos
  tag brand.diagnosis
  <parse>
    @type json
  </parse>
</source>

<filter brand.diagnosis>
  @type record_transformer
  <record>
    hostname ${hostname}
    environment production
    service brand-diagnosis
  </record>
</filter>

<match brand.diagnosis>
  @type elasticsearch
  host elasticsearch.example.com
  port 9200
  index_name brand-diagnosis-logs
  type_name _doc
</match>
"""

# ==================== Docker Compose 配置 ====================

docker_compose_yml = """
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml
      - ./monitoring/prometheus/recording-rules.yml:/etc/prometheus/recording-rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    restart: always

  # Grafana
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/dashboards
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=grafana_admin_password
      - GF_USERS_ALLOW_SIGN_UP=false
    restart: always
    depends_on:
      - prometheus

  # Alertmanager
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager_data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    restart: always

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.ignored-mount-points'
      - '^/(sys|proc|dev|host|etc|rootfs/var/lib/docker/containers|rootfs/var/lib/docker/overlay2|rootfs/run/docker/netns|rootfs/var/lib/docker/aufs)($$|/)'
    restart: always

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
"""

# ==================== 告警通知配置 ====================

alertmanager_yml = """
global:
  smtp_smarthost: 'smtp.example.com:587'
  smtp_from: 'alertmanager@example.com'
  smtp_auth_username: 'alertmanager@example.com'
  smtp_auth_password: 'password'

route:
  group_by: ['alertname', 'severity']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h
  receiver: 'default-receiver'
  routes:
    - match:
        severity: critical
      receiver: 'critical-receiver'
      repeat_interval: 1h
    - match:
        severity: warning
      receiver: 'warning-receiver'
      repeat_interval: 4h

receivers:
  - name: 'default-receiver'
    email_configs:
      - to: 'dev-team@example.com'
        send_resolved: true

  - name: 'critical-receiver'
    email_configs:
      - to: 'oncall@example.com'
        send_resolved: true
    webhook_configs:
      - url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
        send_resolved: true

  - name: 'warning-receiver'
    email_configs:
      - to: 'dev-team@example.com'
        send_resolved: true

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
"""

# ==================== 安装脚本 ====================

install_script = """#!/bin/bash
# 性能监控安装脚本

set -e

echo "=========================================="
echo "品牌诊断系统 - 性能监控安装脚本"
echo "=========================================="

# 创建目录
echo "[1/5] 创建目录结构..."
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/provisioning
mkdir -p monitoring/alertmanager
mkdir -p logs

# 复制配置文件
echo "[2/5] 复制配置文件..."
cp prometheus.yml monitoring/prometheus/
cp alerts.yml monitoring/prometheus/
cp recording-rules.yml monitoring/prometheus/
cp alertmanager.yml monitoring/alertmanager/
cp grafana-dashboard.json monitoring/grafana/dashboards/

# 启动 Docker 服务
echo "[3/5] 启动监控服务..."
docker-compose up -d prometheus grafana alertmanager node-exporter

# 等待服务启动
echo "[4/5] 等待服务启动..."
sleep 10

# 验证服务
echo "[5/5] 验证服务..."
echo "Prometheus: http://localhost:9090"
echo "Grafana: http://localhost:3000 (admin/grafana_admin_password)"
echo "Alertmanager: http://localhost:9093"
echo "Node Exporter: http://localhost:9100"

echo ""
echo "=========================================="
echo "安装完成！"
echo "=========================================="
echo ""
echo "下一步:"
echo "1. 登录 Grafana 添加 Prometheus 数据源"
echo "2. 导入监控仪表盘"
echo "3. 配置告警通知渠道"
echo "4. 验证告警规则"
"""

print("✅ 性能监控配置文件已生成")
print("文件列表:")
print("  - prometheus.yml")
print("  - alerts.yml")
print("  - recording-rules.yml")
print("  - grafana-dashboard.json")
print("  - alertmanager.yml")
print("  - docker-compose.yml")
print("  - install.sh")
