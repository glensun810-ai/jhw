# 后端部署检查清单

**版本**: v1.0  
**创建日期**: 2026-03-13  
**适用范围**: 所有后端代码修改后的部署

---

## 📋 部署前检查

### 代码修改后

- [ ] 1. 检查 Python 语法
  ```bash
  cd /Users/sgl/PycharmProjects/PythonProject
  python3 -m py_compile backend_python/wechat_backend/nxm_concurrent_engine_v3.py
  python3 -m py_compile backend_python/wechat_backend/diagnosis_report_repository.py
  python3 -m py_compile backend_python/wechat_backend/diagnosis_report_service.py
  ```
  - [ ] 所有文件语法检查通过

- [ ] 2. 运行单元测试
  ```bash
  python3 backend_python/tests/test_brand_extraction.py
  ```
  - [ ] 品牌提取测试通过（至少排名列表格式）

---

## 🔄 部署步骤

### 重启后端服务

- [ ] 1. 停止所有后端进程
  ```bash
  pkill -9 -f "backend_python"
  ```

- [ ] 2. 清理 Python 缓存
  ```bash
  find backend_python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
  find backend_python -name "*.pyc" -delete
  ```

- [ ] 3. 重新启动后端
  ```bash
  cd backend_python
  nohup python3 run.py > run.log 2>&1 &
  ```

- [ ] 4. 等待启动（5 秒）
  ```bash
  sleep 5
  ```

- [ ] 5. 验证服务启动
  ```bash
  curl -s http://localhost:5001/
  ```
  - [ ] 返回版本号（如：1.0）

---

## ✅ 部署后验证

### 自动化验证

- [ ] 1. 执行自动化验证脚本
  ```bash
  cd /Users/sgl/PycharmProjects/PythonProject
  python3 backend_python/tests/verify_diagnosis_flow.py
  ```
  
  **预期输出**:
  ```
  ✅ 代码检查
  ✅ 数据库 schema
  ✅ 数据质量 (提取率 > 0%)
  ✅ API 端点
  总计：4/4 通过
  ```

### 功能验证

- [ ] 2. 执行测试诊断（在小程序中）
  - 主品牌：`宝马`
  - 竞品：`奔驰`, `奥迪`
  - AI 模型：`deepseek`
  - 等待完成

- [ ] 3. 验证数据库
  ```bash
  sqlite3 backend_python/database.db \
    "SELECT execution_id, brand, extracted_brand \
     FROM diagnosis_results \
     ORDER BY created_at DESC \
     LIMIT 1;"
  ```
  - [ ] `extracted_brand` 不为 NULL
  - [ ] `extracted_brand` 与 `brand` 不同

- [ ] 4. 验证 API
  ```bash
  EXEC_ID="从上一步获取"
  curl -s "http://localhost:5001/api/diagnosis/report/$EXEC_ID" | jq '.brandDistribution.data'
  ```
  - [ ] 返回多个品牌（不是只有主品牌）

- [ ] 5. 验证前端
  - [ ] 打开小程序"诊断记录"页面
  - [ ] 点击刚才的诊断记录
  - [ ] 看到品牌分布饼图
  - [ ] 看到多个品牌名称
  - [ ] 看到情感分析柱状图
  - [ ] 看到关键词云

---

## 📊 验证标准

### 必须通过（P0）

- [ ] 后端服务可访问
- [ ] 品牌提取代码存在
- [ ] 数据库 schema 正确
- [ ] 新诊断的 `extracted_brand` 不为 NULL
- [ ] 前端报告页显示完整数据

### 建议通过（P1）

- [ ] 品牌分布有 3 个以上品牌
- [ ] 提取率 > 50%
- [ ] API 响应时间 < 2 秒

---

## 🚨 回滚步骤

如果部署失败：

1. **停止服务**
   ```bash
   pkill -9 -f "backend_python"
   ```

2. **恢复代码**
   ```bash
   cd /Users/sgl/PycharmProjects/PythonProject
   git checkout HEAD -- backend_python/wechat_backend/nxm_concurrent_engine_v3.py
   ```

3. **清理缓存**
   ```bash
   find backend_python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   ```

4. **重启服务**
   ```bash
   cd backend_python && python3 run.py &
   ```

---

## 📝 部署记录

**部署日期**: __________  
**部署人**: __________  
**代码版本**: __________  

**验证结果**:
- [ ] 代码检查：✅ / ❌
- [ ] 数据库 schema: ✅ / ❌
- [ ] 数据质量：✅ / ❌
- [ ] API 端点：✅ / ❌
- [ ] 前端展示：✅ / ❌

**备注**:
_________________________________
_________________________________

---

**审批**: 系统首席架构师  
**下次审查**: 2026-03-20
