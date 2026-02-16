# GEO系统测试文档

## 测试文档清单

本目录包含GEO系统的完整测试文档和工具：

### 1. 测试计划与策略
- **GEO_System_Test_Plan.md** - 详细的测试计划，包含测试范围、执行顺序和时间表

### 2. 测试执行脚本
- **test_geo_api_comprehensive.py** - 综合API测试脚本，覆盖所有接口
- **quick_smoke_test.py** - 快速冒烟测试，用于快速验证核心功能

### 3. 测试报告模板
- **Test_Report_Template.md** - 标准化的测试报告模板

### 4. 问题分析与建议
- **Analysis_and_Recommendations.md** - 已知问题分析和改进建议

### 5. 现有测试文件
- **test_integration.py** - 集成测试（已有）
- **test_security_improvements.py** - 安全改进测试（已有）
- **test_startup.py** - 启动测试（已有）

## 快速开始

### 环境准备

```bash
# 1. 确保后端服务已启动
cd /Users/sgl/PycharmProjects/PythonProject/backend_python
python run.py

# 2. 等待服务启动（约5秒）
sleep 5

# 3. 验证服务状态
curl http://127.0.0.1:5001/health
```

### 执行快速冒烟测试

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python/tests
python quick_smoke_test.py
```

预期输出：
```
============================================================
GEO系统快速冒烟测试
============================================================
测试URL: http://127.0.0.1:5001
超时设置: 10秒
============================================================

1. 基础连通性测试
  ✅ 健康检查: 200 (15ms)
  ✅ 首页: 200 (8ms)
  ✅ API测试: 200 (12ms)
...
```

### 执行综合测试

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python/tests
python test_geo_api_comprehensive.py
```

测试将自动执行并生成详细报告：
- 控制台输出测试进度
- 生成JSON格式的详细报告文件

## 测试阶段说明

### 第一阶段：基础连通性测试（P0）
验证服务基本可用性：
- `GET /health` - 健康检查
- `GET /` - 首页服务状态
- `GET /api/test` - API连接测试
- `OPTIONS /api/perform-brand-test` - CORS预检

### 第二阶段：认证接口测试（P0）
验证认证机制：
- `POST /api/login` - 微信登录（异常场景）
- `POST /api/validate-token` - 令牌验证
- `POST /api/refresh-token` - 令牌刷新

### 第三阶段：品牌测试核心接口（P0）
验证核心业务功能：
- `POST /api/perform-brand-test` - 启动品牌测试
- `GET /api/test-progress` - 获取测试进度

### 第四阶段：数据管理接口（P1）
验证数据操作：
- `POST /api/sync-data` - 数据同步
- `POST /api/download-data` - 数据下载
- `GET /api/test-history` - 历史记录

### 第五阶段：平台与配置接口（P1）
验证配置功能：
- `GET /api/ai-platforms` - AI平台列表
- `GET /api/platform-status` - 平台状态
- `GET /api/config` - 配置获取

### 第六阶段：高级功能接口（P2）
验证高级功能：
- `GET /api/source-intelligence` - 信源情报
- `POST /api/competitive-analysis` - 竞争分析

### 第七阶段：安全测试（P1）
验证安全防护：
- SQL注入防护测试
- XSS防护测试
- 限流机制测试

## 已知问题

### 严重问题
1. **403 Forbidden错误** - 多个 `/api/*` 接口返回403
   - 影响接口：`/api/test`, `/api/perform-brand-test` 等
   - 可能原因：CORS配置、装饰器拦截、认证问题
   - 详见：Analysis_and_Recommendations.md

### 建议修复方案
1. 检查CORS配置顺序
2. 临时禁用问题装饰器进行测试
3. 在视图函数中显式处理OPTIONS请求

## 测试数据

测试脚本使用以下测试数据：

```python
TEST_BRAND = "测试品牌"
TEST_COMPETITOR = "竞争对手品牌"
TEST_QUESTION = "测试品牌怎么样？"
TEST_OPENID = f"test_openid_{uuid.uuid4().hex[:8]}"
```

## 报告输出

### 控制台输出
测试完成后，控制台显示：
- 各阶段测试统计
- 失败的测试详情
- 总体通过率

### JSON报告
详细报告保存为JSON文件：
```
test_report_YYYYMMDD_HHMMSS.json
```

报告内容：
- 测试摘要（总数、通过、失败、通过率）
- 各阶段统计
- 失败测试详情
- 所有测试记录

## 持续集成

建议将测试集成到CI/CD流程：

```yaml
# .github/workflows/test.yml
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start server
        run: python run.py &
      - name: Wait for server
        run: sleep 5
      - name: Run smoke tests
        run: python tests/quick_smoke_test.py
      - name: Run comprehensive tests
        run: python tests/test_geo_api_comprehensive.py
```

## 注意事项

1. **服务依赖**：测试需要后端服务运行在 `http://127.0.0.1:5001`
2. **外部API**：部分测试会调用AI平台API，可能因网络或API限制失败
3. **超时设置**：品牌测试接口可能需要较长时间，已设置120秒超时
4. **数据安全**：测试数据为模拟数据，不会污染生产数据

## 问题反馈

如发现测试问题或需要补充测试场景，请：
1. 记录问题详情（接口、参数、响应）
2. 更新测试脚本
3. 更新测试报告

## 参考文档

- [接口审计报告](../docs/2026-02-14_GEO_System_Interface_Audit_Report.md)
- [测试计划](./GEO_System_Test_Plan.md)
- [问题分析与建议](./Analysis_and_Recommendations.md)

---

**最后更新**: 2026-02-15
**文档版本**: 1.0
