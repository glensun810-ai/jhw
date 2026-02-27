# 阶段一回滚方案

## 概述

本文档描述了阶段一（P1-T1 至 P1-T10）功能上线后出现问题时，如何快速回滚到 v1.0.0 版本。

**版本信息**：
- 当前版本：v2.0.0-phase1
- 回滚目标：v1.0.0
- 文档版本：1.0.0
- 最后更新：2026-02-27
- 责任人：系统架构组

---

## 回滚触发条件

### P0 级（立即回滚）

出现以下情况时，立即执行回滚：

- 超过 50% 用户无法使用诊断功能
- 系统完全不可用（API 无响应）
- 数据丢失或损坏
- 安全漏洞被利用

**决策人**：CTO 或技术总监
**响应时间**：< 5 分钟

### P1 级（暂停灰度，评估后回滚）

出现以下情况时，暂停灰度发布，评估后决定是否回滚：

- 20-50% 用户遇到诊断卡死
- 报告大面积为空
- 性能严重下降（响应时间>5 分钟）
- 关键监控指标异常

**决策人**：技术总监
**响应时间**：< 15 分钟

### P2 级（继续观察）

出现以下情况时，继续观察，暂不回滚：

- 5-20% 用户遇到非核心功能问题
- 偶发性错误（错误率<1%）
- 性能轻微下降

**决策人**：后端负责人
**响应时间**：< 1 小时

---

## 回滚前检查

### 1. 确认当前状态

```bash
# 确认当前版本
curl https://api.example.com/api/version
# 预期输出：{"version": "v2.0.0-phase1"}

# 检查健康状态
curl https://api.example.com/api/health
# 预期输出：{"status": "healthy"}

# 查看错误日志
tail -100 /var/log/wechat-backend/error.log | grep -i error
```

### 2. 检查数据库备份

```bash
# 查看备份目录
ls -la /data/backups/

# 确认有最近 24 小时内的备份
# 备份文件命名格式：diagnosis_YYYYMMDD_HHMMSS.db

# 检查备份文件大小（应>0）
stat /data/backups/diagnosis_*.db
```

### 3. 确认回滚脚本可用

```bash
# 检查回滚脚本
ls -la scripts/rollback/
# 应包含:
# - rollback_feature_flags.py
# - rollback_database.sh
# - rollback_code.sh

# 检查脚本执行权限
chmod +x scripts/rollback/*.sh
```

### 4. 通知相关人员

```
【回滚通知】
时间：YYYY-MM-DD HH:MM
原因：[简要描述问题]
影响：[受影响的用户比例/功能]
回滚方案：[方案 A/B/C]
预计耗时：[X 分钟]
负责人：[姓名]
```

---

## 回滚步骤

### 方案 A：特性开关回滚（最快，<1 分钟）

**适用场景**：
- 问题由 v2 新功能引起
- v1 代码仍然存在于系统中
- 需要快速恢复服务

**步骤**：

```bash
# 1. 关闭所有 v2 功能开关
curl -X POST http://localhost:5000/api/admin/feature-flags \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: YOUR_ADMIN_KEY" \
  -d '{
    "diagnosis_v2_enabled": false,
    "diagnosis_v2_state_machine": false,
    "diagnosis_v2_timeout": false,
    "diagnosis_v2_retry": false,
    "diagnosis_v2_dead_letter": false,
    "diagnosis_v2_api_logging": false,
    "diagnosis_v2_data_persistence": false,
    "diagnosis_v2_report_stub": false
  }'

# 2. 验证回滚
curl https://api.example.com/api/version
# 仍显示 v2.0.0-phase1，但功能已回退到 v1

# 3. 验证 v1 功能可用
curl -X POST https://api.example.com/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{"brand_list":["测试品牌"],"selectedModels":[{"name":"deepseek","checked":true}],"custom_question":"测试"}'

# 4. 检查监控指标
curl https://api.example.com/api/monitoring/metrics
```

**验证检查**：
- [ ] v1 API 可以正常发起诊断
- [ ] 诊断任务可以正常完成
- [ ] 报告可以正常获取
- [ ] 错误率下降到正常水平

---

### 方案 B：代码回滚（较慢，<10 分钟）

**适用场景**：
- 特性开关回滚无效
- v1 和 v2 代码不共存
- 需要完全恢复到 v1.0.0

**步骤**：

```bash
# 1. 切换到回滚分支
cd /data/app/wechat-backend
git checkout v1.0.0

# 2. 确认代码版本
git log -1
# 确认是 v1.0.0 的提交

# 3. 重启服务
sudo systemctl restart wechat-backend

# 4. 检查服务状态
sudo systemctl status wechat-backend

# 5. 验证版本
curl https://api.example.com/api/version
# 预期输出：{"version": "v1.0.0"}

# 6. 验证功能
curl -X POST https://api.example.com/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{"brand_list":["测试品牌"]}'
```

**验证检查**：
- [ ] 服务启动成功
- [ ] 版本号显示 v1.0.0
- [ ] v1 API 功能正常
- [ ] 监控指标正常

---

### 方案 C：数据库回滚（最慢，<30 分钟）

**适用场景**：
- 数据库结构已变更且不兼容
- 数据损坏需要恢复
- 其他方案无效

**步骤**：

```bash
# 1. 停止服务
sudo systemctl stop wechat-backend

# 2. 确认备份文件
ls -la /data/backups/
# 选择最近的备份文件

# 3. 备份当前数据库（以防万一）
cp /data/staging/diagnosis.db /data/backups/pre_rollback_backup_$(date +%Y%m%d_%H%M%S).db

# 4. 恢复数据库
cd /data/backups
./rollback_database.sh --restore latest

# 或者手动执行
cp /data/backups/diagnosis_YYYYMMDD_HHMMSS.db /data/staging/diagnosis.db

# 5. 验证数据完整性
python /data/app/wechat-backend/scripts/verify_data_integrity.py

# 6. 重启服务
sudo systemctl start wechat-backend

# 7. 验证服务
curl https://api.example.com/api/health
curl https://api.example.com/api/version
```

**验证检查**：
- [ ] 数据库恢复成功
- [ ] 数据完整性验证通过
- [ ] 服务启动成功
- [ ] 所有功能正常

---

## 回滚后验证

### 1. 健康检查

```bash
# API 健康检查
curl https://api.example.com/api/health
# 预期：{"status": "healthy"}

# 版本检查
curl https://api.example.com/api/version
# 预期：{"version": "v1.0.0"} 或 v2.0.0-phase1（方案 A）

# 监控检查
curl https://api.example.com/api/monitoring/dashboard
# 检查关键指标是否正常
```

### 2. 功能验证

```bash
# 发起诊断
DIAG_RESPONSE=$(curl -X POST https://api.example.com/api/perform-brand-test \
  -H "Content-Type: application/json" \
  -d '{"brand_list":["回滚测试品牌"],"selectedModels":[{"name":"deepseek","checked":true}],"custom_question":"回滚验证"}')

# 提取 execution_id
EXEC_ID=$(echo $DIAG_RESPONSE | jq -r '.execution_id // .data.id')

# 查询状态
curl https://api.example.com/api/diagnostic/tasks/$EXEC_ID/status

# 获取报告
curl https://api.example.com/api/diagnostic/tasks/$EXEC_ID/report
```

### 3. 监控检查

- [ ] 错误率 < 1%
- [ ] 响应时间 < 2 秒
- [ ] CPU 使用率 < 70%
- [ ] 内存使用率 < 80%
- [ ] 数据库连接正常
- [ ] Redis 连接正常

### 4. 用户验证

- [ ] 内部测试账号可以正常使用
- [ ] 抽样用户回访确认功能正常
- [ ] 客服无异常反馈

---

## 紧急联系人

| 角色 | 姓名 | 电话 | 微信 | 邮箱 |
|------|------|------|------|------|
| CTO | 张三 | 138****0000 | zhang3 | zhang3@example.com |
| 技术总监 | 李四 | 139****1111 | li4 | li4@example.com |
| 后端负责人 | 王五 | 137****2222 | wang5 | wang5@example.com |
| 运维负责人 | 赵六 | 136****3333 | zhao6 | zhao6@example.com |
| 产品经理 | 钱七 | 135****4444 | qian7 | qian7@example.com |

**紧急联系群**：[微信群链接/钉钉群链接]

---

## 回滚决策流程

```
                    ┌─────────────┐
                    │   发现问题   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   问题分级   │
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │   P0    │      │   P1    │      │   P2    │
    └────┬────┘      └────┬────┘      └────┬────┘
         │                │                │
         │                │                │
    ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
    │ 立即回滚 │      │ 暂停灰度 │      │ 继续观察 │
    │ 方案 A  │      │ 技术总监 │      │ 后端负责 │
    └────┬────┘      │ 评估     │      │ 人评估   │
         │           └────┬────┘      └───────────┘
         │                │
         │         ┌──────┴──────┐
         │         │             │
         │    ┌────▼────┐  ┌────▼────┐
         │    │  严重   │  │ 可修复  │
         │    │  回滚   │  │  继续   │
         │    └────┬────┘  └─────────┘
         │         │
         │         │
    ┌────▼─────────▼────┐
    │   执行回滚方案    │
    └────┬──────────────┘
         │
    ┌────▼────┐
    │  验证   │
    └────┬────┘
         │
    ┌────▼────┐
    │  复盘   │
    └─────────┘
```

---

## 回滚后复盘

### 复盘清单

- [ ] 问题根因分析完成
- [ ] 影响范围评估完成
- [ ] 修复方案已制定
- [ ] 测试用例已补充
- [ ] 监控告警已完善
- [ ] 文档已更新
- [ ] 团队已同步

### 复盘会议

**时间**：回滚后 24 小时内
**参与人员**：所有相关人员
**议程**：
1. 问题发现过程
2. 问题根因分析
3. 回滚过程回顾
4. 改进措施讨论
5. 行动计划制定

### 复盘报告模板

```markdown
# 回滚复盘报告

## 基本信息
- 回滚时间：YYYY-MM-DD HH:MM
- 回滚原因：
- 影响范围：
- 回滚方案：

## 时间线
- HH:MM - 问题发生
- HH:MM - 问题发现
- HH:MM - 开始回滚
- HH:MM - 回滚完成
- HH:MM - 服务恢复

## 根因分析

## 改进措施
1. 
2. 
3. 

## 行动计划
| 措施 | 负责人 | 截止日期 | 状态 |
|------|--------|----------|------|
|      |        |          |      |
```

---

## 附录

### A. 常用命令速查

```bash
# 查看服务状态
sudo systemctl status wechat-backend

# 重启服务
sudo systemctl restart wechat-backend

# 查看日志
tail -f /var/log/wechat-backend/error.log

# 查看版本
curl https://api.example.com/api/version

# 查看特性开关
curl https://api.example.com/api/admin/feature-flags

# 查看监控指标
curl https://api.example.com/api/monitoring/metrics
```

### B. 相关文件位置

| 文件 | 路径 |
|------|------|
| 服务配置 | /etc/systemd/system/wechat-backend.service |
| 应用代码 | /data/app/wechat-backend |
| 数据库 | /data/staging/diagnosis.db |
| 备份目录 | /data/backups |
| 日志目录 | /var/log/wechat-backend |
| 回滚脚本 | /data/app/wechat-backend/scripts/rollback |

### C. 版本历史

| 版本 | 日期 | 变更 | 负责人 |
|------|------|------|--------|
| 1.0.0 | 2026-02-27 | 初始版本 | 系统架构组 |

---

**文档审批**：
- 技术总监：__________ 日期：__________
- 后端负责人：__________ 日期：__________
- 运维负责人：__________ 日期：__________
