# 阶段一预发布验证清单

## 验证前准备

### 环境确认
- [ ] 预发布环境已部署最新代码（版本号：__________）
- [ ] 数据库已执行所有迁移脚本
- [ ] 特性开关配置正确（所有 v2 功能已开启）
- [ ] 监控系统已配置并正常运行
- [ ] 日志系统可正常访问
- [ ] Redis 服务正常运行
- [ ] 备份目录可访问且有最近备份

### 数据准备
- [ ] 测试账号已创建
- [ ] 测试数据已准备
- [ ] 历史数据备份已完成
- [ ] 死信队列已清空（或确认有数据可验证）

### 脚本准备
- [ ] 验证脚本有执行权限
- [ ] Python 依赖已安装（requests, psutil 等）
- [ ] 管理员密钥已配置

---

## 验证执行

### 1. 环境检查（自动）

运行命令：
```bash
python scripts/preproduction/check_environment.py --url https://staging-api.example.com
```

检查项：
- [ ] API 连通性正常
- [ ] 数据库可正常访问
- [ ] Redis 可正常访问
- [ ] 磁盘空间充足（>10GB）
- [ ] 内存充足（>2GB 可用）
- [ ] 所有必要表已创建
- [ ] 特性开关配置正确
- [ ] 日志目录可写
- [ ] 备份目录存在

---

### 2. 功能测试（自动 + 人工）

运行命令：
```bash
python scripts/preproduction/test_cases/test_functional.py --url https://staging-api.example.com
```

#### 核心功能
- [ ] 可以成功发起诊断
- [ ] 状态轮询正常（不会无限轮询）
- [ ] 可以获取诊断报告
- [ ] 报告包含真实数据

#### 异常处理
- [ ] 超时处理正常
- [ ] 部分成功返回存根报告
- [ ] 完全失败返回错误存根
- [ ] 无效请求返回 400 错误

#### 历史记录
- [ ] 历史记录列表可查看
- [ ] 历史报告可正常打开
- [ ] 历史数据与当时一致

#### 存根报告
- [ ] 不存在的 execution_id 返回存根报告
- [ ] 存根报告包含错误信息
- [ ] 存根报告包含下一步建议

---

### 3. 性能测试（自动）

运行命令：
```bash
python scripts/preproduction/test_cases/test_performance.py --url https://staging-api.example.com
```

| 测试项 | 预期 | 实际 | 结果 |
|-------|------|------|------|
| 单次诊断时间 | <10 分钟 | ______ | [ ] |
| 并发 5 任务 | 成功率 100% | ______ | [ ] |
| API 延迟 | P95 <500ms | ______ | [ ] |
| 数据库查询 | 无慢查询 | ______ | [ ] |

---

### 4. 稳定性测试（自动）

运行命令：
```bash
python scripts/preproduction/test_cases/test_stability.py --url https://staging-api.example.com --duration 30
```

- [ ] 30 分钟持续运行无错误
- [ ] 内存使用率 <80%
- [ ] CPU 使用率 <70%
- [ ] 无任务卡死
- [ ] 健康检查持续通过

---

### 5. 兼容性测试（自动 + 人工）

运行命令：
```bash
python scripts/preproduction/test_cases/test_compatibility.py --url https://staging-api.example.com
```

- [ ] v1 API 仍然可用
- [ ] v2 API 响应格式正确
- [ ] 旧数据可正常读取
- [ ] 特性开关可正常切换
- [ ] 数据格式兼容
- [ ] API 版本控制正常

---

### 6. 回滚测试（自动 + 人工）

运行命令：
```bash
python scripts/preproduction/test_cases/test_rollback.py --url https://staging-api.example.com
```

- [ ] 特性开关回滚有效
- [ ] 数据库回滚脚本可执行
- [ ] 回滚文档完整可用
- [ ] 回滚后系统可正常运行
- [ ] v1 功能在回滚后可用

---

## 验证后确认

### 问题记录

| 问题 ID | 描述 | 严重级别 | 状态 | 负责人 |
|--------|------|----------|------|--------|
| | | P0/P1/P2 | 待处理/处理中/已解决 | |
| | | | | |
| | | | | |

### 问题分级定义

- **P0**：系统完全不可用，需立即回滚
- **P1**：核心功能不可用，需修复后上线
- **P2**：非核心功能问题，可带病上线
- **P3**：轻微问题，后续迭代修复

---

### 审批

- [ ] 所有 P0/P1 问题已修复
- [ ] 测试负责人确认：__________ 日期：__________
- [ ] 开发负责人确认：__________ 日期：__________
- [ ] 产品经理确认：__________ 日期：__________
- [ ] 运维负责人确认：__________ 日期：__________

---

### 最终决策

- [ ] ✅ **通过** - 可以进入灰度发布
- [ ] ⚠️ **有条件通过** - 需注意：__________
- [ ] ❌ **不通过** - 需重新验证

---

## 附录

### 快速验证命令

```bash
# 完整验证
python scripts/preproduction/validate_stage1.py \
  --url https://staging-api.example.com \
  --admin-key your-admin-key

# 快速验证（跳过稳定性测试）
python scripts/preproduction/validate_stage1.py \
  --url https://staging-api.example.com \
  --skip-stability

# 仅运行特定测试
python scripts/preproduction/test_cases/test_functional.py \
  --url https://staging-api.example.com
```

### 报告查看

验证报告生成位置：
- Markdown: `scripts/preproduction/reports/stage1_validation_*.md`
- HTML: `scripts/preproduction/reports/stage1_validation_*.html`
- JSON: `scripts/preproduction/reports/stage1_validation_*.json`

### 参考文档

- 重构基线：第 5.2 节 - 最终验收标准
- 实施路线图：P1-T10 - 预发布验证
- 开发规范：第 10 章 - 部署与发布规范

---

**验证人员**：__________  
**验证日期**：__________  
**验证环境**：__________  
**代码版本**：__________  
**备注**：__________
