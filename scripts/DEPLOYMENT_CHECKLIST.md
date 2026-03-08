# 部署前检查清单

**项目名称**: 品牌诊断报告系统  
**检查日期**: _______________  
**检查人**: _______________  
**部署版本**: _______________

---

## 一、代码检查

### 1.1 NxM 引擎字段完整性

- [ ] `backend_python/wechat_backend/nxm_execution_engine.py` 中所有结果字典包含 `brand` 字段
- [ ] `backend_python/wechat_backend/nxm_execution_engine.py` 中所有结果字典包含 `tokens_used` 字段
- [ ] 添加了 `validate_result_fields` 装饰器
- [ ] 添加了结构化日志（TraceID）

**验证方法**:
```bash
grep "'brand': main_brand" backend_python/wechat_backend/nxm_execution_engine.py
grep "tokens_used" backend_python/wechat_backend/nxm_execution_engine.py
```

### 1.2 验证模块

- [ ] `backend_python/wechat_backend/types.py` 存在且包含 `DiagnosisResult` 类型定义
- [ ] `backend_python/wechat_backend/validators.py` 存在且包含 `ResultValidator` 类
- [ ] 验证器在结果收集时被调用

**验证方法**:
```bash
ls -la backend_python/wechat_backend/types.py
ls -la backend_python/wechat_backend/validators.py
```

### 1.3 云函数

- [ ] `miniprogram/cloudfunctions/getDiagnosisReport/index.js` 存在
- [ ] `miniprogram/cloudfunctions/getDiagnosisReport/package.json` 存在
- [ ] 云函数调用后端 `/api/diagnosis/report/{executionId}` API
- [ ] 云函数包含错误处理和降级逻辑

**验证方法**:
```bash
ls -la miniprogram/cloudfunctions/getDiagnosisReport/
grep "/api/diagnosis/report/" miniprogram/cloudfunctions/getDiagnosisReport/index.js
```

---

## 二、测试检查

### 2.1 单元测试

- [ ] 运行 `python3 -m pytest tests/unit/test_validators.py -v`
- [ ] 所有测试通过（100% 通过率）

### 2.2 端到端测试

- [ ] 运行 `python3 -m pytest tests/e2e/test_diagnosis_full_flow.py -v`
- [ ] 所有测试通过（100% 通过率）

### 2.3 快速验证脚本

- [ ] 运行 `./scripts/quick_verify.sh`
- [ ] 所有检查通过

---

## 三、数据检查

### 3.1 数据库表结构

- [ ] `diagnosis_results` 表存在
- [ ] `brand` 列存在（类型：TEXT）
- [ ] `tokens_used` 列存在（类型：INTEGER）

**验证方法**:
```bash
sqlite3 backend_python/database.db "PRAGMA table_info(diagnosis_results);"
```

### 3.2 数据完整性

- [ ] 执行一次测试诊断
- [ ] 检查数据库记录：`SELECT brand, tokens_used FROM diagnosis_results ORDER BY id DESC LIMIT 5;`
- [ ] `brand` 字段空值率 < 1%
- [ ] `tokens_used` 字段零值率 < 50%

**验证 SQL**:
```sql
-- 检查 brand 空值率
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN brand = '' OR brand IS NULL THEN 1 ELSE 0 END) as empty_brand,
    SUM(CASE WHEN tokens_used = 0 OR tokens_used IS NULL THEN 1 ELSE 0 END) as zero_tokens
FROM diagnosis_results;
```

---

## 四、日志检查

### 4.1 结构化日志

- [ ] 日志中包含 `trace_id` 字段
- [ ] 日志中包含 `execution_id` 字段
- [ ] 日志中包含 `event` 字段（标识事件类型）

**验证方法**:
```bash
tail -f backend_python/logs/app.log | grep "trace_id"
```

### 4.2 字段验证日志

- [ ] 日志中包含 `result_validated` 事件
- [ ] 日志中显示 `brand` 和 `tokens_used` 值

**验证方法**:
```bash
tail -f backend_python/logs/app.log | grep "result_validated"
```

---

## 五、功能检查

### 5.1 后端服务

- [ ] 后端服务启动正常：`cd backend_python && python3 app.py`
- [ ] 健康检查通过：`curl http://localhost:5001/health`
- [ ] 诊断 API 正常：`POST /api/perform-brand-test`
- [ ] 状态查询 API 正常：`GET /test/status/{execution_id}`
- [ ] 报告 API 正常：`GET /api/diagnosis/report/{execution_id}`

### 5.2 前端功能

- [ ] 小程序编译无错误
- [ ] 诊断按钮点击正常
- [ ] 进度显示正常
- [ ] 报告页面显示正常
- [ ] 品牌分布数据正确
- [ ] 情感分析数据正确

### 5.3 数据流验证

- [ ] 前端发起诊断 → 后端接收请求
- [ ] 后端执行 NxM 测试 → 数据库保存结果
- [ ] 前端轮询状态 → 后端返回进度
- [ ] 诊断完成 → 前端显示报告

---

## 六、监控检查

### 6.1 数据质量监控

- [ ] 验证器统计正常：`ResultValidator.get_stats()`
- [ ] 验证通过率 > 95%
- [ ] 错误日志可查询

### 6.2 告警配置

- [ ] `brand` 字段空值率告警阈值 < 1%
- [ ] `tokens_used` 零值率告警阈值 < 50%
- [ ] 告警通知渠道配置正确

---

## 七、回滚计划

### 7.1 回滚条件

- [ ] 诊断失败率 > 10%
- [ ] 报告空值率 > 5%
- [ ] 用户投诉 > 3 起

### 7.2 回滚步骤

1. 停止后端服务
2. 恢复代码到上一个稳定版本：`git checkout <previous-tag>`
3. 重启后端服务
4. 验证基本功能

---

## 八、签署确认

| 检查项 | 检查人 | 日期 | 状态 |
|--------|--------|------|------|
| 代码检查 | | | ☐ 通过 ☐ 不通过 |
| 测试检查 | | | ☐ 通过 ☐ 不通过 |
| 数据检查 | | | ☐ 通过 ☐ 不通过 |
| 日志检查 | | | ☐ 通过 ☐ 不通过 |
| 功能检查 | | | ☐ 通过 ☐ 不通过 |
| 监控检查 | | | ☐ 通过 ☐ 不通过 |

**最终决定**:
- [ ] ✅ 批准部署
- [ ] ❌ 拒绝部署（原因：_______________）

**批准人**: _______________  
**批准日期**: _______________

---

*最后更新：2026-03-07*
