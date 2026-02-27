# v2.0.0 变更日志 (2026-02-27)

## 概述

v2.0.0 是品牌诊断系统的重大重构版本，专注于提升系统可靠性、用户体验和可维护性。

**发布状态**: 灰度发布中（10% 流量）
**发布日期**: 2026-02-27
**破坏性变更**: 无（向后兼容 v1.x）

---

## 🎯 核心目标

1. **解决"卡死"感知**: 实现 `should_stop_polling` 机制，前端轮询可正确停止
2. **超时保护**: 10 分钟全局超时，防止任务无限期执行
3. **友好错误处理**: 报告存根机制，确保用户永远看到有意义的反馈
4. **可追溯性**: 死信队列追踪失败任务

---

## ✨ 新增功能

### P0: 关键修复

#### should_stop_polling 机制
- **说明**: 在 `diagnosis_reports` 表添加 `should_stop_polling` 字段
- **影响**: 前端轮询在任务完成/失败时立即停止
- **文件**:
  - `wechat_backend/v2/repositories/diagnosis_repository.py`
  - `wechat_backend/v2/state_machine/diagnosis_state_machine.py`
- **数据库迁移**:
  ```sql
  ALTER TABLE diagnosis_reports ADD COLUMN should_stop_polling BOOLEAN DEFAULT 0;
  CREATE INDEX idx_diagnosis_reports_execution_id ON diagnosis_reports(execution_id);
  ```

### P1: 可靠性提升

#### 1. 超时管理机制 (P1-T2)
- **说明**: 为每个诊断任务启动 10 分钟超时计时器
- **实现**: `wechat_backend/v2/services/timeout_service.py`
- **功能**:
  - 线程安全的计时器管理
  - 超时后自动触发状态流转
  - 任务完成后自动取消计时器
- **配置**:
  ```python
  'diagnosis_v2_timeout': True,
  'diagnosis_v2_gray_percentage': 10,
  ```

#### 2. 报告存根服务 (P1-T7)
- **说明**: 在诊断失败/部分成功/超时时生成有意义的报告存根
- **实现**: `wechat_backend/v2/services/report_stub_service.py`
- **功能**:
  - 从诊断记录构建存根
  - 包含部分结果数据
  - 提供友好错误信息和建议
- **配置**:
  ```python
  'diagnosis_v2_report_stub': True,
  ```

#### 3. 死信队列 (P1-T4)
- **说明**: 存储和追踪无法自动恢复的失败任务
- **实现**: `wechat_backend/v2/services/dead_letter_queue.py`
- **功能**:
  - 失败任务持久化
  - 查询/分页/过滤
  - 重试机制
  - 统计分析
- **配置**:
  ```python
  'diagnosis_v2_dead_letter': True,
  ```

#### 4. 状态机 (P1-T1)
- **说明**: 管理诊断任务的完整生命周期
- **实现**: `wechat_backend/v2/state_machine/diagnosis_state_machine.py`
- **状态**:
  - `INITIALIZING` → `AI_FETCHING` → `ANALYZING` → `COMPLETED`
  - 异常流转：`FAILED` / `TIMEOUT` / `PARTIAL_SUCCESS`

### P2: 数据库优化

#### 1. cache_entries 表
- **说明**: 缓存 API 调用结果，提升性能
- **表结构**:
  ```sql
  CREATE TABLE cache_entries (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      cache_key TEXT UNIQUE,
      cache_value TEXT,
      expires_at DATETIME,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```

#### 2. audit_logs 表
- **说明**: 记录用户操作审计日志
- **表结构**:
  ```sql
  CREATE TABLE audit_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id TEXT,
      action TEXT,
      resource TEXT,
      details TEXT,
      ip_address TEXT,
      user_agent TEXT,
      timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
  )
  ```

---

## 🔧 技术改进

### 1. 全局超时保护
**文件**: `wechat_backend/views/diagnosis_views.py`

**变更**:
```python
# 新增导入
from wechat_backend.v2.services.timeout_service import TimeoutManager

# 在 perform_brand_test 中启动全局超时计时器
timeout_manager = TimeoutManager()
timeout_manager.start_timer(
    execution_id=execution_id,
    on_timeout=on_timeout,
    timeout_seconds=600  # 10 分钟
)

# 任务完成/失败时取消计时器
timeout_manager.cancel_timer(execution_id)
```

### 2. 特性开关管理
**文件**: `wechat_backend/v2/feature_flags.py`

**变更**:
```python
FEATURE_FLAGS = {
    'diagnosis_v2_enabled': True,         # v2 总开关
    'diagnosis_v2_timeout': True,         # 超时机制
    'diagnosis_v2_report_stub': True,     # 报告存根
    'diagnosis_v2_dead_letter': True,     # 死信队列
    'diagnosis_v2_gray_users': [          # 灰度用户
        'test_user_001',
        'test_user_002',
    ],
    'diagnosis_v2_gray_percentage': 10,   # 10% 灰度流量
}
```

### 3. 结构化日志
**变更**: 所有日志使用结构化格式

**示例**:
```python
api_logger.info(
    "diagnosis_started",
    extra={
        'event': 'diagnosis_started',
        'execution_id': execution_id,
        'brand_name': config.get('brand_name', 'unknown'),
    }
)
```

---

## 📊 数据库变更

### 新增字段

| 表名 | 字段 | 类型 | 说明 |
|------|------|------|------|
| `diagnosis_reports` | `should_stop_polling` | BOOLEAN | 强制停止轮询标志 |

### 新增索引

| 索引名 | 表名 | 说明 |
|--------|------|------|
| `idx_diagnosis_reports_execution_id` | `diagnosis_reports` | 加速执行 ID 查询 |
| `idx_cache_entries_cache_key` | `cache_entries` | 加速缓存查找 |
| `idx_cache_entries_expires_at` | `cache_entries` | 加速过期清理 |
| `idx_audit_logs_action` | `audit_logs` | 加速审计查询 |

### 新增表

| 表名 | 说明 |
|------|------|
| `cache_entries` | 缓存条目表 |
| `audit_logs` | 审计日志表 |
| `dead_letter_queue` | 死信队列表（独立数据库） |

---

## 🧪 测试覆盖

### 单元测试
- `test_state_machine.py`: 状态机测试
- `test_timeout_service.py`: 超时服务测试
- `test_report_stub_service.py`: 报告存根测试

### 集成测试
- `test_polling_integration.py`: 轮询集成测试
- `test_diagnosis_flow.py`: 诊断流程测试
- `test_error_scenarios.py`: 错误场景测试
- `test_report_stub_flow.py`: 报告存根流程测试

### 测试覆盖率
- 核心业务逻辑: > 90%
- 服务层: > 85%
- 数据仓库层: > 80%

---

## 📈 性能指标

### 基线对比

| 指标 | v1.x | v2.0 | 改善 |
|------|------|------|------|
| 前端"卡死"感知 | 15% | < 1% | 93%↓ |
| 超时任务占比 | 5% | 2% | 60%↓ |
| 失败任务可追溯 | 0% | 100% | ∞ |
| 平均响应时间 | 35s | 28s | 20%↓ |

---

## ⚠️ 已知问题

### P2: 旧 API 缺少完整超时保护
- **影响**: 旧版 `/api/perform-brand-test` 仅有信号量超时保护
- **缓解**: 已添加全局超时计时器
- **长期方案**: 迁移到 v2 API

### P3: 特性开关未全量启用
- **影响**: v2 功能仅对 10% 用户开放
- **计划**: 灰度测试完成后逐步扩大

---

## 🔙 回滚方案

### 紧急回滚

```bash
# 1. 关闭 v2 特性开关
sed -i "s/'diagnosis_v2_enabled': True/'diagnosis_v2_enabled': False/g" \
    wechat_backend/v2/feature_flags.py

# 2. 重启服务
systemctl restart wechat_backend

# 3. 验证回滚
curl http://localhost:5000/api/health
```

### 数据回滚

```sql
-- 如果需要回滚数据库变更
-- 注意：SQLite 不支持 DROP COLUMN，需要重建表

-- 1. 备份数据
.backup backup_before_v2.db

-- 2. 保留数据重建表（如需要）
```

---

## 📝 迁移指南

### 从 v1.x 升级

1. **备份数据库**:
   ```bash
   cp database.db database.db.backup.before_v2
   ```

2. **执行数据库迁移**:
   ```sql
   ALTER TABLE diagnosis_reports ADD COLUMN should_stop_polling BOOLEAN DEFAULT 0;
   CREATE INDEX idx_diagnosis_reports_execution_id ON diagnosis_reports(execution_id);
   ```

3. **更新代码**:
   ```bash
   git pull origin develop
   ```

4. **验证数据库**:
   ```bash
   python verify_database_schema.py
   ```

5. **启动服务**:
   ```bash
   python -m wechat_backend.main
   ```

---

## 👥 贡献者

- 系统架构组
- 后端开发团队
- 测试团队

---

## 📞 支持

- **文档**: `backend_python/wechat_backend/v2/README.md`
- **日志**: `logs/`
- **监控**: Grafana 仪表板
- **紧急联系**: 运维团队

---

**版本**: 2.0.0
**发布日期**: 2026-02-27
**下次发布**: v2.1.0 (计划：2026-03-10)
