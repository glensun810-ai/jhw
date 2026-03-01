# 数据库迁移指南

**版本**: 1.0.0
**创建日期**: 2026-02-27
**最后更新**: 2026-02-27

---

## 目录结构

```
migrations/
├── 001_add_task_count_fields.py    # 添加任务计数字段
├── 002_add_task_count_fields.py    # 重复（保留用于兼容）
├── 003_add_should_stop_polling.py  # 添加轮询停止标志
├── 004_add_v2_indexes.py           # 添加 v2 索引
└── README.md                       # 本文档
```

---

## 迁移原则

根据重构开发规范（规则 7.1）：

1. **向后兼容**: 所有迁移必须向后兼容，禁止删除或修改现有字段
2. **可回滚**: 所有迁移必须提供 `downgrade()` 方法
3. **禁止生产 DDL**: 禁止在生产环境直接执行 DDL，必须通过迁移脚本

---

## 执行迁移

### 开发环境

```bash
cd backend_python

# 执行所有迁移
python -m migrations.003_add_should_stop_polling
python -m migrations.004_add_v2_indexes

# 或者直接运行
python migrations/003_add_should_stop_polling.py
python migrations/004_add_v2_indexes.py
```

### 生产环境

```bash
# 1. 备份数据库
cp database.db database.db.backup.$(date +%Y%m%d_%H%M%S)

# 2. 执行迁移
python migrations/003_add_should_stop_polling.py
python migrations/004_add_v2_indexes.py

# 3. 验证迁移
sqlite3 database.db ".schema diagnosis_reports"
sqlite3 database.db ".indexes"
```

---

## 回滚迁移

**警告**: 回滚可能导致数据丢失，请谨慎操作！

```bash
# 回滚单个迁移
python migrations/004_add_v2_indexes.py downgrade

# 注意：SQLite 不支持直接删除列
# 如需回滚 003_add_should_stop_polling，需要手动重建表
```

---

## 迁移检查清单

执行迁移前：

- [ ] 已备份数据库
- [ ] 已停止应用服务
- [ ] 已测试迁移脚本（开发环境）
- [ ] 已准备回滚方案

执行迁移后：

- [ ] 验证表结构正确
- [ ] 验证索引已创建
- [ ] 验证应用启动正常
- [ ] 验证核心功能正常

---

## 索引说明

### v2 新增索引

| 索引名称 | 表 | 字段 | 用途 |
|---------|-----|------|------|
| `idx_diagnosis_reports_execution_id` | diagnosis_reports | execution_id | 状态查询优化 |
| `idx_diagnosis_reports_status` | diagnosis_reports | status | 状态过滤优化 |
| `idx_diagnosis_reports_user_id` | diagnosis_reports | user_id | 用户历史查询优化 |
| `idx_diagnosis_reports_created_at` | diagnosis_reports | created_at | 时间范围查询优化 |
| `idx_diagnosis_results_execution_id` | diagnosis_results | execution_id | 结果查询优化 |
| `idx_api_call_logs_execution_id` | api_call_logs | execution_id | API 日志查询优化 |
| `idx_api_call_logs_request_timestamp` | api_call_logs | request_timestamp | 时间范围查询优化 |

---

## 故障排查

### 迁移失败

```bash
# 检查数据库锁
lsof database.db

# 检查数据库完整性
sqlite3 database.db "PRAGMA integrity_check"

# 手动执行迁移
sqlite3 database.db "ALTER TABLE diagnosis_reports ADD COLUMN should_stop_polling BOOLEAN DEFAULT 0"
```

### 索引已存在

```bash
# 查看现有索引
sqlite3 database.db ".indexes diagnosis_reports"

# 删除冲突索引
sqlite3 database.db "DROP INDEX IF EXISTS idx_diagnosis_reports_execution_id"
```

---

## 联系支持

- 迁移问题：查看日志 `migrations/*.log`
- 紧急故障：联系运维团队
