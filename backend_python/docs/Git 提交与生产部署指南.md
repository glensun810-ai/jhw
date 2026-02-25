# Git 提交与生产部署指南

**文档编号**: DEPLOY-GUIDE-20260306-001  
**创建日期**: 2026-03-06  
**负责人**: DevOps 孙工  

---

## 一、Git 提交

### 1.1 提交清单

#### 核心代码文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `wechat_backend/nxm_concurrent_engine.py` | 新增 | 并发执行引擎 |
| `wechat_backend/smart_circuit_breaker.py` | 新增 | 智能熔断器 |
| `wechat_backend/ai_timeout.py` | 修改 | 动态超时配置 |
| `wechat_backend/repositories/dimension_result_repository.py` | 修改 | 批量数据库写入 |
| `wechat_backend/repositories/__init__.py` | 修改 | 导出批量写入函数 |
| `wechat_backend/repositories/task_status_repository.py` | 新增 | 任务状态仓库 |

#### 测试文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `tests/test_integration_p0.py` | 新增 | 集成测试脚本 |
| `tests/test_performance_p0.py` | 新增 | 性能测试脚本 |

#### 文档文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `docs/20 秒极速响应优化方案_20260306.md` | 新增 | 优化方案 |
| `docs/P0 优化实施计划_20260306.md` | 新增 | 实施计划 |
| `docs/P0 优化实施完成报告_20260306.md` | 新增 | 实施报告 |
| `docs/P0 优化集成与性能测试报告_20260306.md` | 新增 | 测试报告 |
| `docs/P0 优化最终完成报告_20260306.md` | 新增 | 最终报告 |

---

### 1.2 Git 提交命令

```bash
# 1. 进入项目目录
cd /Users/sgl/PycharmProjects/PythonProject

# 2. 查看变更
git status

# 3. 添加核心代码文件
git add backend_python/wechat_backend/nxm_concurrent_engine.py
git add backend_python/wechat_backend/smart_circuit_breaker.py
git add backend_python/wechat_backend/ai_timeout.py
git add backend_python/wechat_backend/repositories/dimension_result_repository.py
git add backend_python/wechat_backend/repositories/__init__.py
git add backend_python/wechat_backend/repositories/task_status_repository.py

# 4. 添加测试文件
git add backend_python/tests/test_integration_p0.py
git add backend_python/tests/test_performance_p0.py

# 5. 添加文档文件
git add backend_python/docs/20\ 秒极速响应优化方案_20260306.md
git add backend_python/docs/P0\ 优化实施计划_20260306.md
git add backend_python/docs/P0\ 优化实施完成报告_20260306.md
git add backend_python/docs/P0\ 优化集成与性能测试报告_20260306.md
git add backend_python/docs/P0\ 优化最终完成报告_20260306.md

# 6. 提交
git commit -m "feat: P0 性能优化 - 并发执行引擎和智能熔断器

主要变更:
- 新增并发执行引擎 (8 线程并发，35 秒超时)
- 新增智能熔断器 (5 次失败熔断，30 秒恢复)
- 新增动态超时配置 (根据问题长度调整)
- 新增批量数据库写入 (事务批量保存)

性能提升:
- 端到端延迟：>300 秒 → 4.11 秒 (73 倍提升)
- 成功率：0% → 100%
- 并发度：1 → 8 (8 倍提升)

测试覆盖:
- 集成测试：7/7 通过 (100%)
- 性能测试：5/5 通过 (100%)
- 报告验证：通过

相关文档:
- docs/20 秒极速响应优化方案_20260306.md
- docs/P0 优化最终完成报告_20260306.md

Refs: P0-20260306"

# 7. 推送到远程仓库
git push origin main

# 8. 验证推送
git status
```

---

### 1.3 快速提交脚本

```bash
#!/bin/bash
# scripts/commit_p0_optimization.sh

set -e

echo "=========================================="
echo "P0 优化 Git 提交脚本"
echo "=========================================="

cd /Users/sgl/PycharmProjects/PythonProject

# 添加文件
echo "[1/4] 添加核心代码..."
git add backend_python/wechat_backend/nxm_concurrent_engine.py
git add backend_python/wechat_backend/smart_circuit_breaker.py
git add backend_python/wechat_backend/ai_timeout.py
git add backend_python/wechat_backend/repositories/

echo "[2/4] 添加测试文件..."
git add backend_python/tests/test_integration_p0.py
git add backend_python/tests/test_performance_p0.py

echo "[3/4] 添加文档..."
git add backend_python/docs/*20260306*.md

echo "[4/4] 提交并推送..."
git commit -m "feat: P0 性能优化 - 并发执行引擎和智能熔断器

主要变更:
- 新增并发执行引擎 (8 线程并发，35 秒超时)
- 新增智能熔断器 (5 次失败熔断，30 秒恢复)
- 新增动态超时配置 (根据问题长度调整)
- 新增批量数据库写入 (事务批量保存)

性能提升:
- 端到端延迟：>300 秒 → 4.11 秒 (73 倍提升)
- 成功率：0% → 100%
- 并发度：1 → 8 (8 倍提升)

测试覆盖:
- 集成测试：7/7 通过 (100%)
- 性能测试：5/5 通过 (100%)

Refs: P0-20260306"

git push origin main

echo "=========================================="
echo "✅ 提交完成！"
echo "=========================================="
```

---

## 二、生产部署

### 2.1 部署前检查清单

#### 环境检查

- [ ] 生产服务器已准备
- [ ] 数据库备份已完成
- [ ] 监控告警已配置
- [ ] 回滚方案已准备

#### 代码检查

- [ ] 所有测试通过
- [ ] 代码已合并到 main 分支
- [ ] 版本号已更新
- [ ] CHANGELOG 已更新

#### 配置检查

- [ ] 生产环境配置文件已准备
- [ ] API Key 已配置
- [ ] 数据库连接已配置
- [ ] 日志配置已准备

---

### 2.2 部署脚本

```bash
#!/bin/bash
# scripts/deploy_production.sh

set -e

echo "=========================================="
echo "品牌诊断系统 - 生产部署脚本"
echo "=========================================="
echo "部署时间：$(date)"
echo "=========================================="

# 1. 备份当前版本
echo "[1/8] 备份当前版本..."
BACKUP_DIR="/backup/brand_diagnosis/$(date +%Y%m%d_%H%M%S)"
mkdir -p $BACKUP_DIR
cp -r /var/www/brand_diagnosis/backend_python $BACKUP_DIR/
echo "✅ 备份完成：$BACKUP_DIR"

# 2. 拉取最新代码
echo "[2/8] 拉取最新代码..."
cd /var/www/brand_diagnosis
git pull origin main
echo "✅ 代码拉取完成"

# 3. 安装依赖
echo "[3/8] 安装依赖..."
pip3 install -r backend_python/requirements.txt
echo "✅ 依赖安装完成"

# 4. 数据库迁移
echo "[4/8] 数据库迁移..."
cd backend_python
python3 database/run_migration.py
echo "✅ 数据库迁移完成"

# 5. 验证配置
echo "[5/8] 验证配置..."
python3 -c "from config import Config; print('✅ 配置验证通过')"
echo "✅ 配置验证完成"

# 6. 运行测试
echo "[6/8] 运行测试..."
python3 -m pytest tests/test_integration_p0.py -v --tb=short
python3 -m pytest tests/test_performance_p0.py -v --tb=short
echo "✅ 测试运行完成"

# 7. 重启服务
echo "[7/8] 重启服务..."
sudo systemctl restart brand-diagnosis-backend
sudo systemctl status brand-diagnosis-backend
echo "✅ 服务重启完成"

# 8. 健康检查
echo "[8/8] 健康检查..."
sleep 5
curl -s http://localhost:5000/api/test | grep -q "success" && echo "✅ 健康检查通过" || echo "❌ 健康检查失败"

echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo "部署时间：$(date)"
echo "备份位置：$BACKUP_DIR"
echo "=========================================="
```

---

### 2.3 灰度发布脚本

```bash
#!/bin/bash
# scripts/gray_release.sh

set -e

GRAY_PERCENT=${1:-1}  # 默认 1%

echo "=========================================="
echo "品牌诊断系统 - 灰度发布脚本"
echo "=========================================="
echo "灰度比例：${GRAY_PERCENT}%"
echo "=========================================="

# 更新 Nginx 配置
cat > /etc/nginx/conf.d/brand_diagnosis_gray.conf << EOF
upstream brand_diagnosis_backend {
    server 10.0.1.10:5000 weight=$((100 - GRAY_PERCENT));  # 旧版本
    server 10.0.1.11:5000 weight=${GRAY_PERCENT};           # 新版本
}

server {
    listen 80;
    server_name brand-diagnosis.example.com;

    location / {
        proxy_pass http://brand_diagnosis_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

# 重载 Nginx
sudo nginx -t && sudo nginx -s reload

echo "✅ 灰度发布完成：${GRAY_PERCENT}%"
```

---

### 2.4 回滚脚本

```bash
#!/bin/bash
# scripts/rollback.sh

set -e

BACKUP_VERSION=${1:-latest}

echo "=========================================="
echo "品牌诊断系统 - 回滚脚本"
echo "=========================================="
echo "回滚版本：$BACKUP_VERSION"
echo "=========================================="

# 1. 停止服务
echo "[1/5] 停止服务..."
sudo systemctl stop brand-diagnosis-backend

# 2. 找到备份
if [ "$BACKUP_VERSION" == "latest" ]; then
    BACKUP_DIR=$(ls -td /backup/brand_diagnosis/* | head -1)
else
    BACKUP_DIR="/backup/brand_diagnosis/$BACKUP_VERSION"
fi

echo "回滚到：$BACKUP_DIR"

# 3. 恢复代码
echo "[2/5] 恢复代码..."
rm -rf /var/www/brand_diagnosis/backend_python
cp -r $BACKUP_DIR/backend_python /var/www/brand_diagnosis/

# 4. 启动服务
echo "[3/5] 启动服务..."
sudo systemctl start brand-diagnosis-backend

# 5. 健康检查
echo "[4/5] 健康检查..."
sleep 5
curl -s http://localhost:5000/api/test | grep -q "success" && echo "✅ 健康检查通过" || echo "❌ 健康检查失败"

echo "[5/5] 回滚完成..."

echo "=========================================="
echo "✅ 回滚完成！"
echo "=========================================="
```

---

## 三、监控配置

### 3.1 Prometheus 告警规则

```yaml
# monitoring/prometheus/alerts.yml

groups:
  - name: brand_diagnosis
    rules:
      - alert: HighErrorRate
        expr: rate(api_errors_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 错误率过高"
          description: "错误率超过 5%"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(api_latency_seconds_bucket[5m])) > 35
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API 延迟过高"
          description: "P95 延迟超过 35 秒"
```

---

## 四、部署时间表

| 阶段 | 时间 | 操作 | 负责人 |
|------|------|------|--------|
| 灰度 1% | 3/01 10:00 | 部署新版本，1% 流量 | 孙工 |
| 监控观察 | 3/01-3/02 | 监控指标，收集反馈 | 全体 |
| 灰度 10% | 3/02 10:00 | 扩大到 10% 流量 | 孙工 |
| 监控观察 | 3/02-3/03 | 监控指标，收集反馈 | 全体 |
| 灰度 50% | 3/03 10:00 | 扩大到 50% 流量 | 孙工 |
| 监控观察 | 3/03-3/04 | 监控指标，收集反馈 | 全体 |
| 全量发布 | 3/05 10:00 | 100% 流量 | 孙工 |
| 持续监控 | 3/05-3/12 | 持续监控一周 | 全体 |

---

## 五、签字确认

| 角色 | 姓名 | 签字 | 日期 |
|------|------|------|------|
| DevOps | 孙工 | _________ | _________ |
| 后端开发 | 李工 | _________ | _________ |
| 测试工程师 | 赵工 | _________ | _________ |
| 首席架构师 | 张工 | _________ | _________ |
| 项目总指挥 | TPM | _________ | _________ |

---

**文档状态**: ✅ 已完成  
**创建日期**: 2026-03-06  
**负责人**: DevOps 孙工
